---
in_progress: true
---

Shell Language Deprecations
===========================

When you turn on Oil, there are some shell constructs you can no longer use.
We try to minimize the length of this list.

You **don't** need to read this doc if you plan on using Oil in its default 
POSIX- and bash-compatible mode.  Oil is compatible by default.

<!-- cmark.py expands this -->
<div id="toc">
</div>

## Right Now (`shopt -s oil:basic`)

This is what new Oil users should know about.  There's just one thing!

### Some Extended Globs Can't Be Used (`shopt -s parse_at`)

No:

    echo @(*.py|*.sh)

Use this Oil alias instead:

    echo ,(*.py|*.sh)

TODO: Implement this.

Justification: Most people don't know about extended globs, and we want
explicitly split command subs like `@(seq 3)` to work.

That is, Oil doesn't have implicit word splitting.  Instead, it uses [simple
word evaluation](simple-word-eval.html).

## Later (`shopt -s oil:all`, under  `bin/oil`)

This is for the "legacy-free" Oil language.  Existing shell users will turn
this on later.  Users who have never used shell may want to start with the Oil
language.

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

This is the list of major features that is broken.  There are other features
that are **discouraged**, like `$(( x + 1 ))`, `(( i++ ))`, `[[ $s =~ $pat ]]`,
and `${s%%prefix}`.  These have better alternatives in the Oil expression
language, but they can still be used.


