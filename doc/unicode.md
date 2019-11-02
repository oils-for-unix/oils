---
in_progress: yes
---

Notes on Unicode in Shell
=========================

<div id="toc">
</div>

## Philosophy

Oil's unicode support is unlike that of other shells because it's
UTF-8-centric.

In other words, it's like newer languages like Go, Rust, Julia, and Swift, as opposed
, JavaScript, and Python (despite its Python heritage).  The latter languages
use the notion of "multibyte characters".

In particular, Oil doesn't have global variables like LANG for libc or a notion
of "default encoding".  In my experience, these types of globals cause
correctness problems.

## List of Unicode-Aware Operations in Shell

- `${#s}` -- length in code points
- `${s:1:2}` -- offsets in code points
- `${x#?}` and family (not yet implemented)

Where bash respects it:

- [[ a < b ]] and [ a '<' b ] for sorting
- ${foo,} and ${foo^} for lowercase / uppercase


This is a list of operations that SHOULD be aware of Unicode characters.  OSH
doesn't implement all of them yet, e.g. the globbing stuff.

- Length operator counts code points: `${#s}`
  - TODO: provide an option to count bytes.
- String slicing counts code points: `${s:0:1}`
- Any operation that uses glob, because it has `?` for a single character,
  character classes like `[[:alpha:]]`, etc.
  - `case $x in ?) echo 'one char' ;; esac`
  - `[[ $x == ? ]]`
  - `${s#?}` (remove one character)
  - `${s/?/x}` (note: this uses our glob to ERE translator for position)
- `printf '%d' \'c` where `c` is an arbitrary character.  This is an obscure
  syntax for `ord()`, i.e. getting an integer from an encoded character.

List of operations that depend on the locale (not implemented):

- String ordering: `[[ $a < $b ]]` -- should use current locale?  TODO: compare
  with `sort` command.
- Lowercase and uppercase operators: `${s^}` and `${s,}`
- Prompt string has time, which is locale-specific.
- In bash, `printf` also has time.

Other:

- The prompt width is calculated with `wcswidth()`, which doesn't just count
  code points.  It calculates the **display width** of characters, which is
  different in general.
