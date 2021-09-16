---
in_progress: yes
---

Command Language
================

Recall that Oil is composed of three interleaved languages: words, commands,
and expressions.

For now, this document describes things that are **not** covered in:

- [A Tour of the Oil Language](oil-language-tour.html)
- The `#command-lang` section of [OSH Help
  Topics](osh-help-topics.html#command-lang)
- The `#command-lang` section of [Oil Help
  Topics](oil-help-topics.html#command-lang)

That is, it has both trivia or high-level concepts that aren't covered
elsewhere.

<div id="toc">
</div>

## POSIX Shell Constructs

- Bourne-style shell functions `f() { echo hi; }`
- "Direct" shell blocks like `{ echo hi; }`
- Redirects like `>&`

## Bash / ksh Constructs

### Still Useful

- The `time` keyword.  Yes, it's a **keyword**, not a builtin!

### Deprecated

- `[[` and `((`
- `for (( ))` loops
- More redirects like `&>`
- Here docs like `<<-`

