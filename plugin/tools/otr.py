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
from fnmatch import fnmatch
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
    r = subprocess.run(["gh", *args, "-R", str(REPO)], cwd=ROOT, capture_output=True, text=True)
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


class _Lazy(str):
    """Resolved on first use so `otr init`/`lint` work before origin exists."""
    def __new__(cls):
        return super().__new__(cls, "")
    def __str__(self):
        return _repo_from_origin()
    __repr__ = __str__


REPO = _Lazy()


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


def record_body_of(text: str) -> str:
    sys.path.insert(0, str(TOOLS))
    from record_lint import parse_frontmatter
    _, body = parse_frontmatter(text)
    return body


def extract_section(body: str, header: str) -> str:
    """Text of a `## Header` section up to the next `## ` or end, stripped."""
    sys.path.insert(0, str(TOOLS))
    from record_lint import find_section
    i = find_section(body, header)
    if i < 0:
        return ""
    rest = body[i + len(header):]
    j = rest.find("\n## ")
    return (rest if j < 0 else rest[:j]).strip()


def set_section(body: str, header: str, content: str) -> str:
    """Replace a `## Header` section's content in place, or append it if absent."""
    sys.path.insert(0, str(TOOLS))
    from record_lint import find_section
    block = f"{header}\n\n{content}\n"
    i = find_section(body, header)
    if i < 0:
        return body.rstrip() + "\n\n" + block
    rest = body[i + len(header):]
    j = rest.find("\n## ")
    tail = "" if j < 0 else rest[j:]
    return body[:i] + block + tail


# ---------------------------------------------------------------- init

def cmd_init(a: argparse.Namespace) -> None:
    login = me()
    if not login:
        sys.exit("otr: `gh api user` returned nothing — log in with `gh auth login` (as the account that will approve) and rerun")
    made = []

    def put(rel: str, text: str) -> None:
        p = ROOT / rel
        if p.exists():
            return
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text)
        made.append(rel)

    today = _now().date().isoformat()
    put("docs/specs/approvers.md", f"# Approvers\n\nOne GitHub login per line. Only these may approve, accept, reject, delegate.\nWritten by `otr init` from `gh api user`; add a line only for a person you mean.\n\n{login}\n")
    put("docs/decisions/README.md", (PKG / "templates/decisions-README.md").read_text())
    put("docs/specs/northpole.md", (
        "# North pole\n\n"
        "What the human has decided for this repository. Five sections, each holding\n"
        "only the human's own words. Edited in place as thinking changes; history is\n"
        "`git log -p` on this file.\n\n"
        "## Problem\n\n"
        "(which problem, and why — the human's own words)\n\n"
        f"- since {today} · revised {today}\n\n"
        "## Watch for\n\n"
        "(what could go wrong or be overdone as work proceeds)\n\n"
        f"- since {today} · revised {today}\n\n"
        "## Constraints\n\n"
        "(what may not be crossed)\n\n"
        f"- since {today} · revised {today}\n\n"
        "## Priorities\n\n"
        "(when two goods conflict, which wins — ranked)\n\n"
        f"- since {today} · revised {today}\n\n"
        "## Must first\n\n"
        "(what must happen before anything else is worth accepting)\n\n"
        f"- since {today} · revised {today}\n"
    ))
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

def cmd_issue(a: argparse.Namespace) -> None:
    body = a.body
    if a.origin:
        body = f"origin: {a.origin}\n\n" + body
    n = gh("issue", "create", "--title", a.title, "--body", body).rsplit("/", 1)[-1]
    print(f"issue #{n} — https://github.com/{REPO}/issues/{n}")


def issue_view(n: int) -> dict:
    d = gh_json("issue", "view", str(n), "--json", "number,title,body,state,comments")
    if not d:
        sys.exit(f"otr: issue #{n} not found in {REPO!s}")
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

BEFORE ANYTHING ELSE read docs/specs/northpole.md — Problem, Watch for, Constraints,
Priorities, Must first — and every `status: frozen` file in docs/decisions/ (`python3
{tools}/decisions.py` lists them). Choose methods by Priorities, turn Watch for into
checks, order work by Must first, and record such judgment under ## Judgment; a change
against Constraints or a frozen decision is a Deviation to record, never a judgment call
to make.

ISSUE #{n} — {title}
{body}

TASK
{task}

PHASE: {phase}
{phase_rules}

RECORD
- Your record is docs/issue-{n}/reports/{hex}.md. Start from {pkg}/templates/record.md
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
- Deliver a proposal only: what you will change, how. No implementation beyond
  throwaway probes.
- Put a proposed `## Acceptance` and `## Out of scope` in your record
  (plugin/templates/record.md has the sections) and say how each Acceptance item will
  be verified. If the issue above already has `## Acceptance` / `## Out of scope`, keep
  or refine them there instead and say which — the human is never asked to write them
  up front, so their absence in the issue is the normal case, not an error.
- Fill `## Judgment`: the methods you considered (smallest marked), the one you chose,
  and why — name the Priority or Watch for item that decided it. Only one method was
  ever possible → write `none`.
- Record: type: proposal, loop_state: proposed. Commit on your branch.""",
    "delivery": """\
- The proposal on this branch was approved on the issue, which by then carries the
  approved `## Acceptance`. Implement exactly it; deviations go under ## Deviations.
- If delivery changed the method chosen in `## Judgment` (a Watch for item forced a
  course change, or the approved feedback picked a different method), update that
  section to say so; otherwise carry it over unchanged.
- Record: rewrite it as type: implementation (or verification/repair as fits),
  loop_state: landed, with ## Acceptance verification covering every item in the
  issue's current `## Acceptance` section.""",
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
    print(DIRECTIVE.format(n=n, hex=hexid, root=ROOT, repo=str(REPO), tools=TOOLS, pkg=PKG,
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
    judgment = extract_section(record_body_of(text), "## Judgment")
    git("push", "-q", "-u", "origin", branch)
    pr = pr_for(branch)
    summary = (f"Closes #{n}\n\n**{fm.get('type', '?')} · {fm.get('loop_state', '?')}**\n\n"
               f"{fm.get('verdict', '')}\n\n**Judgment**\n\n{judgment or 'none'}"
               f"\n\nRecord: `docs/issue-{n}/reports/{hexid}.md`")
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
    text = record_on(branch, a.issue, a.hex)
    if not text and not pr_for(branch):
        sys.exit(f"otr: nothing published for {branch}")
    via = ""
    if a.via == "delegation":
        d = require_delegation(a.issue)
        via = f" VIA DELEGATION until {d['until'].isoformat()}"
    sha = git("rev-parse", "--short", branch, check=False) or "?"
    wrote = []
    if text:
        rec_body = record_body_of(text)
        issue_body = issue_view(a.issue)["body"]
        for header, label in (("## Acceptance", "Acceptance"), ("## Out of scope", "Out of scope")):
            content = extract_section(rec_body, header)
            if content:
                issue_body = set_section(issue_body, header, content)
                wrote.append(label)
        if wrote:
            gh("issue", "edit", str(a.issue), "--body", issue_body)
    note = a.note or ""
    if wrote:
        note = (note + "\n\n" if note else "") + f"Wrote {', '.join(wrote)} from the record into the issue body."
    gh("issue", "comment", str(a.issue), "--body", f"APPROVE issue-{a.issue}/{a.hex}{via}\n\nat {sha}\n\n{note}")
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


_STOPWORDS = {
    "a", "an", "the", "of", "to", "in", "on", "for", "and", "or", "is", "are", "be",
    "that", "this", "it", "its", "as", "with", "by", "at", "from", "not", "no", "if",
    "when", "than", "then", "so", "do", "does", "did", "has", "have", "had", "was",
    "were", "will", "would", "can", "may", "must", "never", "only", "one", "their",
    "they", "them", "which", "who", "what", "each", "every", "any", "some", "other",
    "another", "own", "same", "such", "also", "into", "under", "over", "out", "up",
}


def _words(s: str) -> set[str]:
    return {w for w in re.findall(r"[a-z][a-z']+", s.lower()) if w not in _STOPWORDS and len(w) > 2}


def _claims(bullet: str, text: str) -> bool:
    """True if a majority of `bullet`'s significant words show up in `text` — a
    paraphrase match, not a quote match (the north pole's prose wraps and a record
    is not required to repeat it verbatim)."""
    bw = _words(bullet)
    if not bw:
        return True
    return len(bw & _words(text)) * 2 >= len(bw)


def _section(text: str, header: str) -> str:
    sys.path.insert(0, str(TOOLS))
    from record_lint import find_section
    i = find_section(text, header)
    if i < 0:
        return ""
    rest = text[i + len(header):]
    j = rest.find("\n## ")
    return rest if j < 0 else rest[:j]


def _bullets(section_text: str) -> list[str]:
    """`- ` bullets from a north-pole/issue section, continuation lines joined onto
    their bullet, the `- since ... revised ...` metadata line dropped."""
    out: list[str] = []
    for line in section_text.splitlines():
        s = line.strip()
        if not s:
            continue
        if s.startswith("- since") and "revised" in s:
            continue
        if s.startswith("-"):
            out.append(s.lstrip("- ").strip())
        elif out:
            out[-1] += " " + s
    return out


def _must_first_claim_text(record_text: str) -> str:
    """Where a record can claim to satisfy a Must-first item: its own verification of
    what it did, its judgment of why, and its Acceptance section — which by convention
    (`otr approve` writes the issue's Acceptance into the issue, and records keep or
    quote it) carries the issue's title/Problem/Acceptance without a second GitHub call."""
    body = record_body_of(record_text)
    return "\n".join([
        extract_section(body, "## Acceptance verification"),
        extract_section(body, "## Judgment"),
        extract_section(body, "## Acceptance"),
    ])


def _landed_records_on_main() -> list[str]:
    """Full text of every docs/issue-*/reports/*.md on `main` whose loop_state is
    landed/done. A delivery branch has already merged main in (per the directive), so
    this needs no GitHub call — just the git history already in this checkout."""
    paths = [p for p in git("ls-tree", "-r", "--name-only", MAIN, "--", "docs").splitlines()
             if re.match(r"docs/issue-\d+/reports/[0-9a-f]{8}\.md$", p)]
    out = []
    for p in paths:
        text = git("show", f"{MAIN}:{p}", check=False)
        if text and frontmatter_of(text).get("loop_state") in ("landed", "done"):
            out.append(text)
    return out


def _require_must_first(record_text: str) -> None:
    """Notice only — never refuses. A hard gate on Must-first order was tried and
    rejected: it deadlocks every later issue once the satisfying one is accepted but
    nobody has gone back to edit the north pole (the human's own account of the
    predecessor system's failure mode; see ## Judgment). A Must-first item is "met"
    for this notice's purposes once some landed/done record on main claims it, or the
    human edits it out of (or revises it in) northpole.md; either quiets the notice on
    its own, with no otr command needed to acknowledge it."""
    northpole = (ROOT / "docs/specs/northpole.md").read_text()
    bullets = _bullets(_section(northpole, "## Must first"))
    own = _must_first_claim_text(record_text)
    landed = [_must_first_claim_text(t) for t in _landed_records_on_main()]
    unmet = [b for b in bullets if not _claims(b, own) and not any(_claims(b, t) for t in landed)]
    for b in unmet:
        print(f"notice: Must first not yet met — {b}")


def _require_watch_for_evidence(n: int, record_text: str) -> None:
    """Every bullet under the issue's own `## Watch for` needs a line in this record's
    `## Evidence` that shows it was checked — not a bigger Evidence section, one line
    per item (`evidence-per-acceptance-item`)."""
    bullets = _bullets(_section(issue_view(n)["body"], "## Watch for"))
    if not bullets:
        return
    evidence = extract_section(record_body_of(record_text), "## Evidence")
    missing = [b for b in bullets if not _claims(b, evidence)]
    if missing:
        lines = [f"  - {b}" for b in missing]
        sys.exit("otr: issue's Watch for item(s) with no evidence line in this record's ## Evidence:\n" + "\n".join(lines))


_TEST_INFRA_GLOBS = ["**/test/**", "**/tests/**", "**/*_test.*", "**/*.test.*", "**/*.spec.*", "**/conftest.py"]


def _glob_hit(path: str, globs: list[str]) -> bool:
    for g in globs:
        if fnmatch(path, g):
            return True
        if g.endswith("/**") and (path == g[:-3] or path.startswith(g[:-3] + "/")):
            return True
    return False


def _require_reason_for_unrequested_files(n: int, branch: str, record_text: str) -> None:
    """A diff that adds CI/deploy/workflow files (the `minimal-change` decision's own
    globs — no second list) or new, unnamed test-infrastructure files needs a reason in
    this record's `## Judgment`. This never forbids the files, only a missing reason."""
    sys.path.insert(0, str(TOOLS))
    import decisions
    minimal = next((d for d in decisions.frozen() if d.id == "minimal-change"), None)
    # minimal-change's scope.globs also names the files that *implement* the decision
    # (plugin/templates/record.md, this file) so reaffirms-detection can find them; only
    # the CI/deploy/workflow-shaped entries describe an unrequested *file kind*.
    ci_globs = [g for g in (minimal.globs if minimal else [])
                if g.startswith(".github") or "/ci/" in g or "/deploy/" in g or g.endswith((".yml", ".yaml"))]
    all_paths = git("diff", "--name-only", f"{MAIN}...{branch}").splitlines()
    added = set(git("diff", "--diff-filter=A", "--name-only", f"{MAIN}...{branch}").splitlines())
    acceptance = extract_section(issue_view(n)["body"], "## Acceptance").lower()

    flagged = {p for p in all_paths if _glob_hit(p, ci_globs)}
    for p in added:
        if _glob_hit(p, _TEST_INFRA_GLOBS) and p.lower() not in acceptance and Path(p).name.lower() not in acceptance:
            flagged.add(p)
    if not flagged:
        return
    judgment = extract_section(record_body_of(record_text), "## Judgment").strip()
    if judgment and judgment.lower() != "none":
        return
    lines = [f"  - {p}" for p in sorted(flagged)]
    sys.exit(
        "otr: diff adds CI/deploy/workflow or unnamed test-infrastructure file(s) with no "
        "reason in this record's ## Judgment:\n" + "\n".join(lines)
    )


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
    _require_must_first(text)
    _require_watch_for_evidence(n, text)
    _require_reason_for_unrequested_files(n, branch, text)
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
