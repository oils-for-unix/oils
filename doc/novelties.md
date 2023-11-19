---
default_highlighter: oils-sh
---

Novelties in OSH and YSH
========================

Oils usually cleans up existing practice, rather than inventing brand new
things.  But here are a few features that may be unfamiliar.

Related: [Known Differences](known-differences.html).

<div id="toc">
</div>

## Global Options in the Interpreter

The interpreter has a big list of global settings!  Print them with `shopt -p`.

This idea comes from shell, and they can be tamed with blocks to `shopt`:

    shopt --unset errexit {
      touch /let
      touch /it
      touch /fail
    }

We use options to upgrade OSH to YSH:

    shopt --set ysh:upgrade


It's a bit like `use strict;` in Perl and JavaScript, or `from __future__` in
Python.


## The First Word of a Command

The Python-like features in YSH have to co-exist with shell like `echo "hello
$name"`, so there are more "first words".

### Mutation Uses the `setvar` Keyword

In YSH, mutation looks like this:

    setvar x = 42
    setvar x += 3

Not like JavaScript or Python

    x = 42  # doesn't work
    x += 3  # nope

### Evaluate Expressions with the `call` and `=` Keywords

In YSH, you use the `call` keyword to throw away the result of an expression.
It's most often used with functions and methods:

    call myFunc(x)

    call mylist->pop()

The `=` operator works the same way, but prints the return value:

    $ = mylist->pop()  # pretty-print result with = operator
    (Str)    "x"

    $ = 42 + a[i]
    (Int)    43

See [Command vs. Expression Mode](command-vs-expression-mode.html) for more.

### Hay Case Sensitivity

Attribute nodes start with capital letters, and this changes the parsing mode
to allow "bare" assignment:

    hay define Package
 
    Package {
      name = 'cpython'  # assignment without var/setvar keyword
      version = '3.12'
    }

## Lazy Arg Lists

These use `[]` instead of `()`:

    assert [42 === x]  # assert can pretty-print the expression

    ls8 | where [size > 10]  # not implemented

It's motivated by idioms from Awk and R.

## Three Quotation Types

YSH is Lisp-y!  These **unevaluated** quotation types don't appear in Python
and JS:

    var myblock = ^(ls /tmp | wc -l)  

    var myexpr = ^[age > 10]  # use evalExpr()

    var mytemplate = ^"$name is $age years old"  # not implemented


TODO: Explain more.



<!--

Other: value.Place could be unfamliar to Python/JS users.  It's based on C/C++
(but safe), and Rust also uses a similar syntax.

-->

## Related 

- [Quirks](quirks.html) is about OSH.
- [Warts](warts.html) is about YSH.

