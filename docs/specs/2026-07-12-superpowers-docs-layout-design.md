# Superpowers Docs Layout Design

## Goal

Create a durable personal fork of the Superpowers plugin. Its brainstorming workflow must write project artifacts into generic `docs/` locations compatible with the local `docs-scaffold` skill.

The workflow must never create `.superpowers/` or `docs/superpowers/` directories.

## Decisions

- Use a personal fork, not the mutable marketplace cache.
- Disable the remote `superpowers` plugin after the personal fork is installed and enabled. This prevents duplicate skill names and ambiguous selection.
- Retain all upstream skills. Change only brainstorming documentation, its visual-companion guide, and its companion server script.
- Update the personal `docs-scaffold` skill because it owns documentation source discovery.
- Migrate existing project specs from `docs/superpowers/specs/` to `docs/specs/` as part of adoption.

## Artifact Locations

| Artifact | Location | Docs Scaffold Behavior |
| --- | --- | --- |
| Approved design specification | `docs/specs/YYYY-MM-DD-<topic>-design.md` | Always read as additional Phase 0 input. |
| Visual companion content and runtime state | `docs/brainstorming/<session-id>/` | Read only when user explicitly names an artifact. |

Visual companion runtime state can contain browser session keys. It remains inside `docs/brainstorming/` to meet the location requirement. The companion server creates `docs/brainstorming/.gitignore` that ignores session contents while retaining the ignore file itself. Runtime state is never automatically consumed by `docs-scaffold`.

Neither location is a framework-owned documentation taxonomy. `docs-scaffold` may reorganize their contents into its canonical documentation tree.

## Plugin Changes

### Brainstorming skill

Change the approved-design output path from `docs/superpowers/specs/` to `docs/specs/`. Add an explicit invariant that brainstorming must not create `.superpowers/` or any `superpowers` directory under `docs/`.

The design-document instruction remains: create the approved spec, self-review it, commit it, request user review, then transition to planning.

### Visual companion guide

Replace references to `--project-dir` with `--docs-dir <project>/docs`. The guide instructs that companion sessions live at `docs/brainstorming/<session-id>/`, that session runtime state must be git-ignored, and that only explicitly named artifacts are passed to `docs-scaffold`.

### Companion server script

Replace the `--project-dir` option with a required `--docs-dir` option.

Given `--docs-dir /path/to/project/docs`, it creates:

```text
/path/to/project/docs/brainstorming/<session-id>/
  content/
  state/
```

Port and session-token state also remain below `docs/brainstorming/`. Before creating a session, the script creates `docs/brainstorming/.gitignore` to prevent session contents from being committed. The legacy `--project-dir` option is removed and must fail with an explicit unknown-option error. The script must not retain a compatibility path that creates `.superpowers/`.

### Docs Scaffold skill

Add a Phase 0 source-discovery rule:

- Read `docs/specs/*.md` as additional project input.
- Read a `docs/brainstorming/` artifact only when the user explicitly identifies it as source material.
- Do not reserve or duplicate either folder in the final documentation structure.

## Test Strategy

Apply test-first workflow to the script and skill behavior.

Baseline evidence to record before implementation:

- Current brainstorming guidance writes to `docs/superpowers/specs/`.
- Current visual companion script creates `.superpowers/brainstorm/` when passed `--project-dir`.
- Current `docs-scaffold` instructions do not discover brainstorm specifications.

Required regression checks:

- Starting the companion with `--docs-dir <project>/docs` produces session files only below `docs/brainstorming/`.
- Starting the companion creates `docs/brainstorming/.gitignore` that excludes runtime session contents.
- Passing legacy `--project-dir` fails and creates no `.superpowers/` directory.
- Modified brainstorming documentation contains `docs/specs/` and no prohibited paths.
- Modified visual companion documentation uses `--docs-dir` and documents runtime-state exclusion.
- Modified `docs-scaffold` instructions discover `docs/specs/` and require explicit selection for visual artifacts.
- Local marketplace installation exposes the personal fork and the remote plugin is disabled before final verification.

## Failure Handling

- Missing or invalid `--docs-dir`: server exits with a precise error before creating a session directory.
- Server startup failure: report error without leaving a partial `.superpowers/` path.
- Docs-scaffold finds no specs: continue with normal source discovery; no invented documents.
- Existing remote plugin remains enabled after personal fork install: stop deployment and resolve duplicate-plugin state before declaring success.

## Verification

Before completion, run targeted script and guide checks, list enabled plugins, and verify a fresh brainstorming invocation has no `.superpowers/` or `docs/superpowers/` output. Commit plugin-source changes separately from the design specification.
