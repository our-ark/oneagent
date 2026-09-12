# Teach

## Purpose

Use this hidden skill to describe OneAgent's ability to make useful skill-level changes available for descendants to inherit or learn.

## Boundary

OneAgent does not expose a user-facing `/teach` command. Teaching is implicit: descendants can inspect OneAgent's declared skills, lineage changes, work output, and skill packages, then adapt selected changes through `inherit` and `learn`.

## Use When

- OneAgent gains or changes a skill package that descendants may need.
- OneAgent's work flow emits inheritable skill-level learning artifacts.
- Documentation should distinguish OneAgent's hidden teaching ability from Lucy's explicit teaching command.
