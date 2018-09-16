Notes on OSH Architecture
-------------------------

# Parse Time

## Where we (unfortunately) must re-parse previously parsed text

- alias expansion
- Array assignment like `a[x+1]=foo` (because breaking word boundaries like
  `a[x + 1]=foo` causes a lot of problems, and I don't see it used.)

Each of these cases has implications for translation, because we break the
"arena invariant".

### Extra Passes Over the LST

These are handled up front, but not in a single pass.

- Assignment / Env detection: `FOO=bar declare a[x]=1`
  - s=1 doesn't cause reparsing, but a[x+1]=y does.
- Brace Detection in a few places: `echo {a,b}`
- Tilde Detection: `echo ~bob`, `home=~bob`

## Parser Lookahead

- `func() { echo hi; }` vs.  `func=()  # an array`
- precedence parsing?  I think this is also a single token.

## Where the arena invariant is broken

- Here docs with <<-.  The leading tab is lost, because we don't need it for
  translation.

## Where VirtualLineReader is used

This isn't re-parsing, but it's re-reading.

- alias expansion
- HereDoc

## Where parsers are instantiated

- See `osh/parse_lib.py` and its callers.

# Runtime

## Where code strings are evaluated

- source and eval
- trap
  - exit
  - debug
  - err
  - signals
- PS1 and PS4 (WordParser is used)

### Function Callbacks

- completion hooks registered by `complete -F ls_complete_func ls`
- bash has a `command_not_found` hook; osh doesn't yet

## Parse errors at runtime (need line numbers)

- [ -a -a -a ]
- command line flag usage errors

## Where unicode is respected

- ${#s} -- length in code points
- ${s:1:2} -- offsets in code points
- ${x#?} and family (not yet implemented)

## Parse-time and Runtime Pairs

- echo -e '\x00\n' and echo $'\x00\n' (shared in OSH)
- test / [ and [[ (shared in OSH)

### Other Pairs

- expr and $(( )) (expr not in shell)
- later: find and our own language

# Build Time

## Dependencies

- Optional: readline

## Borrowed Code

- All of OPy:
  - pgen2
  - compiler2 from stdlib
  - byterun
- ASDL front end from CPython (heavily refactored)
- core/tdop.py: Heavily adapted from tinypy

## Generated Code

- See `build/dev.sh`

