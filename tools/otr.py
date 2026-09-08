#!/usr/bin/env python3
"""on-the-record, git-only edition.

Everything of record lives in git:
  requirement  docs/issue-<n>/issue.md               (human, on main)
  work         branch issue-<n>/<hex>                 (subagent)
  rationale    docs/issue-<n>/reports/<hex>.md        (session, on its branch)
  approval     docs/issue-<n>/approvals/<hex>.md      (human commit on main)
  acceptance   merge --no-ff into main                (human)
  rejection    docs/issue-<n>/rejections/<hex>.md     (human commit on main)
  delegation   docs/specs/delegation.md               (human commit on main; lets the
                                                       orchestrator approve/accept alone)

This tool never writes a record. It reads state, prints the directive a
subagent is spawned with (the orchestrator — the interactive Claude Code
session — passes it to the Agent tool), and relays the human's decisions
as commits.

Commands:
  issue "<title>"                 open docs/issue-<n>/issue.md, commit
  directive <n> "<task>" [--phase proposal|delivery] [--session <hex>]
                                  print the subagent prompt (new hex for proposal)
  board                           loop_state of every record on main
  approve <n> <hex> ["<note>"] [--via delegation]   commit approval on main
  accept <n> <hex> [--via delegation]               lint + principles + merge --no-ff
  delegate --until <ISO|+Nh|+Nd> [--issues 3,4|all] ["<note>"]
                                  grant standing delegation (human), commit on main
  revoke                          end the delegation now, commit on main
  delegation                      show whether a delegation is live
  reject <n> <hex> "<reason>"     commit rejection, delete branch
  lint [path]                     record lint
  clean [--all]                   remove worktrees/branches/scratch of finished sessions
  issue "<title>" --origin "<issue-n/hex deviation>"   open a follow-up issue from a deviation
"""
from __future__ import annotations
import argparse
import json
import re
import secrets
import shutil
import subprocess
import sys
import tempfile
from datetime import date, datetime, timedelta, timezone
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
    if a.origin:
        body = body.replace("state: open   # open | done | rejected", f"state: open   # open | done | rejected\norigin: {a.origin}")
    (d / "issue.md").write_text(body)
    (d / "reports/.gitkeep").write_text("")
    git("add", str(d))
    git("commit", "-q", "-m", f"issue-{n}: {a.title}")
    print(f"docs/issue-{n}/issue.md — fill in Need/Acceptance, then commit and `otr directive`")


# ---------------------------------------------------------------- directive

DIRECTIVE = """\
You are a subagent bound to issue-{n}, session id {hex}, in repository {root}.

FIRST, create your isolated working copy and branch (never work on main):
  {worktree_cmd}
  cd runs/ws/issue-{n}-{hex}{after_cd}
All work and every command below happens inside that directory.
Scratch files (probe repos, temp clones, logs) go ONLY under {root}/runs/scratch/issue-{n}-{hex}/
— never under /tmp or $HOME. Delete that directory before your final reply.

BEFORE ANYTHING ELSE read docs/specs/northpole.md (what this repo is for, verbatim) and every
`status: frozen` file in docs/decisions/ (`python3 tools/decisions.py` lists them). A change
that works against either is a deviation to record, never a judgment call to make.

TASK
{task}

PHASE: {phase}
{phase_rules}

RECORD
- Your record is docs/issue-{n}/reports/{hex}.md. Start from docs/templates/record.md
  (author: {hex}, issue: {n}). Write no other record. To correct another session's record,
  add `supersedes: <path>  # <reason>` or `amends: <path>#<section>  # <reason>` to yours.
- Order: change the code, run the checks, THEN write the record once from the executed
  results. Every claim cites the command and its output under ## Evidence. Bare counts
  ("all tests pass") without the command are not evidence.
- Before your final commit run `python3 tools/record_lint.py docs/issue-{n}/reports/{hex}.md`
  and fix everything it prints. Commit everything; leave no uncommitted changes.

PRINCIPLES
- Under ## Principles list `reaffirms <id>` for every frozen decision whose scope (path
  globs / keywords) your diff or record touches, or `none touched`. `otr accept` refuses a
  branch that touches a frozen scope without the matching line.

SCOPE
- The requirement is docs/issue-{n}/issue.md. Do not widen it. If finishing needs something
  outside it (another change, a judgment call, a risk), write it under ## Deviations in your
  record and stop — never start new work yourself.
- Never push, merge, switch to main, rebase, or delete branches. Landing is the human's act.
- Make a checkpoint commit BEFORE any long verification run; amend or follow up after.
- Nobody answers questions mid-run. Decide, record why, continue.

FINAL REPLY: the branch name, the record path, the record's `verdict:` line verbatim, and
the ## Deviations section verbatim (or "none").
"""

PHASE_RULES = {
    "proposal": """\
- Deliver a proposal only: what you will change, how, and how each ## Acceptance item in
  issue.md will be verified. No implementation beyond throwaway probes.
- Record: type: proposal, loop_state: proposed. Commit on your branch.""",
    "delivery": """\
- The proposal on this branch was approved (docs/issue-{n}/approvals/{hex}.md on main, now
  merged into your branch). Implement exactly it; deviations go under ## Deviations.
- Record: type: implementation (or verification/repair as fits), loop_state: landed,
  with ## Acceptance verification covering every item in issue.md.""",
}


def cmd_directive(a: argparse.Namespace) -> None:
    n = a.issue
    if not (ROOT / f"docs/issue-{n}/issue.md").exists():
        sys.exit(f"otr: docs/issue-{n}/issue.md not found — run `otr issue` first")
    hexid = a.session or secrets.token_hex(4)
    branch = f"issue-{n}/{hexid}"
    task = a.task
    if a.phase == "delivery":
        if not (ROOT / f"docs/issue-{n}/approvals/{hexid}.md").exists():
            sys.exit(f"otr: no approval on {MAIN} for {branch}; run `otr approve {n} {hexid}` first")
        if not git("branch", "--list", branch):
            sys.exit(f"otr: no branch {branch}")
        task = task or f"Implement the approved proposal in docs/issue-{n}/reports/{hexid}.md."
        worktree_cmd = f"[ -d runs/ws/issue-{n}-{hexid} ] || git worktree add runs/ws/issue-{n}-{hexid} {branch}"
        after_cd = f"\n  git merge --no-edit {MAIN}   # brings in the approval commit"
    else:
        if git("branch", "--list", branch):
            sys.exit(f"otr: branch {branch} already exists")
        if not task:
            sys.exit("otr: a task is required for a proposal")
        worktree_cmd = f"git worktree add -b {branch} runs/ws/issue-{n}-{hexid} {MAIN}"
        after_cd = ""
    WS.mkdir(parents=True, exist_ok=True)
    print(DIRECTIVE.format(n=n, hex=hexid, root=ROOT, worktree_cmd=worktree_cmd, after_cd=after_cd,
                           task=task, phase=a.phase, phase_rules=PHASE_RULES[a.phase].format(n=n, hex=hexid)))


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
    # for-each-ref (pattern needs */*: * does not cross /): `git branch --list` prefixes worktree-checked-out branches with `* `/`+ `
    branches = set(git("for-each-ref", "--format=%(refname:short)", "refs/heads/issue-*/*").splitlines())
    for n in sorted(issues, key=int):
        i = issues[n]
        print(f"issue-{n} [{i['state']}] {i['title']}")
        for hexid, typ, ls in i["records"]:
            print(f"    {hexid}  {typ:<14} {ls}")
        for b in sorted(b for b in branches if b.startswith(f"issue-{n}/")):
            hexid = b.split("/")[1]
            on_main = any(h == hexid for h, _, _ in i["records"])
            merged = subprocess.run(["git", "merge-base", "--is-ancestor", b, MAIN], cwd=ROOT, capture_output=True).returncode == 0
            if on_main and merged:
                print(f"    branch {b}: landed")
                continue
            text = git("show", f"{b}:docs/issue-{n}/reports/{hexid}.md", check=False)
            if text:
                fm = frontmatter_of(text)
                tag = f"{fm.get('type', '?')} {fm.get('loop_state', '?')}"
            else:
                tag = "no record"
            if hexid in i["approved"]:
                tag += ", approved"
            print(f"    branch {b}: {tag}")
    if not issues:
        print("no issues")


# ---------------------------------------------------------------- delegation

DELEG = ROOT / "docs/specs/delegation.md"


def _now() -> datetime:
    return datetime.now(timezone.utc).replace(microsecond=0)


def _parse_until(v: str) -> datetime:
    if m := re.match(r"^\+(\d+)([hd])$", v):
        return _now() + timedelta(**{"hours" if m.group(2) == "h" else "days": int(m.group(1))})
    d = datetime.fromisoformat(v)
    return d if d.tzinfo else d.replace(tzinfo=timezone.utc)


def delegation() -> dict | None:
    """The live grant from main, or None. Read from main, never the tree,
    so a revoke commit is honoured the moment it lands."""
    text = git("show", f"{MAIN}:docs/specs/delegation.md", check=False)
    if not text:
        return None
    fm = frontmatter_of(text)
    if fm.get("status") != "live":
        return None
    until = datetime.fromisoformat(fm["until"])
    if _now() > until:
        return None
    return {"until": until, "issues": fm.get("issues", "all"), "granted_by": fm.get("granted_by", "")}


def require_delegation(issue: int) -> dict:
    d = delegation()
    if not d:
        sys.exit("otr: no live delegation on main — ask the human, or `otr delegate --until ...`")
    if d["issues"] != "all" and str(issue) not in [x.strip() for x in d["issues"].split(",")]:
        sys.exit(f"otr: delegation covers issues {d['issues']}, not issue-{issue} — ask the human")
    return d


def cmd_delegate(a: argparse.Namespace) -> None:
    require_clean_main()
    email = require_approver()
    until = _parse_until(a.until)
    DELEG.write_text(f"""---
status: live
granted_by: {email}
granted: {_now().isoformat()}
until: {until.isoformat()}
issues: {a.issues}
---

# Standing delegation

While `status: live` and before `until`, the orchestrator may run
`otr approve --via delegation` and `otr accept --via delegation` on the
issues named above without a human turn. Every such act still lands as
its own commit naming this grant. `otr revoke` ends it; expiry ends it.

{a.note or ''}
""")
    git("add", str(DELEG))
    git("commit", "-q", "-m", f"DELEGATE {a.issues} UNTIL {until.isoformat()}")
    print(f"delegation live for issues={a.issues} until {until.isoformat()}")


def cmd_revoke(a: argparse.Namespace) -> None:
    require_clean_main()
    require_approver()
    if not DELEG.exists():
        sys.exit("otr: no delegation file")
    t = re.sub(r"^status: \w+", "status: revoked", DELEG.read_text(), count=1, flags=re.M)
    DELEG.write_text(t)
    git("add", str(DELEG))
    git("commit", "-q", "-m", f"REVOKE delegation at {_now().isoformat()}")
    print("delegation revoked")


def cmd_delegation(a: argparse.Namespace) -> None:
    d = delegation()
    print(f"live: issues={d['issues']} until {d['until'].isoformat()} (by {d['granted_by']})" if d else "none")


# ---------------------------------------------------------------- decisions

def cmd_approve(a: argparse.Namespace) -> None:
    require_clean_main()
    email = require_approver()
    via = f"delegation until {require_delegation(a.issue)['until'].isoformat()}" if a.via == "delegation" else "human turn"
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
via: {via}
date: {date.today().isoformat()}
---

APPROVE issue-{a.issue}/{a.hex}

{a.note or ''}
""")
    git("add", str(p))
    git("commit", "-q", "-m", f"APPROVE issue-{a.issue}/{a.hex} at {sha[:8]}" + (" VIA DELEGATION" if a.via else ""))
    print(f"approved {branch} at {sha[:8]} → otr directive {a.issue} --phase delivery --session {a.hex}")


def cmd_accept(a: argparse.Namespace) -> None:
    require_clean_main()
    require_approver()
    via = " VIA DELEGATION" if a.via == "delegation" else ""
    if a.via == "delegation":
        require_delegation(a.issue)
    branch = f"issue-{a.issue}/{a.hex}"
    rec_path = f"docs/issue-{a.issue}/reports/{a.hex}.md"
    text = git("show", f"{branch}:{rec_path}", check=False)
    if not text:
        sys.exit(f"otr: {branch} has no record at {rec_path}")
    fm = frontmatter_of(text)
    if fm.get("loop_state") not in ("landed", "done"):
        sys.exit(f"otr: record loop_state is {fm.get('loop_state')!r}, not landed/done")
    ws = WS / f"issue-{a.issue}-{a.hex}"
    WS.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=str(WS)) as td:
        subprocess.run(["git", "worktree", "add", "-q", "--detach", td, branch], cwd=ROOT, check=True)
        try:
            lint = subprocess.run([sys.executable, str(TOOLS / "record_lint.py"), rec_path], cwd=td, capture_output=True, text=True)
        finally:
            git("worktree", "remove", "--force", td, check=False)
    if lint.returncode:
        sys.exit("otr: record lint fails:\n" + lint.stdout)
    _require_principles(branch, text)
    git("merge", "--no-ff", "-q", "-m", f"ACCEPT issue-{a.issue}/{a.hex}{via}", branch)
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
    _cleanup(branch, WS / f"issue-{a.issue}-{a.hex}")
    print(f"rejected {branch} (recorded at {sha[:8]} in {p.relative_to(ROOT)}); branch and worktree removed")


def _require_principles(branch: str, record_text: str) -> None:
    """A branch touching a frozen decision's scope must carry `reaffirms <id>`
    in its record (docs/decisions/README.md). Mechanical only: whether the
    change actually honours the principle is the human's read of the diff."""
    sys.path.insert(0, str(TOOLS))
    import decisions
    paths = git("diff", "--name-only", f"{MAIN}...{branch}").splitlines()
    missing = [(d, why) for d, why in decisions.touched(paths, record_text)
               if not re.search(rf"reaffirms\s+{re.escape(d.id)}\b", record_text)]
    if missing:
        lines = [f"  {d.id}  ({why})  — {d.path.relative_to(ROOT)}" for d, why in missing]
        sys.exit("otr: branch touches frozen decision(s) with no `reaffirms <id>` under ## Principles:\n" + "\n".join(lines))


def _set_issue_state(n: int, state: str) -> None:
    p = ROOT / f"docs/issue-{n}/issue.md"
    t = re.sub(r"^state: \w+", f"state: {state}", p.read_text(), count=1, flags=re.M)
    p.write_text(t)
    git("add", str(p))
    git("commit", "-q", "-m", f"issue-{n}: state {state}")


def _cleanup(branch: str, ws: Path, delete_branch: bool = True) -> None:
    if ws.exists():
        git("worktree", "remove", "--force", str(ws), check=False)
    git("worktree", "prune")
    shutil.rmtree(ROOT / "runs" / "scratch" / ws.name, ignore_errors=True)
    if delete_branch:
        git("branch", "-D", branch, check=False)


def cmd_clean(a: argparse.Namespace) -> None:
    """Remove every leftover of finished (accepted or rejected) sessions, and
    with --all also of in-flight ones (a crashed subagent leaves its worktree
    and branch behind). Records on main are never touched."""
    git("worktree", "prune")
    finished = set()
    for f in git("ls-tree", "-r", "--name-only", MAIN).splitlines():
        if m := re.match(r"docs/issue-(\d+)/(reports|rejections)/([0-9a-f]{8})\.md$", f):
            finished.add(f"issue-{m.group(1)}-{m.group(3)}")
    removed = []
    for d in list((WS).glob("issue-*-*")) + list((ROOT / "runs" / "scratch").glob("issue-*-*")):
        if a.all or d.name in finished:
            if d.parent == WS:
                git("worktree", "remove", "--force", str(d), check=False)
            shutil.rmtree(d, ignore_errors=True)
            removed.append(str(d.relative_to(ROOT)))
    for b in git("for-each-ref", "--format=%(refname:short)", "refs/heads/issue-*/*").splitlines():
        n, hexid = b.split("/")
        if a.all or f"{n}-{hexid}" in finished:
            git("branch", "-D", b, check=False)
            removed.append(f"branch {b}")
    for stray in list(WS.glob("*.json")) + list((ROOT / "runs").glob("*.log")):
        stray.unlink()
        removed.append(str(stray.relative_to(ROOT)))
    shutil.rmtree(ROOT / "tools" / "__pycache__", ignore_errors=True)
    print("\n".join(removed) if removed else "nothing to clean")
    left = [p.name for p in WS.glob("issue-*-*")]
    if left:
        print("in flight (kept; use --all to force):", ", ".join(left))


def cmd_lint(a: argparse.Namespace) -> None:
    sys.exit(subprocess.run([sys.executable, str(TOOLS / "record_lint.py"), *([a.path] if a.path else [])]).returncode)


# ---------------------------------------------------------------- main

def main() -> None:
    ap = argparse.ArgumentParser(prog="otr", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sp = ap.add_subparsers(dest="cmd", required=True)
    p = sp.add_parser("issue"); p.add_argument("title"); p.add_argument("--origin"); p.set_defaults(fn=cmd_issue)
    p = sp.add_parser("directive"); p.add_argument("issue", type=int); p.add_argument("task", nargs="?", default="")
    p.add_argument("--phase", choices=["proposal", "delivery"], default="proposal"); p.add_argument("--session"); p.set_defaults(fn=cmd_directive)
    p = sp.add_parser("board"); p.set_defaults(fn=cmd_board)
    p = sp.add_parser("approve"); p.add_argument("issue", type=int); p.add_argument("hex"); p.add_argument("note", nargs="?"); p.add_argument("--via", choices=["delegation"]); p.set_defaults(fn=cmd_approve)
    p = sp.add_parser("accept"); p.add_argument("issue", type=int); p.add_argument("hex"); p.add_argument("--via", choices=["delegation"]); p.set_defaults(fn=cmd_accept)
    p = sp.add_parser("delegate"); p.add_argument("--until", required=True); p.add_argument("--issues", default="all"); p.add_argument("note", nargs="?"); p.set_defaults(fn=cmd_delegate)
    p = sp.add_parser("revoke"); p.set_defaults(fn=cmd_revoke)
    p = sp.add_parser("delegation"); p.set_defaults(fn=cmd_delegation)
    p = sp.add_parser("reject"); p.add_argument("issue", type=int); p.add_argument("hex"); p.add_argument("reason"); p.set_defaults(fn=cmd_reject)
    p = sp.add_parser("clean"); p.add_argument("--all", action="store_true"); p.set_defaults(fn=cmd_clean)
    p = sp.add_parser("lint"); p.add_argument("path", nargs="?"); p.set_defaults(fn=cmd_lint)
    a = ap.parse_args()
    a.fn(a)


if __name__ == "__main__":
    main()
