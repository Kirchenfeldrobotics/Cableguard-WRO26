## graphify

This project has a knowledge graph at graphify-out/ with god nodes, community structure, and cross-file relationships.

Rules:
- For codebase questions, first run `graphify query "<question>"` when graphify-out/graph.json exists. Use `graphify path "<A>" "<B>"` for relationships and `graphify explain "<concept>"` for focused concepts. These return a scoped subgraph, usually much smaller than GRAPH_REPORT.md or raw grep output.
- If graphify-out/wiki/index.md exists, use it for broad navigation instead of raw source browsing.
- Read graphify-out/GRAPH_REPORT.md only for broad architecture review or when query/path/explain do not surface enough context.
- After modifying code, run `graphify update .` to keep the graph current (AST-only, no API cost).

## Git authorship

- Commits are authored by the repository owner only: `valerypiot <valery.piot@outlook.com>`.
- **Never** add `Co-Authored-By: Claude ...`, `Claude-Session: ...`, `Generated with Claude Code`,
  or any other AI attribution to commit messages, pull request descriptions, or code comments.
- Write commit messages in plain English describing the change itself, nothing about the tooling
  that produced it.

## Git safety

- **Never run `git push`.** The repository owner pushes manually after reviewing the changes.
- Do not commit unless explicitly asked to. Stage changes and let the owner review them.
