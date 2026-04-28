# AGENTS.md — OpenCode Session Exporter

## Project Overview

Python tool with two interfaces (CLI + web UI) for exporting OpenCode sessions to Markdown files.

## Workflow
- Explain implementation approach before coding
- Wait for approval on ambiguous/high-risk requirements
- Follow spec coding; avoid vibe coding
- Plan only includes design approach, no code.
- Iterate using `/loop` when possible.
- Run `/simplify` after implementation.

## Coding Rules
- Locate code by conceptual description (module, signal, logic).

## Task Splitting & Scope
- Split tasks into loosely coupled, independently verifiable sub-tasks;
- Patterns repeated 3+ times should be abstracted into reusable modules or skills.

## Quality Standards
- Early project minimum quality: compilable, simulable, rollbackable.
- Ensure critical paths and high-risk changes are verifiable.

## Correction & Collaboration
- Identify root causes when corrected; document repeated issues as rules.
- Separate implementation and review: finish code/plan first, then review independently.