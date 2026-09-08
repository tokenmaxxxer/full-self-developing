#!/usr/bin/env python3
"""on-the-record, GitHub edition.

GitHub is the ledger; the orchestrator is its only writer.

  requirement  GitHub issue #n                          (orchestrator relays the human)
  work         branch issue-<n>/<hex>, local worktree   (subagent — never touches GitHub)
  rationale    docs/issue-<n>/reports/<hex>.md          (subagent, on its branch)
  publish      push + PR for issue-<n>/<hex>            (orchestrator, after reading it)
  approval     issue comment `APPROVE issue-<n>/<hex>`  (orchestrator relays the human)
  acceptance   PR merge; rejection: PR close + comment  (orchestrator relays the human)
  delegation   comment `DELEGATE <scope> UNTIL <iso>` / `REVOKE` on the pinned
               "delegation" issue                       (orchestrator relays the human)

The repo is the one `origin` fetches from. Records, north pole and decisions
are files in the repo and reach GitHub when their branch is pushed.

Commands:
  init                                 approvers / decisions README / north pole / .gitignore
  issue "<title>" --body "<md>" [--origin "<issue-n/hex deviation>"]   create the GitHub issue
  directive <n> "<task>" [--phase proposal|delivery] [--session <hex>]  print the subagent prompt
  publish <n> <hex>                    push the branch, open or update its PR
  approve <n> <hex> ["<note>"] [--via delegation]
  accept <n> <hex> [--via delegation]  gates + merge PR + close issue + local cleanup
  reject <n> <hex> "<reason>"          close PR with the reason + local cleanup
  delegate --until <ISO|+Nh|+Nd> [--issues 3,4|all] ["<note>"] / revoke / delegation
  board                                open issues, their branches/PRs, record state
  clean [--all]                        local leftovers of finished (or, --all, any) sessions
  lint [path]                          record lint
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
from datetime import datetime, timedelta, timezone
from pathlib import Path

_top = subprocess.run(["git", "rev-parse", "--show-toplevel"], capture_output=True, text=True)
if _top.returncode:
    sys.exit("otr: not inside a git repository")
ROOT = Path(_top.stdout.strip())
TOOLS = Path(__file__).resolve().parent
PKG = TOOLS.parent
WS = ROOT / "runs" / "ws"
MAIN = "main"


def git(*args: str, cwd: Path = ROOT, check: bool = True) -> str:
    return subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True, check=check).stdout.strip()


def gh(*args: str, check: bool = True) -> str:
    r = subprocess.run(["gh", *args, "-R", REPO], cwd=ROOT, capture_output=True, text=True)
    if r.returncode and check:
        sys.exit(f"otr: gh {' '.join(args[:2])} failed: {r.stderr.strip()}")
    return r.stdout.strip()


def gh_json(*args: str):
    out = gh(*args)
    return json.loads(out) if out else None


def _repo_from_origin() -> str:
    url = git("remote", "get-url", "origin", check=False)
    m = re.search(r"github\.com[:/]([^/]+/[^/.]+)", url)
    if not m:
        sys.exit("otr: origin is not a GitHub remote")
    return m.group(1)


REPO = _repo_from_origin()


def _now() -> datetime:
    return datetime.now(timezone.utc).replace(microsecond=0)


def require_clean_main() -> None:
    if git("branch", "--show-current") != MAIN:
        sys.exit(f"otr: run this on {MAIN}")
    if git("status", "--porcelain"):
        sys.exit("otr: working tree is dirty; commit or stash first")


def approvers() -> set[str]:
    p = ROOT / "docs/specs/approvers.md"
    if not p.exists():
        sys.exit("otr: docs/specs/approvers.md missing — run `otr init`")
    return {l.strip().lstrip("@") for l in p.read_text().splitlines() if l.strip() and not l.startswith("#") and " " not in l.strip()}


def me() -> str:
    return subprocess.run(["gh", "api", "user", "--jq", ".login"], capture_output=True, text=True).stdout.strip()


def require_approver() -> str:
    login = me()
    if login not in approvers():
        sys.exit(f"otr: @{login} is not in docs/specs/approvers.md")
    return login


def frontmatter_of(text: str) -> dict[str, str]:
    sys.path.insert(0, str(TOOLS))
    from record_lint import parse_frontmatter
    fm, _ = parse_frontmatter(text)
    return fm or {}


# ---------------------------------------------------------------- init

def cmd_init(a: argparse.Namespace) -> None:
    login = me() or "<github-login>"
    made = []

    def put(rel: str, text: str) -> None:
        p = ROOT / rel
        if p.exists():
            return
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text)
        made.append(rel)

    today = _now().date().isoformat()
    put("docs/specs/approvers.md", f"# Approvers\n\nOne GitHub login per line. Only these may approve, accept, reject, delegate.\n\n{login}\n")
    put("docs/decisions/README.md", (PKG / "docs/decisions/README.md").read_text())
    put("docs/specs/northpole.md", f"# North pole\n\nWhat this repository is for, as currently understood. Edited in place as\nthinking changes; history is `git log -p` on this file.\n\n## N0 — \n\n- since {today} · revised {today}\n- served by: GAP\n")
    gi = ROOT / ".gitignore"
    if "runs/" not in (gi.read_text() if gi.exists() else ""):
        with gi.open("a") as f:
            f.write("runs/\n")
        made.append(".gitignore")
    if made:
        git("add", *made)
        git("commit", "-q", "-m", "otr init: approvers, decisions, north pole")
        print("initialised:", ", ".join(made), "— push when ready")
    else:
        print("already initialised")


# ---------------------------------------------------------------- issue

ISSUE_BODY = """\
## Need

{need}

## Acceptance

{acceptance}

## Out of scope

{out_of_scope}
"""


def cmd_issue(a: argparse.Namespace) -> None:
    body = a.body
    if a.origin:
        body = f"origin: {a.origin}\n\n" + body
    n = gh("issue", "create", "--title", a.title, "--body", body).rsplit("/", 1)[-1]
    print(f"issue #{n} — {REPO}/issues/{n}")


def issue_view(n: int) -> dict:
    d = gh_json("issue", "view", str(n), "--json", "number,title,body,state,comments")
    if not d:
        sys.exit(f"otr: issue #{n} not found in {REPO}")
    return d


def approval_comment(n: int, hexid: str) -> dict | None:
    """The first APPROVE comment for this session by an approver, or None."""
    ok = approvers()
    for c in issue_view(n)["comments"]:
        body = c["body"].strip()
        if re.match(rf"^APPROVE issue-{n}/{hexid}\b", body) and c["author"]["login"] in ok:
            return c
    return None


# ---------------------------------------------------------------- directive

DIRECTIVE = """\
You are a subagent bound to issue #{n}, session id {hex}, in repository {root}
(GitHub: {repo}). You never talk to GitHub: no gh, no push, no PR. The orchestrator
publishes your branch after reading it.

FIRST, create your isolated working copy and branch (never work on main):
  {worktree_cmd}
  cd runs/ws/issue-{n}-{hex}{after_cd}
All work and every command below happens inside that directory.
Scratch files (probe repos, temp clones, logs) go ONLY under {root}/runs/scratch/issue-{n}-{hex}/
— never under /tmp or $HOME. Delete that directory before your final reply.

BEFORE ANYTHING ELSE read docs/specs/northpole.md (what this repo is for) and every
`status: frozen` file in docs/decisions/ (`python3 {tools}/decisions.py` lists them). A change
that works against either is a deviation to record, never a judgment call to make.

ISSUE #{n} — {title}
{body}

TASK
{task}

PHASE: {phase}
{phase_rules}

RECORD
- Your record is docs/issue-{n}/reports/{hex}.md. Start from {pkg}/docs/templates/record.md
  (author: {hex}, issue: {n}). Write no other record. To correct another session's record,
  add `supersedes: <path>  # <reason>` or `amends: <path>#<section>  # <reason>` to yours.
- Order: change the code, run the checks, THEN write the record once from the executed
  results. Every claim cites the command and its output under ## Evidence. Bare counts
  ("all tests pass") without the command are not evidence.
- Before your final commit run `python3 {tools}/record_lint.py docs/issue-{n}/reports/{hex}.md`
  and fix everything it prints. Commit everything; leave no uncommitted changes.

PRINCIPLES
- Under ## Principles list `reaffirms <id>` for every frozen decision whose scope (path
  globs / keywords) your diff or record touches, or `none touched`.

SCOPE
- The requirement is the issue text above. Do not widen it. If finishing needs something
  outside it (another change, a judgment call, a risk), write it under ## Deviations in your
  record and stop — never start new work yourself.
- Never push, merge, switch to main, rebase, force anything, or delete branches.
- Make a checkpoint commit BEFORE any long verification run; amend or follow up after.
- Nobody answers questions mid-run. Decide, record why, continue.

FINAL REPLY: the branch name, the record path, the record's `verdict:` line verbatim, and
the ## Deviations section verbatim (or "none").
"""

PHASE_RULES = {
    "proposal": """\
- Deliver a proposal only: what you will change, how, and how each Acceptance item of the
  issue will be verified. No implementation beyond throwaway probes.
- Record: type: proposal, loop_state: proposed. Commit on your branch.""",
    "delivery": """\
- The proposal on this branch was approved on the issue. Implement exactly it; deviations
  go under ## Deviations.
- Record: rewrite it as type: implementation (or verification/repair as fits),
  loop_state: landed, with ## Acceptance verification covering every Acceptance item.""",
}


def cmd_directive(a: argparse.Namespace) -> None:
    n = a.issue
    issue = issue_view(n)
    hexid = a.session or secrets.token_hex(4)
    branch = f"issue-{n}/{hexid}"
    task = a.task
    if a.phase == "delivery":
        if not approval_comment(n, hexid):
            sys.exit(f"otr: no `APPROVE issue-{n}/{hexid}` comment by an approver on #{n}")
        if not git("branch", "--list", branch):
            sys.exit(f"otr: no local branch {branch}")
        task = task or f"Implement the approved proposal in docs/issue-{n}/reports/{hexid}.md."
        worktree_cmd = f"[ -d runs/ws/issue-{n}-{hexid} ] || git worktree add runs/ws/issue-{n}-{hexid} {branch}"
        after_cd = f"\n  git merge --no-edit {MAIN}   # pick up anything landed since your proposal"
    else:
        if git("branch", "--list", branch):
            sys.exit(f"otr: branch {branch} already exists")
        if not task:
            sys.exit("otr: a task is required for a proposal")
        worktree_cmd = f"git worktree add -b {branch} runs/ws/issue-{n}-{hexid} {MAIN}"
        after_cd = ""
    WS.mkdir(parents=True, exist_ok=True)
    print(DIRECTIVE.format(n=n, hex=hexid, root=ROOT, repo=REPO, tools=TOOLS, pkg=PKG,
                           worktree_cmd=worktree_cmd, after_cd=after_cd, title=issue["title"],
                           body=issue["body"].strip(), task=task, phase=a.phase,
                           phase_rules=PHASE_RULES[a.phase]))


# ---------------------------------------------------------------- publish

def record_on(branch: str, n: int, hexid: str) -> str:
    return git("show", f"{branch}:docs/issue-{n}/reports/{hexid}.md", check=False)


def pr_for(branch: str) -> dict | None:
    prs = gh_json("pr", "list", "--head", branch, "--state", "all", "--json", "number,state,url,headRefName") or []
    return prs[0] if prs else None


def cmd_publish(a: argparse.Namespace) -> None:
    n, hexid = a.issue, a.hex
    branch = f"issue-{n}/{hexid}"
    text = record_on(branch, n, hexid)
    if not text:
        sys.exit(f"otr: {branch} has no record at docs/issue-{n}/reports/{hexid}.md")
    fm = frontmatter_of(text)
    git("push", "-q", "-u", "origin", branch)
    pr = pr_for(branch)
    summary = (f"Closes #{n}\n\n**{fm.get('type', '?')} · {fm.get('loop_state', '?')}**\n\n"
               f"{fm.get('verdict', '')}\n\nRecord: `docs/issue-{n}/reports/{hexid}.md`")
    if pr and pr["state"] == "OPEN":
        gh("pr", "edit", str(pr["number"]), "--body", summary)
        gh("pr", "comment", str(pr["number"]), "--body", f"Updated: {fm.get('type', '?')} · {fm.get('loop_state', '?')} · {git('rev-parse', '--short', branch)}")
        print(f"updated PR #{pr['number']} {pr['url']}")
    else:
        url = gh("pr", "create", "--base", MAIN, "--head", branch, "--title", f"issue-{n}/{hexid}: {issue_view(n)['title']}", "--body", summary)
        print(f"opened PR {url}")


# ---------------------------------------------------------------- delegation

def delegation_issue() -> int:
    for i in gh_json("issue", "list", "--state", "all", "--limit", "200", "--json", "number,title") or []:
        if i["title"] == "delegation":  # oldest wins; list is newest-first
            found = i["number"]
    if "found" in locals():
        return found
    url = gh("issue", "create", "--title", "delegation", "--body",
             "Standing delegation lives here as comments: `DELEGATE <issues|all> UNTIL <iso>` and `REVOKE`. "
             "The orchestrator reads the latest comment by an approver.")
    return int(url.rsplit("/", 1)[-1])


def delegation() -> dict | None:
    ok = approvers()
    live = None
    for c in issue_view(delegation_issue())["comments"]:
        if c["author"]["login"] not in ok:
            continue
        body = c["body"].strip()
        if body.startswith("REVOKE"):
            live = None
        elif m := re.match(r"^DELEGATE\s+(\S+)\s+UNTIL\s+(\S+)", body):
            live = {"issues": m.group(1), "until": datetime.fromisoformat(m.group(2)), "by": c["author"]["login"]}
    if live and _now() > live["until"]:
        return None
    return live


def require_delegation(issue: int) -> dict:
    d = delegation()
    if not d:
        sys.exit("otr: no live delegation — ask the human, or `otr delegate --until ...` on their word")
    if d["issues"] != "all" and str(issue) not in d["issues"].split(","):
        sys.exit(f"otr: delegation covers {d['issues']}, not #{issue} — ask the human")
    return d


def _parse_until(v: str) -> datetime:
    if m := re.match(r"^\+(\d+)([hd])$", v):
        return _now() + timedelta(**{"hours" if m.group(2) == "h" else "days": int(m.group(1))})
    d = datetime.fromisoformat(v)
    return d if d.tzinfo else d.replace(tzinfo=timezone.utc)


def cmd_delegate(a: argparse.Namespace) -> None:
    require_approver()
    until = _parse_until(a.until).isoformat()
    gh("issue", "comment", str(delegation_issue()), "--body", f"DELEGATE {a.issues} UNTIL {until}\n\n{a.note or ''}")
    print(f"delegation live for {a.issues} until {until}")


def cmd_revoke(a: argparse.Namespace) -> None:
    require_approver()
    gh("issue", "comment", str(delegation_issue()), "--body", f"REVOKE at {_now().isoformat()}")
    print("delegation revoked")


def cmd_delegation(a: argparse.Namespace) -> None:
    d = delegation()
    print(f"live: {d['issues']} until {d['until'].isoformat()} (by @{d['by']})" if d else "none")


# ---------------------------------------------------------------- decisions

def cmd_approve(a: argparse.Namespace) -> None:
    login = require_approver()
    branch = f"issue-{a.issue}/{a.hex}"
    if not record_on(branch, a.issue, a.hex) and not pr_for(branch):
        sys.exit(f"otr: nothing published for {branch}")
    via = ""
    if a.via == "delegation":
        d = require_delegation(a.issue)
        via = f" VIA DELEGATION until {d['until'].isoformat()}"
    sha = git("rev-parse", "--short", branch, check=False) or "?"
    gh("issue", "comment", str(a.issue), "--body", f"APPROVE issue-{a.issue}/{a.hex}{via}\n\nat {sha}\n\n{a.note or ''}")
    print(f"approved {branch} at {sha} → otr directive {a.issue} --phase delivery --session {a.hex}")


def _require_principles(branch: str, record_text: str) -> None:
    sys.path.insert(0, str(TOOLS))
    import decisions
    paths = git("diff", "--name-only", f"{MAIN}...{branch}").splitlines()
    missing = [(d, why) for d, why in decisions.touched(paths, record_text)
               if not re.search(rf"reaffirms\s+{re.escape(d.id)}\b", record_text)]
    if missing:
        lines = [f"  {d.id}  ({why})  — {d.path.relative_to(ROOT)}" for d, why in missing]
        sys.exit("otr: branch touches frozen decision(s) with no `reaffirms <id>` under ## Principles:\n" + "\n".join(lines))


def _lint_on_branch(branch: str, rec_path: str) -> None:
    WS.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=str(WS)) as td:
        subprocess.run(["git", "worktree", "add", "-q", "--detach", td, branch], cwd=ROOT, check=True)
        try:
            lint = subprocess.run([sys.executable, str(TOOLS / "record_lint.py"), rec_path], cwd=td, capture_output=True, text=True)
        finally:
            git("worktree", "remove", "--force", td, check=False)
    if lint.returncode:
        sys.exit("otr: record lint fails:\n" + lint.stdout)


def cmd_accept(a: argparse.Namespace) -> None:
    require_clean_main()
    require_approver()
    n, hexid = a.issue, a.hex
    branch = f"issue-{n}/{hexid}"
    via = ""
    if a.via == "delegation":
        via = f" VIA DELEGATION until {require_delegation(n)['until'].isoformat()}"
    text = record_on(branch, n, hexid)
    if not text:
        sys.exit(f"otr: {branch} has no record")
    fm = frontmatter_of(text)
    if fm.get("loop_state") not in ("landed", "done"):
        sys.exit(f"otr: record loop_state is {fm.get('loop_state')!r}, not landed/done")
    _lint_on_branch(branch, f"docs/issue-{n}/reports/{hexid}.md")
    _require_principles(branch, text)
    pr = pr_for(branch)
    if not pr or pr["state"] != "OPEN":
        sys.exit(f"otr: no open PR for {branch} — `otr publish {n} {hexid}` first")
    git("push", "-q", "origin", branch)  # make sure the PR has the latest commits
    gh("pr", "merge", str(pr["number"]), "--merge", "--delete-branch", "--subject", f"ACCEPT issue-{n}/{hexid}{via}")
    git("pull", "-q", "--ff-only", "origin", MAIN)
    if issue_view(n)["state"] == "OPEN":
        gh("issue", "close", str(n), "--comment", f"ACCEPT issue-{n}/{hexid}{via} — PR #{pr['number']} merged")
    _cleanup(branch, WS / f"issue-{n}-{hexid}")
    print(f"accepted {branch}: PR #{pr['number']} merged, #{n} closed")


def cmd_reject(a: argparse.Namespace) -> None:
    require_approver()
    n, hexid = a.issue, a.hex
    branch = f"issue-{n}/{hexid}"
    pr = pr_for(branch)
    if pr and pr["state"] == "OPEN":
        gh("pr", "close", str(pr["number"]), "--comment", f"REJECT issue-{n}/{hexid}\n\n{a.reason}", "--delete-branch")
    else:
        gh("issue", "comment", str(n), "--body", f"REJECT issue-{n}/{hexid} (never published)\n\n{a.reason}")
    _cleanup(branch, WS / f"issue-{n}-{hexid}")
    print(f"rejected {branch}")


def _cleanup(branch: str, ws: Path) -> None:
    if ws.exists():
        git("worktree", "remove", "--force", str(ws), check=False)
    git("worktree", "prune")
    shutil.rmtree(ROOT / "runs" / "scratch" / ws.name, ignore_errors=True)
    git("branch", "-D", branch, check=False)


# ---------------------------------------------------------------- board

def cmd_board(a: argparse.Namespace) -> None:
    issues = gh_json("issue", "list", "--state", "open", "--json", "number,title,comments") or []
    prs = {p["headRefName"]: p for p in gh_json("pr", "list", "--state", "open", "--json", "number,headRefName,url") or []}
    local = set(git("for-each-ref", "--format=%(refname:short)", "refs/heads/issue-*/*").splitlines())
    ok = approvers()
    for i in sorted(issues, key=lambda x: x["number"]):
        if i["title"] == "delegation":
            continue
        n = i["number"]
        print(f"#{n} {i['title']}")
        approved = {m.group(1) for c in i["comments"] if c["author"]["login"] in ok
                    for m in [re.match(rf"^APPROVE issue-{n}/([0-9a-f]{{8}})", c["body"].strip())] if m}
        branches = sorted({b for b in local if b.startswith(f"issue-{n}/")} | {b for b in prs if b.startswith(f"issue-{n}/")})
        for b in branches:
            hexid = b.split("/")[1]
            text = git("show", f"{b}:docs/issue-{n}/reports/{hexid}.md", check=False) if b in local else ""
            fm = frontmatter_of(text) if text else {}
            tag = f"{fm.get('type', '?')} {fm.get('loop_state', '?')}" if text else "no local record"
            if b in prs:
                tag += f", PR #{prs[b]['number']}"
            if hexid in approved:
                tag += ", approved"
            print(f"    {b}: {tag}")
    if not issues:
        print("no open issues")
    d = delegation()
    print(f"delegation: {d['issues']} until {d['until'].isoformat()}" if d else "delegation: none")


# ---------------------------------------------------------------- clean

def cmd_clean(a: argparse.Namespace) -> None:
    git("worktree", "prune")
    open_prs = {p["headRefName"] for p in gh_json("pr", "list", "--state", "open", "--json", "headRefName") or []}
    removed = []
    for b in git("for-each-ref", "--format=%(refname:short)", "refs/heads/issue-*/*").splitlines():
        n, hexid = b.split("/")
        merged = subprocess.run(["git", "merge-base", "--is-ancestor", b, MAIN], cwd=ROOT).returncode == 0
        if a.all or (merged and b not in open_prs):
            _cleanup(b, WS / f"{n}-{hexid}")
            removed.append(f"branch {b}")
    for d in list(WS.glob("issue-*-*")) + list((ROOT / "runs" / "scratch").glob("issue-*-*")):
        if a.all or f"{d.name[6:].replace('-', '/', 1)}" not in local_branches():
            if d.parent == WS:
                git("worktree", "remove", "--force", str(d), check=False)
            shutil.rmtree(d, ignore_errors=True)
            removed.append(str(d.relative_to(ROOT)))
    shutil.rmtree(ROOT / "tools" / "__pycache__", ignore_errors=True)
    print("\n".join(removed) if removed else "nothing to clean")


def local_branches() -> set[str]:
    return set(git("for-each-ref", "--format=%(refname:short)", "refs/heads/issue-*/*").splitlines())


def cmd_lint(a: argparse.Namespace) -> None:
    sys.exit(subprocess.run([sys.executable, str(TOOLS / "record_lint.py"), *([a.path] if a.path else [])]).returncode)


# ---------------------------------------------------------------- main

def main() -> None:
    ap = argparse.ArgumentParser(prog="otr", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sp = ap.add_subparsers(dest="cmd", required=True)
    p = sp.add_parser("init"); p.set_defaults(fn=cmd_init)
    p = sp.add_parser("issue"); p.add_argument("title"); p.add_argument("--body", required=True); p.add_argument("--origin"); p.set_defaults(fn=cmd_issue)
    p = sp.add_parser("directive"); p.add_argument("issue", type=int); p.add_argument("task", nargs="?", default="")
    p.add_argument("--phase", choices=["proposal", "delivery"], default="proposal"); p.add_argument("--session"); p.set_defaults(fn=cmd_directive)
    p = sp.add_parser("publish"); p.add_argument("issue", type=int); p.add_argument("hex"); p.set_defaults(fn=cmd_publish)
    p = sp.add_parser("approve"); p.add_argument("issue", type=int); p.add_argument("hex"); p.add_argument("note", nargs="?"); p.add_argument("--via", choices=["delegation"]); p.set_defaults(fn=cmd_approve)
    p = sp.add_parser("accept"); p.add_argument("issue", type=int); p.add_argument("hex"); p.add_argument("--via", choices=["delegation"]); p.set_defaults(fn=cmd_accept)
    p = sp.add_parser("reject"); p.add_argument("issue", type=int); p.add_argument("hex"); p.add_argument("reason"); p.set_defaults(fn=cmd_reject)
    p = sp.add_parser("delegate"); p.add_argument("--until", required=True); p.add_argument("--issues", default="all"); p.add_argument("note", nargs="?"); p.set_defaults(fn=cmd_delegate)
    p = sp.add_parser("revoke"); p.set_defaults(fn=cmd_revoke)
    p = sp.add_parser("delegation"); p.set_defaults(fn=cmd_delegation)
    p = sp.add_parser("board"); p.set_defaults(fn=cmd_board)
    p = sp.add_parser("clean"); p.add_argument("--all", action="store_true"); p.set_defaults(fn=cmd_clean)
    p = sp.add_parser("lint"); p.add_argument("path", nargs="?"); p.set_defaults(fn=cmd_lint)
    a = ap.parse_args()
    a.fn(a)


if __name__ == "__main__":
    main()
