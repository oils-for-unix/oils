Index of Oil Enhancement Proposals
----------------------------------

Meta:

- [0000-intro](0000-intro.md) - Why write these docs?
- TODO: Code Style Guide: indentation, naming, etc.
- TODO: Prose Style Guide: probably best illustrated with examples of bad
  sentences and good sentences

OSH:

- [0010-compatible-arrays](0010-compatible-arrays.md)
  - Parsing Bash is Undecidable
  - syntax and semantics a[x]=1  a=(['x']=1)  
  - behavior within (( )) -- coercion to integer
  - TODO: should go in known-differences?
  - see doc/osh-data-model too.  Does that help end users?
- [0011-assignment-builtins](0011-assignment-builtins.md)
  - Static and dynamic parsing.  No splitting.
  - TODO: should go in known-differences?
- [0012-exit-status](0012-exit-status.md)
   - Status of command sub, assignments builtins, "bare" assignment, etc.

Oil:

- [0020-oil-word-eval](0020-oil-word-eval.md)
  - The "!QEFS" problem.
  - `shopt -s oil-word-eval` or `shopt -s static-word-eval`
    - no splitting
    - static globbing
    - are these separate options or not?  maybe just make it one option
    - keep `oil` out of the name so other shells can implement it
- [0021-splicing-arrays](0021-splicing-arrays.md)
  - `__syntax__ oil-splice` -- syntax change @a @f(x, y) syntax
    - @(...) makes since in OSH but not Oil... doh.  I guess it's not used, so you
      can use it.
    - also add argv in addition to repr?  yeah I think that's a good addition
      - should it use json format or no?  with color for \n?
      - note: like echo it can't take an options.
- [0022-oil-brace-paren-set](0022-oil-brace-paren-set.md)
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
- [0023-expr-string-literals](0023-expr-string-literals.md)
  - Balancing compatibility with shell vs. a legacy-free Oil language.
- [0024-oil-builtins](0024-oil-builtins.md)
  - Modified, Enhanced, and New Builtins.  Deprecated builtins.

More:

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

### Links

- [python/peps](https://github.com/python/peps)
- [rust-lang/rfcs](https://github.com/rust-lang/rfcs/tree/master/text)

