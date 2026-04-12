---
name: GitHub
id: github
skill: github
version: 1.0.0
description: Your code becomes Ink — commits are published works, PRs are manuscripts under review, open issues are unresolved questions in the Academy's archive.
author: The Doobaleedoos
triggers:
  - type: cron
    schedule: "0 8 * * *"
  - type: session-open
config:
  - key: ENCHANTIFY_GITHUB_USERNAME
    description: Your GitHub username
    required: true
  - key: ENCHANTIFY_GITHUB_REPOS
    description: Comma-separated "owner/repo" pairs to watch (leave blank for all your repos)
    required: false
requires:
  pip: []
  bins: [gh]
---

## What OpenClaw Skill This Wraps

The `github` skill — uses the `gh` CLI. Must be authenticated (`gh auth login`).

## What It Reads

Via `gh` CLI:
- Commits in the last 24h (your authored commits)
- PRs opened or merged in the last 24h
- Issues opened or closed in the last 24h
- Open PRs awaiting your review

## What It Writes

Writes to tick-queue (`memory/tick-queue.md`). Surfaces commits as Ink Well
contributions; PRs as manuscripts; issues as open questions.

## Setup

```bash
gh auth login
export ENCHANTIFY_GITHUB_USERNAME="yourhandle"
# Optional:
export ENCHANTIFY_GITHUB_REPOS="myorg/myproject,myuser/sideproject"
```

## Interactive Use

- *"What have I been building?"* → Labyrinth reads recent commits as the player's Ink Well contributions to the Academy
- *"What's waiting for my review?"* → Labyrinth reads pending PR reviews as manuscripts awaiting your assessment
- *"What's unresolved in [project]?"* → Labyrinth frames open issues as the Archive's unanswered questions
