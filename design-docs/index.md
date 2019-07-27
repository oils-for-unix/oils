Index of Oil Enhancement Proposals
----------------------------------

- [0001-intro](0001-intro.md) - Why write these docs?
- [0002-compatible-arrays](0002-compatible-arrays.md)
  - Parsing Bash is Undecidable
  - syntax and semantics a[x]=1  a=(['x']=1)  
  - behavior within (( )) -- coercion to integer
  - TODO: should go in known-differences?
  - see doc/osh-data-model too.  Does that help end users?
- [0003-assignment-builtins](0003-assignment-builtins.md)
  - Static and dynamic parsing.  No splitting.
  - TODO: should go in known-differences?
- [0004-exit-status](0004-exit-status.md)
   - Status of command sub, assignments builtins, "bare" assignment, etc.
- [0005-oil-word-eval](0005-oil-word-eval.md)
  - The "!QEFS" problem.
  - `shopt -s oil-word-eval` or `shopt -s static-word-eval`
    - no splitting
    - static globbing
    - are these separate options or not?  maybe just make it one option
    - keep `oil` out of the name so other shells can implement it
- [0006-splicing-arrays](0006-splicing-arrays.md)
  - `__syntax__ oil-splice` -- syntax change @a @f(x, y) syntax
    - @(...) makes since in OSH but not Oil... doh.  I guess it's not used, so you
      can use it.
    - also add argv in addition to repr?  yeah I think that's a good addition
      - should it use json format or no?  with color for \n?
      - note: like echo it can't take an options.
- [0007-oil-brace-paren-set](0007-oil-brace-paren-set.md)
  - Very slight breaks in compatibility for a nicer looking language!
  - `__syntax__ oil-brace`: syntax extension so { isn't significant
    - as a TOKEN, or as a special WORD
      - I think as a word is enough, so you don't break echo {f,b}
  - `__syntax__ oil-paren`: syntax extension so ( isn't subshell
    - requires adding shell { ... }
      - alternatives considered: subshell { }  , child { ... }, wait { ... }
    - also add fork { ... }
  - `__syntax__ oil-set`
    - set instead of setvar
    - builtin set -o errexit -- this is fine
- [0008-expr-string-literals](0008-expr-string-literals.md)
  - Balancing compatibility with shell vs. a legacy-free Oil language.
- `__syntax__ oil-equals` for config dialect
- `shopt -s longopts` -- for builtins


### TODO

- Expression Language (now)
  - Regex Literals (and character class literals, which are reused for globs)
  - Collection Literals, JSON
    - <https://github.com/oilshell/oil/wiki/Implementing-the-Oil-Expression-Language>
    - dicts have unquoted keys, and punning instead of Set notation
- Expression Language (LATER)
  - Find Dialect (`fs`)
  - Number Literals
    - JSON floating point, `1_000_000`, etc.
  - Function definitions, positional and keyword args
- Command Language
  - xargs / each
  - block arguments / context managers
- Style
  - Code Style Guide: indentation, naming, etc.
  - Prose Style Guide: probably best illustrated with examples of bad sentences
    and good sentences

