# Sonnet DP Research Bridge

Use this when a discussion point needs external research that you want to run manually in Claude / Sonnet.

## Purpose

- Research unresolved design questions
- Compare external options without making project-specific decisions
- Prefer current, official, dated sources for time-sensitive claims

## Instructions For Sonnet

- Treat the input as a neutral research brief
- Do not decide what this project should do
- Compare options and summarize trade-offs
- For time-sensitive claims, require dated primary sources
- Separate product surfaces when relevant
- If only old primary sources are available, label them as stale candidates

## Output

Write the result to `.agents/context/sonnet-dp-research.md` after you bring it back into the repo.

Then use it as supporting input for `.agents/context/plan.md`.
