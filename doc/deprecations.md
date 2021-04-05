---
default_highlighter: oil-sh
---

Shell Language Deprecations
===========================

When you turn on Oil, there are some shell constructs you can no longer use.
We try to minimize the length of this list.

You **don't** need to read this doc if you plan on using Oil in its default 
POSIX- and bash-compatible mode.  **Oil is compatible by default**.

<!-- cmark.py expands this -->
<div id="toc">
</div>

## Right Now (`shopt -s oil:basic`)

Here are two things that Oil users should know about, one major and one minor:
The meaning of the POSIX construct `()` has changed, and the meaning of the
bash construct `@()` has changed.

### Use `forkwait` for subshells rather than `()` (`shopt -s parse_paren`)

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

You don't need a subshell for some idioms:

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

TODO: Implement `forkwait`.

### Some Extended Globs Can't Be Used (`shopt -s parse_at`)

No:

    echo @(*.py|*.sh)

Use this Oil alias instead:

    echo ,(*.py|*.sh)

Justification: Most people don't know about extended globs, and we want
explicitly split command subs like `@(seq 3)` to work.

That is, Oil doesn't have implicit word splitting.  Instead, it uses [simple
word evaluation](simple-word-eval.html).

TODO: Implement this.

### Minor Breakages

- `@foo` must be quoted `'@foo'` to preserve meaning (`shopt -s parse_at`)

## Later (`shopt -s oil:all`, under  `bin/oil`)

This is for the "legacy-free" Oil language.  These options **break more code**.

Existing shell users will turn this on later.  Users who have never used shell
may want to start with the Oil language.

### The `set` builtin Can't Be Used (`shopt -s parse_set`)

No:

    set -x   
    set -o errexit

Yes:

    builtin set -x
    builtin set -o errexit

Possible alternatives:

    shopt -s errexit
    shopt --set errexit

Justification: It conflicts with `set x = 1` in Oil, which has an alias `Set x
= 1` for compatibility.  (TODO: Implement `Set`).


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

## That's It

This is the list of major features that's broken when you upgrade from OSH to
Oil.  Again, we try to minimize this list, and there are two tiers.

There are other features that are **discouraged**, like `$(( x + 1 ))`, `((
i++))`, `[[ $s =~ $pat ]]`, and `${s%%prefix}`.  These have better alternatives
in the Oil expression language, but they can still be used.  See [Oil Language
Idioms](idioms.html).

## Related

- [Ideas for Future Deprecations](future.html)

