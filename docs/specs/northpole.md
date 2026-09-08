# North pole

What this repository is for, in the operator's own words, verbatim and
undated-by-paraphrase. Append; never rewrite a quote. Each entry names the
mechanism that currently serves it, or `GAP` when nothing does yet.

A subagent reads this before starting; a change that works against an entry
is a deviation, not a judgment call.

## N1

> 저기서 git을 이용한 기록 체계와, 서브 에이전트 위임 체계를 가져오고 싶어.

served by: `docs/issue-<n>/`, `tools/otr.py directive`, `CLAUDE.md`

## N2

> 기록의 거의 모든게 git에 있어야 하지 않나?

served by: `docs/decisions/2026-09-08-git-only-ledger.md` (frozen)

## N3

> 저 레포에서 역할같은건 다 필요가 없고 … skill도 뺄거야 … env 나눌 필요 없어. 저 기록 체계랑 서브에이전트 활용하는 아이디어만 가져오려는거야.

served by: `docs/decisions/2026-09-08-no-roles-skills-or-isolation.md` (frozen)

## N4

> 워크트리같은거 새로 만드는게 로컬 PC에 잔재들이 남거나 하면 안되는데 … /tmp 아래도 직접 정리하게 해

served by: directive scratch rule (`runs/scratch/` only), `otr accept/reject/clean`

## N5

> On the record에서 한 가지 더 차용하고 싶은 체계가 뭐냐면, 레포의 지향점을 기록해두는 체계야.

served by: this file, `docs/decisions/` frontmatter `status: frozen` + `tools/decisions.py`, `otr accept` principle check
