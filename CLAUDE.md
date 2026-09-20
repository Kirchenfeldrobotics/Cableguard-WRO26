## Git authorship

- Commits are authored by the repository owner only: `valerypiot <valery.piot@outlook.com>`.
- **Never** add `Co-Authored-By: Claude ...`, `Claude-Session: ...`, `Generated with Claude Code`,
  or any other AI attribution to commit messages, pull request descriptions, or code comments.
- Write commit messages in plain English describing the change itself, nothing about the tooling
  that produced it.

## Git safety

- **Never run `git push`.** The repository owner pushes manually after reviewing the changes.
- Do not commit unless explicitly asked to. Stage changes and let the owner review them.
