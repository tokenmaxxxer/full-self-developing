#!/usr/bin/env python3
"""on-the-record, git-only edition.

Everything of record lives in git:
  requirement  docs/issue-<n>/issue.md               (human, on main)
  work         branch issue-<n>/<hex>, one worktree   (spawned session)
  rationale    docs/issue-<n>/reports/<hex>.md        (session, on its branch)
  approval     docs/issue-<n>/approvals/<hex>.md      (human commit on main)
  acceptance   merge --no-ff into main                (human)
  rejection    docs/issue-<n>/rejections/<hex>.md     (human commit on main)

This tool never writes a record. It reads state, brings up a session, and
relays the human's decisions as commits.

Commands:
  issue "<title>"                 open docs/issue-<n>/issue.md, commit
  spawn <n> "<task>" [--phase proposal|delivery] [--session <hex>]
                                  worktree + branch + headless claude session
  board                           loop_state of every record on main
  approve <n> <hex> ["<note>"]    commit approval on main
  accept <n> <hex>                lint + merge --no-ff into main
  reject <n> <hex> "<reason>"     commit rejection, delete branch
  lint [path]                     record lint
"""
from __future__ import annotations
import argparse
import json
import os
import re
import secrets
import subprocess
import sys
import tempfile
from datetime import date
from pathlib import Path

ROOT = Path(subprocess.run(["git", "rev-parse", "--show-toplevel"], capture_output=True, text=True, check=True).stdout.strip())
TOOLS = ROOT / "tools"
WS = ROOT / "runs" / "ws"
MAIN = "main"


def git(*args: str, cwd: Path = ROOT, check: bool = True) -> str:
    return subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True, check=check).stdout.strip()


def require_clean_main() -> None:
    if git("branch", "--show-current") != MAIN:
        sys.exit(f"otr: run this on {MAIN} (current: {git('branch', '--show-current')})")
    if git("status", "--porcelain"):
        sys.exit("otr: working tree is dirty; commit or stash first")


def approver_emails() -> set[str]:
    p = ROOT / "docs/specs/approvers.md"
    return {l.strip() for l in p.read_text().splitlines() if "@" in l and not l.startswith("#")}


def require_approver() -> str:
    email = git("config", "user.email")
    if email not in approver_emails():
        sys.exit(f"otr: {email} is not in docs/specs/approvers.md")
    return email


# ---------------------------------------------------------------- issue

def next_issue_number() -> int:
    nums = [int(m.group(1)) for p in (ROOT / "docs").glob("issue-*") if (m := re.match(r"issue-(\d+)$", p.name))]
    return max(nums, default=0) + 1


def cmd_issue(a: argparse.Namespace) -> None:
    require_clean_main()
    n = next_issue_number()
    d = ROOT / f"docs/issue-{n}"
    (d / "reports").mkdir(parents=True)
    body = (ROOT / "docs/templates/issue.md").read_text()
    body = body.replace("<n>", str(n)).replace("<one line>", a.title).replace("<YYYY-MM-DD>", date.today().isoformat()).replace("<title>", a.title)
    (d / "issue.md").write_text(body)
    (d / "reports/.gitkeep").write_text("")
    git("add", str(d))
    git("commit", "-q", "-m", f"issue-{n}: {a.title}")
    print(f"docs/issue-{n}/issue.md — fill in Need/Acceptance, then commit and spawn")


# ---------------------------------------------------------------- spawn

DIRECTIVE = """\
You are a headless session bound to issue-{n} on branch {branch}, session id {hex}.
Working directory: {ws} (a git worktree; only this branch lives here).

TASK
{task}

PHASE: {phase}
{phase_rules}

RECORD
- Your record is docs/issue-{n}/reports/{hex}.md. Start from docs/templates/record.md.
  author: is {hex}; issue: is {n}. You may not write any other record, any file under
  docs/issue-*/approvals/, or docs/specs/approvers.md. To correct another session's
  record, add `supersedes: <path>  # <reason>` or `amends: <path>#<section>  # <reason>`
  to your own record's frontmatter instead.
- Order: change the code, run the checks, THEN write the record once from the executed
  results. Every claim in the record cites the command and its output under ## Evidence.
  Bare counts ("all tests pass") without the command are not evidence.
- Run `python3 {tools}/record_lint.py docs/issue-{n}/reports/{hex}.md` before committing.
  The Stop hook refuses to end the session while lint fails or the tree is dirty.

SCOPE
- The requirement is docs/issue-{n}/issue.md. Do not widen it. If finishing needs something
  outside it (another change, a judgment call, a risk), write it under ## Deviations in your
  record and stop — never open new work yourself.
- Never push, merge, switch to main, or delete branches. Landing is the human's act.
- Make a checkpoint commit BEFORE any long verification run, then amend or follow up after.
- This is a single-shot headless run: nobody answers questions. Decide, record why, continue.
"""

PHASE_RULES = {
    "proposal": """\
- Deliver a proposal only: what you will change, how, and how it will be verified
  against each ## Acceptance item in issue.md. No implementation beyond throwaway probes.
- Record: type: proposal, loop_state: proposed. Commit it on this branch.""",
    "delivery": """\
- The proposal on this branch was approved (docs/issue-{n}/approvals/{hex}.md on main).
  Implement exactly it. Deviations go under ## Deviations, not into the code.
- Record: type: implementation (or verification/repair as fits), loop_state: landed,
  with ## Acceptance verification covering every item in issue.md.""",
}


def session_settings(n: int, hexid: str) -> Path:
    py = sys.executable
    hooks = {
        "hooks": {
            "PreToolUse": [
                {"matcher": "Write|Edit|MultiEdit|NotebookEdit", "hooks": [{"type": "command", "command": f"{py} {TOOLS}/hooks/record_guard.py"}]},
                {"matcher": "Bash", "hooks": [{"type": "command", "command": f"{py} {TOOLS}/hooks/git_guard.py"}]},
            ],
            "Stop": [{"hooks": [{"type": "command", "command": f"{py} {TOOLS}/hooks/stop_gate.py"}]}],
        },
        "env": {"OTR_ISSUE": str(n), "OTR_SESSION": hexid},
    }
    f = tempfile.NamedTemporaryFile("w", suffix=f"-otr-{n}-{hexid}.json", delete=False, dir=str(WS))
    json.dump(hooks, f, indent=1)
    f.close()
    return Path(f.name)


def cmd_spawn(a: argparse.Namespace) -> None:
    n = a.issue
    issue_md = ROOT / f"docs/issue-{n}/issue.md"
    if not issue_md.exists():
        sys.exit(f"otr: {issue_md} not found — run `otr issue` first")
    hexid = a.session or secrets.token_hex(4)
    branch = f"issue-{n}/{hexid}"
    WS.mkdir(parents=True, exist_ok=True)
    ws = WS / f"issue-{n}-{hexid}"

    if a.phase == "delivery":
        if not (ROOT / f"docs/issue-{n}/approvals/{hexid}.md").exists():
            sys.exit(f"otr: no approval on {MAIN} for {branch}; run `otr approve {n} {hexid}` first")
        if not ws.exists():
            git("worktree", "add", "-q", str(ws), branch)
        git("merge", "-q", "--no-edit", MAIN, cwd=ws)  # carry the approval commit into the branch
    else:
        if git("branch", "--list", branch):
            sys.exit(f"otr: branch {branch} already exists; pass --session for a new hex or --phase delivery")
        git("worktree", "add", "-q", "-b", branch, str(ws), MAIN)

    task = a.task
    if a.phase == "delivery" and not task:
        task = f"Implement the approved proposal in docs/issue-{n}/reports/{hexid}.md."
    directive = DIRECTIVE.format(
        n=n, hex=hexid, branch=branch, ws=ws, task=task, phase=a.phase, tools=TOOLS,
        phase_rules=PHASE_RULES[a.phase].format(n=n, hex=hexid),
    )
    settings = session_settings(n, hexid)
    cmd = ["claude", "-p", directive, "--settings", str(settings), "--permission-mode", "bypassPermissions"]
    if a.model:
        cmd += ["--model", a.model]
    env = {**os.environ, "OTR_ISSUE": str(n), "OTR_SESSION": hexid}
    log = ROOT / "runs" / f"issue-{n}-{hexid}-{a.phase}.log"
    print(f"otr: spawning {branch} ({a.phase}) in {ws}\n     log: {log}")
    if a.dry_run:
        print(directive)
        return
    with log.open("w") as lf:
        rc = subprocess.run(cmd, cwd=ws, env=env, stdout=lf, stderr=subprocess.STDOUT).returncode
    rec = ws / f"docs/issue-{n}/reports/{hexid}.md"
    lint = subprocess.run([sys.executable, str(TOOLS / "record_lint.py"), str(rec.relative_to(ws))], cwd=ws, capture_output=True, text=True)
    print(f"otr: session exit {rc}; lint: {lint.stdout.strip() or lint.stderr.strip()}")
    print(f"     review: git log {MAIN}..{branch}  /  git diff {MAIN}...{branch}")
    print(f"     then:   otr approve {n} {hexid}   or   otr reject {n} {hexid} \"<reason>\"")


# ---------------------------------------------------------------- board

def frontmatter_of(text: str) -> dict[str, str]:
    sys.path.insert(0, str(TOOLS))
    from record_lint import parse_frontmatter
    fm, _ = parse_frontmatter(text)
    return fm or {}


def cmd_board(a: argparse.Namespace) -> None:
    files = git("ls-tree", "-r", "--name-only", MAIN).splitlines()
    issues: dict[str, dict] = {}
    for f in files:
        if m := re.match(r"docs/issue-(\d+)/issue\.md$", f):
            fm = frontmatter_of(git("show", f"{MAIN}:{f}"))
            issues.setdefault(m.group(1), {"title": fm.get("title", ""), "state": fm.get("state", "?"), "records": [], "approved": set()})
    for f in files:
        if m := re.match(r"docs/issue-(\d+)/reports/([0-9a-f]{8})\.md$", f):
            fm = frontmatter_of(git("show", f"{MAIN}:{f}"))
            issues[m.group(1)]["records"].append((m.group(2), fm.get("type", "?"), fm.get("loop_state", "?")))
        elif m := re.match(r"docs/issue-(\d+)/approvals/([0-9a-f]{8})\.md$", f):
            issues[m.group(1)]["approved"].add(m.group(2))
    branches = {b.strip() for b in git("branch", "--list", "issue-*/*").splitlines()}
    for n in sorted(issues, key=int):
        i = issues[n]
        print(f"issue-{n} [{i['state']}] {i['title']}")
        for hexid, typ, ls in i["records"]:
            print(f"    {hexid}  {typ:<14} {ls}")
        for b in sorted(b for b in branches if b.startswith(f"issue-{n}/")):
            hexid = b.split("/")[1]
            on_main = any(h == hexid for h, _, _ in i["records"])
            tag = "approved, awaiting delivery" if hexid in i["approved"] and not on_main else ("in flight" if not on_main else "landed")
            print(f"    branch {b}: {tag}")
    if not issues:
        print("no issues")


# ---------------------------------------------------------------- decisions

def cmd_approve(a: argparse.Namespace) -> None:
    require_clean_main()
    email = require_approver()
    branch = f"issue-{a.issue}/{a.hex}"
    if not git("branch", "--list", branch):
        sys.exit(f"otr: no branch {branch}")
    rec_path = f"docs/issue-{a.issue}/reports/{a.hex}.md"
    sha = git("rev-parse", branch)
    if not git("show", f"{branch}:{rec_path}", check=False):
        sys.exit(f"otr: {branch} has no proposal record at {rec_path}")
    p = ROOT / f"docs/issue-{a.issue}/approvals/{a.hex}.md"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(f"""---
issue: {a.issue}
approves: {a.hex}
proposal_sha: {sha}
approver: {email}
date: {date.today().isoformat()}
---

APPROVE issue-{a.issue}/{a.hex}

{a.note or ''}
""")
    git("add", str(p))
    git("commit", "-q", "-m", f"APPROVE issue-{a.issue}/{a.hex} at {sha[:8]}")
    print(f"approved {branch} at {sha[:8]} → otr spawn {a.issue} --phase delivery --session {a.hex}")


def cmd_accept(a: argparse.Namespace) -> None:
    require_clean_main()
    require_approver()
    branch = f"issue-{a.issue}/{a.hex}"
    rec_path = f"docs/issue-{a.issue}/reports/{a.hex}.md"
    text = git("show", f"{branch}:{rec_path}", check=False)
    if not text:
        sys.exit(f"otr: {branch} has no record at {rec_path}")
    fm = frontmatter_of(text)
    if fm.get("loop_state") not in ("landed", "done"):
        sys.exit(f"otr: record loop_state is {fm.get('loop_state')!r}, not landed/done")
    ws = WS / f"issue-{a.issue}-{a.hex}"
    if ws.exists():
        lint = subprocess.run([sys.executable, str(TOOLS / "record_lint.py"), rec_path], cwd=ws, capture_output=True, text=True)
        if lint.returncode:
            sys.exit("otr: record lint fails:\n" + lint.stdout)
    git("merge", "--no-ff", "-q", "-m", f"ACCEPT issue-{a.issue}/{a.hex}", branch)
    _set_issue_state(a.issue, "done")
    _cleanup(branch, ws)
    print(f"accepted {branch} into {MAIN}")


def cmd_reject(a: argparse.Namespace) -> None:
    require_clean_main()
    email = require_approver()
    branch = f"issue-{a.issue}/{a.hex}"
    sha = git("rev-parse", branch, check=False) or "unknown"
    p = ROOT / f"docs/issue-{a.issue}/rejections/{a.hex}.md"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(f"""---
issue: {a.issue}
rejects: {a.hex}
branch_sha: {sha}
approver: {email}
date: {date.today().isoformat()}
---

REJECT issue-{a.issue}/{a.hex}

{a.reason}
""")
    git("add", str(p))
    git("commit", "-q", "-m", f"REJECT issue-{a.issue}/{a.hex}: {a.reason[:60]}")
    _cleanup(branch, WS / f"issue-{a.issue}-{a.hex}", delete_branch=False)
    print(f"rejected {branch}; branch kept for reference (delete with git branch -D)")


def _set_issue_state(n: int, state: str) -> None:
    p = ROOT / f"docs/issue-{n}/issue.md"
    t = re.sub(r"^state: \w+", f"state: {state}", p.read_text(), count=1, flags=re.M)
    p.write_text(t)
    git("add", str(p))
    git("commit", "-q", "-m", f"issue-{n}: state {state}")


def _cleanup(branch: str, ws: Path, delete_branch: bool = True) -> None:
    if ws.exists():
        git("worktree", "remove", "--force", str(ws), check=False)
    if delete_branch:
        git("branch", "-d", branch, check=False)


def cmd_lint(a: argparse.Namespace) -> None:
    sys.exit(subprocess.run([sys.executable, str(TOOLS / "record_lint.py"), *([a.path] if a.path else [])]).returncode)


# ---------------------------------------------------------------- main

def main() -> None:
    ap = argparse.ArgumentParser(prog="otr", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sp = ap.add_subparsers(dest="cmd", required=True)
    p = sp.add_parser("issue"); p.add_argument("title"); p.set_defaults(fn=cmd_issue)
    p = sp.add_parser("spawn"); p.add_argument("issue", type=int); p.add_argument("task", nargs="?", default="")
    p.add_argument("--phase", choices=["proposal", "delivery"], default="proposal"); p.add_argument("--session")
    p.add_argument("--model"); p.add_argument("--dry-run", action="store_true"); p.set_defaults(fn=cmd_spawn)
    p = sp.add_parser("board"); p.set_defaults(fn=cmd_board)
    p = sp.add_parser("approve"); p.add_argument("issue", type=int); p.add_argument("hex"); p.add_argument("note", nargs="?"); p.set_defaults(fn=cmd_approve)
    p = sp.add_parser("accept"); p.add_argument("issue", type=int); p.add_argument("hex"); p.set_defaults(fn=cmd_accept)
    p = sp.add_parser("reject"); p.add_argument("issue", type=int); p.add_argument("hex"); p.add_argument("reason"); p.set_defaults(fn=cmd_reject)
    p = sp.add_parser("lint"); p.add_argument("path", nargs="?"); p.set_defaults(fn=cmd_lint)
    a = ap.parse_args()
    a.fn(a)


if __name__ == "__main__":
    main()
