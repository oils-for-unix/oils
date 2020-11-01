Tea Language
============

This is an experiment!  Background:

- <http://www.oilshell.org/blog/2020/10/big-changes.html#appendix-the-tea-language>
- <https://old.reddit.com/r/ProgrammingLanguages/comments/jb5i5m/help_i_keep_stealing_features_from_elixir_because/g8urxou/>
- <https://lobste.rs/s/4hx42h/assorted_thoughts_on_zig_rust#c_mqpg6e>

tl;dr Tea is a cleanup of Oil's metalanguages, which can be called "statically
typed Python with sum types".  (Zephyr ASDL is pretty clean, but mycpp is
messy, and needs cleanup.)

- Tea Grammar: <https://github.com/oilshell/oil/blob/master/oil_lang/grammar.pgen2#L363>
- Tea ASDL Schema: <https://github.com/oilshell/oil/blob/master/frontend/syntax.asdl#L324>

## Testing

This is currently run in the continuous build
(<http://travis-ci.oilshell.org/jobs/>).

    tea/run.sh travis

## Demo

    $ bin/tea -n -c 'var x = 42'

    $ bin/oil -O parse_tea -n -c 'var x = 42'


