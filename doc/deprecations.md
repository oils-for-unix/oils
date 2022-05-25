---
default_highlighter: oil-sh
---

Shell Language Deprecations
===========================

When you turn on Oil language features, then there are a few shell constructs you can no longer use.
But we try to minimize the length of this list.

NOTE: The **`bin/osh`** interpreter, which is Oil in its default POSIX-
and bash-compatible mode **is compatible by default**.

<!-- cmark.py expands this -->
<div id="toc">
</div>

## Oil language upgrade mode (`shopt --set oil:basic`)


### Soft Deprecations

#### Use `forkwait` for subshells rather than `()` (`shopt -s parse_subshell`)

Subshells are **uncommon** in idiomatic Oil code, so they have the awkward name
`forkwait`.  Think of it as a sequence of the `fork` builtin (for `&`) and the
`wait` builtin.

No:

    ( not_mutated=foo )
    echo $not_mutated

Yes:

    forkwait {
      setvar not_mutated = 'foo'
    }
    echo $not_mutated

However, you don't even need a subshell for some idioms:

No:

    ( cd /tmp; echo $PWD )
    echo $PWD  # not mutated

Yes:

    cd /tmp {
      echo $PWD 
    }
    echo $PWD  # restored

Justification: We're using parentheses for Oil expressions like

    if (x > 0) { echo 'positive' }

and subshells are uncommon.  Oil has blocks to save and restore state.




### Hard Deprecations (Disallowed Syntax)


#### The "@()" Extended Globs changed to ",()" (`shopt -s parse_at`)

No:

    echo @(*.py|*.sh)

Use this Oil alias instead:

    echo ,(*.py|*.sh)

Justification: Most people don't know about extended globs, and we want
explicitly split command subs like `@(seq 3)` to work.

That is, Oil doesn't have implicit word splitting.  Instead, it uses [simple
word evaluation](simple-word-eval.html).

#### "@..." strings need quoting

`@foo` must be quoted `'@foo'` to preserve meaning (`shopt -s parse_at`)

#### No first-words beginning with "="

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

