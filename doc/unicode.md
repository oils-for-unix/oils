Notes on Unicode in Shell
=========================

This is a list of operations in shell that should be aware of Unicode
characters.  (OSH doesn't implement all of them yet, e.g. all the glob stuff.)

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
