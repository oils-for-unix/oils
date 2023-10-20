Tea Language
============

This is an experiment!  Background:

- <http://www.oilshell.org/blog/2020/10/big-changes.html#appendix-the-tea-language>
- <https://old.reddit.com/r/ProgrammingLanguages/comments/jb5i5m/help_i_keep_stealing_features_from_elixir_because/g8urxou/>
- <https://lobste.rs/s/4hx42h/assorted_thoughts_on_zig_rust#c_mqpg6e>
- <https://news.ycombinator.com/item?id=24845983>: mycpp origins, related to
  mycpp and ShedSkin
- There's no good language for writing languages:
  <https://lobste.rs/s/vmkv3r/first_thoughts_on_rust_vs_ocaml#c_v5ch1q>

tl;dr Tea is a cleanup of Oil's metalanguages, which can be called "statically
typed Python with sum types".  (Zephyr ASDL is pretty clean, but mycpp is
messy, and needs cleanup.)

- Tea Grammar: <https://github.com/oilshell/oil/blob/master/oil_lang/grammar.pgen2#L363>
- Tea ASDL Schema: <https://github.com/oilshell/oil/blob/master/frontend/syntax.asdl#L324>
- Python-like "transformer" from CST to AST:
  <https://github.com/oilshell/oil/blob/master/oil_lang/expr_to_ast.py>.  This
  code is repetitive, but it's how CPython did it for 25+ years.

## Metaphors

- "Oil + Tea" is like "Shell + C".  :)
- Oil could be the metaprogramming language for Tea.  "So Oil + Tea" is like
  the "C preprocessor + C".

## Demo

    $ bin/tea -n -c 'var x = 42'

    $ bin/oil -O parse_tea -n -c 'var x = 42'

    # Similar to both of the above
    $ tea/run.sh parse-one tea/testdata/hello.tea

Note that Tea stands alone as a language, but it can also be intermingled with
Oil, which I think will be useful for metaprogramming.

## Testing

This is currently run in the continuous build
(<http://travis-ci.oilshell.org/jobs/>).

    tea/run.sh soil-run


