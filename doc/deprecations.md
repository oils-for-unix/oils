---
default_highlighter: oil-sh
---

Shell Language Deprecations when Upgrading to Oil (`oil:upgrade`)
===========================

When you turn on the Oil language features there are a few shell constructs which continue to work, but whose use is now discouraged (i.e. deprecations). They are deprecated because they have some suboptmal property that was deemed large enough to warrant implementing an improved solution in Oil.

We try to keep the alternatives to be as compatible or similar as possible, wherever it makes sense, and any breakage or required syntax adjustments to a minimum.

Nevertheless, it couldn't be avoided that there are some, but very few and minor cases, in which legacy shell syntax is so ambiguous, inconsistent, or conflicting, that it simply had to be completely disallowed or redefined in the Oil shell. Fortunately, these are also rarely used things, so only very few people should actually have to deal with them.

NOTE: The **`bin/osh`** interpreter, which is the POSIX- and bash-compatible mode of the Oil-shell **is backwards-compatible by default**.

<!-- cmark.py expands this -->
<div id="toc">
</div>


## Discouraged Syntax (Deprecations)

### Spawning subshells with `()` -- instead use the more telling `forkwait` (`shopt -s parse_subshell`)

Subshells are a computationally costly concept to create a separate execution environment for commands. In idiomatic Oil code they should really be **uncommon**, because Oil provides much more efficient alternatives. Where it's really necessary to spawn a separte subshell in Oil, this should be done using `forkwait`.

Think of it as a sequence of the `fork` builtin (for `&`) and the `wait` builtin.

No:

    ( not_mutated=foo )
    echo $not_mutated

Yes:

    forkwait {
      setvar not_mutated = 'foo'
    }
    echo $not_mutated

However, in most cases you shouldn't even need a subshell:

No:

    ( cd /tmp; echo $PWD )
    echo $PWD  # not mutated

Yes:

    cd /tmp {
      echo $PWD 
    }
    echo $PWD  # restored

Justification: Instead of wasting a terse and short syntax for something rarely necesary in the command language (a cryptic speciality), in Oil the parentheses are used to place Oil expressions into conditional clauses (`shopt --set parse_paren`):

    if (x > 0) { echo 'positive' }

So using `forkwait` for subshells makes the usage of that rare and discouraged subshells mechanism obvious, and allows that parenthesis can attain their consisten meaning: Denoting conditions that are written as Oil expressions.



## Minor Breakages (New meanings, or disallowed Syntax.)


### The Extended Glob `@()` changed to `,()` (`shopt --set parse_at`)

No:

    echo @(*.py|*.sh)

Use this Oil alias instead:

    echo ,(*.py|*.sh)

Justification: Most people don't know about extended globs, and we want
explicitly split command subs like `@(seq 3)` to work.

That is, Oil doesn't have implicit word splitting.  Instead, it uses [simple
word evaluation](simple-word-eval.html).

### `@...` strings need quoting

`@foo` must be quoted `'@foo'` to preserve meaning (`shopt -s parse_at`)

### No first-words beginning with `=`

`=x` is disallowed as the first word in a command to avoid confusion with
  Oil's `=` operator.
  - It could be quoted like `'=x'`, but there's almost no reason to do that.





<!--    https://github.com/oilshell/oil/issues/678

## Oil language interpretter (`shopt -s oil:all`, under  `bin/oil`)

This is for the "legacy-free" Oil language.  These options **break more code**.

Existing shell users will turn this on later.  Users who have never used shell
may want to start with the Oil language.

### Shell Assignment and Env Bindings Can't Be Used (`shopt -s parse_equals`)

No:

    x=42
    PYTHONPATH=. foo.py

Yes:

    x = '42'  # string
    x = 42    # integer

    const x = '42'  # synonyms
    const x = 42

    env PYTHONPATH=. foo.py

Justification: We want bindings in config blocks without `const`.  For example,
this is valid Oil syntax:

    server www.example.com {
      port = 80
      root = "/home/$USER/www/"
    }

-->




## That's It

This is the list of major features that's broken when you upgrade from OSH to
Oil.  Again, we try to minimize this list, and there are two tiers.

There are other features that are **discouraged**, like `$(( x + 1 ))`, `((
i++ ))`, `[[ $s =~ $pat ]]`, and `${s%%prefix}`.  These have better alternatives
in the Oil expression language, but they can still be used.  See [Oil vs. Shell
Idioms](idioms.html).

## Related

- [Ideas for Future Deprecations](future.html)

