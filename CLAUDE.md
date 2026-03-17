# Project Rules

## Workflow: Discussion Before Implementation

**NEVER write code, create files, or update documentation without explicit user approval.**

The workflow is strictly:

1. **Discuss** — Raise the decision, present options, explain trade-offs
2. **Decide** — User reviews, asks questions, and approves
3. **Document** — Write/update docs only after user approves the decision
4. **Implement** — Write code only after user approves the documented plan

This applies to everything: tech choices, architecture, data models, file structure, dependencies, mock data, prompts, and any other decision.

## What "Discuss First" Means

- When a new decision comes up (e.g., "what DB?", "what audio format?", "how to handle errors?"), **stop and ask** — don't assume or decide silently
- Present options with clear trade-offs (cost, complexity, quality, speed)
- Wait for the user to say "yes", "go with X", or "approved" before writing anything
- If the user asks to "start building", confirm which specific part and get approval on any undecided choices first

## What Does NOT Need Approval

- Reading files to understand the codebase
- Searching/exploring the project
- Answering questions about the project or technologies
- Presenting options and recommendations (that's the "discuss" step)

## Documentation

- Docs are the source of truth for all decisions
- Every tech choice gets documented with reasoning (ADR format)
- Update docs when decisions change — don't let docs go stale
- The user should be able to read the docs and fully understand every decision and why it was made

## Block-Based Execution

When tackling complex, multi-part features, break the work into **blocks** — self-contained chunks that build on each other.

### How to define blocks

- **Identify natural boundaries** — backend vs frontend, foundational vs dependent, simple vs complex
- **Order by dependency** — build what other things depend on first
- **Isolate the hardest piece** — give it its own block so it gets full attention
- **Keep blocks small enough to verify** — the user should be able to test/see results after each block

### At the start of each block, present:

- **What we're building** — specific files, endpoints, components
- **Any remaining micro-decisions** — things that weren't settled in the ADR
- **The plan** — step-by-step, then wait for approval before building

### Between blocks:

- **Checkpoint** — let the user test, open the browser, poke around
- **Get feedback** — before moving to the next block
- **Adjust** — the plan for remaining blocks may change based on what we learn

## Keeping the User's Mental Model in Sync

The user wants to understand what's being built, not just watch code appear.

- **Explain what each piece does and why** before building it
- **Don't dump large code blocks without context** — walk through the approach first
- **When something is complex**, explain the strategy before implementation
- **If you make a non-obvious choice**, say why
- **After building**, briefly confirm what was done and how to verify it
