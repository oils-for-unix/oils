Nicer Syntax With `{`, `(`, and `set`
-------------------------------------

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
