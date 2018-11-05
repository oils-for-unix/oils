Notes on OSH Architecture
=========================

## Parser Issues

### Where we (unfortunately) must re-parse previously parsed text

These cases make it harder to produce good error messages with source location
info.  They also have implications for translation, because we break the "arena
invariant".

(1) **Alias expansion** like `alias foo='ls | wc -l'`.  Aliases are like
"lexical macros".

(2) **Array L-values** like `a[x+1]=foo`.  bash allows splitting arithmetic
expressions across word boundaries: `a[x + 1]=foo`.  But I don't see this used,
and it would significantly complicate the OSH parser.

NOTE: These two cases involve extra passes at **parse time**.  Cases that
involve runtime code evaluation are demonstrated below.

### Where VirtualLineReader is used

This isn't necessarily re-parsing, but it's re-reading.

- alias expansion:
- HereDoc:  We first read lines, and then

### Extra Passes Over the LST

These are handled up front, but not in a single pass.

- Assignment / Env detection: `FOO=bar declare a[x]=1`
  - s=1 doesn't cause reparsing, but a[x+1]=y does.
- Brace Detection in a few places: `echo {a,b}`
- Tilde Detection: `echo ~bob`, `home=~bob`

### Parser Lookahead

- `func() { echo hi; }` vs.  `func=()  # an array`
- precedence parsing?  I think this is also a single token.

### Where the arena invariant is broken

- Here docs with <<-.  The leading tab is lost, because we don't need it for
  translation.

### Where parsers are instantiated

- See `osh/parse_lib.py` and its callers.

## Runtime Issues

### Where Strings are Evaluated As Code (intentionally)

- `source` builtin (`CommandParser`)
` `eval` builtin
- `trap` builtin
  - exit
  - debug
  - err
  - signals
- `$PS1` and `$PS4` (WordParser)

### Where Strings are Evaluated As Code (perhaps unintentionally)

(1) Recursive **Arithmetic Evaluation**:

    $ a='1+2'
    $ b='a+3'
    $ echo $(( b ))
    6

This also happens for the operands to `[[ x -eq x ]]`.

NOTE that `a='$(echo 3)` results in a **syntax error**.  I believe this was due
to the ShellShock mitigation.

(2) The **`unset` builtin** (not yet implemented in OSH):

    $ a=(1 2 3 4)
    $ expr='a[1+1]'
    $ unset "$expr"
    $ argv "${a[@]}"
    ['1', '2', '4']

(3) **Var refs** with `${!x}` (not yet implemented OSH.  Relied on by
`bash-completion`, as discovered by Greg Price)

    $ a=(1 2 3 4)
    $ expr='a[$(echo 2 | tee BAD)]'
    $ echo ${!expr}
    3
    $ cat BAD
    2

(4) ShellShock (removed from bash): `export -f`, all variables were checked for
a certain pattern.

### Parse errors at runtime (need line numbers)

- [ -a -a -a ]
- command line flag usage errors

## Other Cross-Cutting Observations

### Shell Function Callbacks

- completion hooks registered by `complete -F ls_complete_func ls`
- bash has a `command_not_found` hook; osh doesn't yet

### Where Unicode is Respected

- ${#s} -- length in code points
- ${s:1:2} -- offsets in code points
- ${x#?} and family (not yet implemented)

Where bash respects it:

- [[ a < b ]] and [ a '<' b ] for sorting
- ${foo,} and ${foo^} for lowercase / uppercase

### Parse-time and Runtime Pairs

- echo -e '\x00\n' and echo $'\x00\n' (shared in OSH)
- test / [ and [[ (shared in OSH)

### Other Pairs

- expr and $(( )) (expr not in shell)
- later: find and our own language

## Build Time

### Dependencies

- Optional: readline

### Borrowed Code

- All of OPy:
  - pgen2
  - compiler2 from stdlib
  - byterun
- ASDL front end from CPython (heavily refactored)
- core/tdop.py: Heavily adapted from tinypy

### Generated Code

- See `build/dev.sh`

