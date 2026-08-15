# Shared AI Context Files — Kiro, Claude Code & the Web App

Three consumers need the same project knowledge: the Kiro IDE assistant, Claude Code, and
the trip-planner web app's backend. This document describes how they share one set of
files instead of three drifting copies.

---

## The principle

**Every fact has exactly one file. Other consumers reach it by symlink or by path
reference — never by copy.**

A copied file is a file that will drift. The moment `road-planner` gains a step, a
duplicate under `.claude/` silently keeps planning trips the old way, and nothing fails
loudly enough to notice. So the rule is absolute: if two tools need the same content,
one of them gets a link, not a copy.

---

## The three consumers

| Consumer | Reads | Bridging needed |
| --- | --- | --- |
| **Kiro** | `AGENTS.md` hierarchy, `.kiro/skills/`, `.kiro/settings/mcp.json` | none — these are its native locations |
| **Claude Code** | `AGENTS.md` hierarchy, `.claude/skills/`, `.mcp.json` | symlinks for skills and MCP config |
| **Web app** | assembled by `app/backend/core/context.py` | none — reads the originals by path |

Kiro previously used `.kiro/steering/*.md`. That directory is gone; its content moved into
the `AGENTS.md` hierarchy and `.kiro/skills/`, which both assistants read.

---

## Layer 1 — Preferences and conventions (`AGENTS.md`)

Facts that apply whenever you work somewhere in the tree. Both assistants load these
natively by path, and parent files load alongside child files — working in `trips/road/`
pulls in `AGENTS.md`, `trips/AGENTS.md` and `trips/road/AGENTS.md`.

| File | Content |
| --- | --- |
| `AGENTS.md` | Repository overview, commit conventions, Python environment |
| `trips/AGENTS.md` | Universal travel preferences, home base, content integrity |
| `trips/road/AGENTS.md` | Roadtrip preferences (flights, interests, food) |
| `trips/bike/AGENTS.md` | Bike tour preferences (distance, terrain, Einkehr) |
| `app/AGENTS.md` | Web app architecture and coding guidelines |
| `mcp/AGENTS.md` | MCP server development guidelines |

**No bridging required.** This layer is the reason the setup works at all — the majority of
shared context needs no tricks, because both tools already agree on the file name.

---

## Layer 2 — Workflows (Skills)

Procedures that should load only when you actually plan a tour, not on every file touch.

```
.kiro/skills/road-planner/
├── SKILL.md                        ← the original
└── references/
    └── output-template.md          ← not duplicated anywhere

.claude/skills/road-planner/
└── SKILL.md -> ../../../.kiro/skills/road-planner/SKILL.md
```

Two details make this work:

**The symlink carries no tool-specific syntax.** `SKILL.md` uses YAML frontmatter with
`name` and `description`, which both assistants interpret the same way. One file, two
readers.

**`references/` is deliberately not mirrored.** `SKILL.md` points at its template using a
path from the repository root:

```
.kiro/skills/road-planner/references/output-template.md
```

Because that path is root-relative rather than relative to `SKILL.md`, it resolves
correctly no matter which symlink the assistant came through. The consequence is that
**the working directory must be the repository root** — an assistant started from a
subdirectory will not find the template.

---

## Layer 3 — MCP servers

One server definition file, two entry points:

```
.kiro/settings/mcp.json             ← the original, 15 servers
.mcp.json -> .kiro/settings/mcp.json
```

Unlike `SKILL.md`, this file is *not* format-neutral. Kiro's schema has three keys Claude
Code does not share:

| Kiro key | Claude Code behaviour |
| --- | --- |
| `disabled` | ignored — remove the entry, or use `disabledMcpjsonServers` in `.claude/settings.json` |
| `autoApprove` | **ignored** — the equivalent is `permissions.allow` in `.claude/settings.json`, named `mcp__<server>__<tool>` |
| `disabledTools` | ignored |
| `url` without `"type"` | tolerated — `context7` connects despite having no explicit `"type": "http"` |

The unknown keys are tolerated rather than rejected, so the symlink works: all 15 servers
connect under both tools. Verify with `/mcp` in Claude Code.

The one behavioural gap is `autoApprove`. Kiro auto-approves 42 of the 45 tools; Claude
Code will prompt for each until an equivalent allowlist exists in `.claude/settings.json`.
Keep in mind that `serpapi-flights`, `tavily` and `travel-content` consume paid API quota
— those are the entries worth *not* auto-approving.

The Kiro list has also drifted once: `openrouteservice` exposes five tools, but only four
are listed under `autoApprove`. `isochrone` is missing, so it prompts in Kiro while the
rest of the server does not.

API keys need no bridging at all. Every server loads the project-root `.env` itself via
`Path(__file__).resolve()`, so no `env` block belongs in `mcp.json` under either tool.

---

## Layer 4 — The web app

`app/backend/core/context.py` is the third consumer and behaves differently: instead of
loading files by proximity, it detects the tour type from the user's message and
concatenates a subset into one system prompt.

```python
TRIPS_DIR  = ROOT / "trips"
SKILLS_DIR = ROOT / ".kiro" / "skills"
```

For a road trip it assembles `trips/AGENTS.md`, `trips/road/AGENTS.md`,
`.kiro/skills/road-planner/SKILL.md` and that skill's `references/output-template.md`,
stripping YAML frontmatter from each.

Two constraints follow:

- **Paths are hardcoded.** Moving or renaming any file in layers 1–2 means editing this
  module. It reads the `.kiro/` originals directly, not the `.claude/` symlinks.
- **Frontmatter must stay strippable.** The module removes everything between the first
  two `---` markers. A `SKILL.md` whose body legitimately starts with `---` would lose
  content.

---

## Rules for changing things

| Change | Do this |
| --- | --- |
| Add or edit an MCP server | Edit `.kiro/settings/mcp.json` only — the symlink propagates |
| Add a skill | Create `.kiro/skills/<name>/SKILL.md`, then symlink it (below) |
| Edit a skill or template | Edit the `.kiro/` original |
| Add a preference | Put it in the narrowest `AGENTS.md` that covers it |
| Move or rename any context file | Update `app/backend/core/context.py` |

Adding a skill:

```bash
mkdir -p .claude/skills/<name>
ln -s ../../../.kiro/skills/<name>/SKILL.md .claude/skills/<name>/SKILL.md
```

Two things never to do: write tool-specific content into a shared file, and reference
another file relatively from inside a symlinked one — always use a path from the
repository root.

---

## Verifying the wiring

```bash
# Every symlink resolves?
find .claude .mcp.json -type l -exec ls -l {} \;

# Any broken ones?
find .claude -xtype l

# Skill originals and their references present?
ls .kiro/skills/*/SKILL.md .kiro/skills/*/references/*.md
```

In Claude Code, `/mcp` reports connection status per server. The expected result is
15 connected, 0 failed.

---

## Known gaps

- **`.claude/` and `.mcp.json` are untracked.** A fresh clone gets a working Kiro setup and
  a Claude Code setup with no skills and no MCP servers. Git stores symlinks natively, so
  committing them costs nothing and is the missing step.
- **No `.claude/settings.json` exists**, so Kiro's `autoApprove` lists have no counterpart
  and every MCP tool call prompts.
- **`SKILL.md` bodies name `.kiro/` paths.** The shared files are format-neutral but not
  location-neutral; the directory layout is part of the contract.
