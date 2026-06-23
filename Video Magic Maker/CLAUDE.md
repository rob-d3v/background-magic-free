---
brain: background-magic-free
maintained-by: second-brain agent (agentes_perdidos)
confidential: false
---

# background-magic-free — brain schema

This folder is an **LLM-wiki second brain**, maintained by the `second-brain` agent.
It's an Obsidian vault: open it in Obsidian to browse pages, links, and the graph.

## Layout

- `index.md` — catalog of every page. Read FIRST on a query. Regenerate via reindex.
- `log.md`   — append-only dated history (`## [YYYY-MM-DD] <op> | <title>`).
- `wiki/`    — LLM-owned pages: `overview/ entities/ concepts/ comparisons/ decisions/ sources/`.
- `raw/`     — immutable source documents. Read from, never edit.

## Conventions

- One page per entity/concept/source. Filename = kebab-case slug.
- Every page opens with YAML frontmatter (`title, type, created, updated, sources, tags`).
- Cross-link liberally with `[[slug]]`. Cite sources inline: `(per [[source-slug]])`.
- Contradictions are flagged inline (`> ⚠️ Contradiction: ...`), never silently overwritten.

## Generic knowledge → shared base (don't duplicate)

Generic, non-confidential topics (Claude Code best practices, uv/PEP-723, the LLM-wiki
pattern, the agentes_perdidos agents) live ONCE in the shared base at:

    E:/backup_2026/Repositórios/agentes_perdidos/agents/second-brain/shared/

Reference those pages instead of re-ingesting them here. Keep this brain project-specific.

## Project notes (background-magic-free / lumina-bg)

- **Language:** the migrated detail pages (`entities/`, `concepts/`, `decisions/`) are
  written in **pt-BR**, following the original brain's convention. The overview and
  source pages are in English. Keep new detail pages pt-BR for consistency; technical
  terms and code stay in their original form.
- **Migrated brain.** On 2026-06-14 this vault absorbed a pre-existing `wiki/` brain at
  the **repo root** (`background-magic-free/wiki/`): 10 components → `wiki/entities/`,
  7 concepts → `wiki/concepts/`, 2 decisions → `wiki/decisions/`. Wikilinks
  `[[components/x]]` were rewritten to `[[entities/x]]`. Original frontmatter is preserved
  as `status` / `original-date` / `migrated-from`. The old root `wiki/` was left in place;
  this vault is now the canonical brain.
- **Inferred decisions / open issues** worth knowing before editing: relighting has two
  verified bugs (bg discarded; wrong weight load) tracked in [[entities/relighting]] +
  [[decisions/migrate-fc-to-fbc]]; Colab paths in `pipeline.py` are hardcoded.

## How to drive

Point an LLM at `agents/second-brain/SKILL.md` (in agentes_perdidos) and this vault, then:
`ingest <raw/...>`, `query <question>`, `lint`, `onboard`.
