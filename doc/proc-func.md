---
default_highlighter: oils-sh
in_progress: true
---

Guide to Procs and Funcs
========================

YSH has two major units of code: shell-like `proc`, and Python-like `func`.

- Roughly speaking, procs are for "commands" and **I/O**, while funcs are for pure
**computation**.
- Procs are often **big**, and often call **small** funcs.  The opposite
  &mdash; funcs calling procs &mdash; is possible, but rarer.
- You can write shell scripts **mostly** with procs, and maybe a few funcs.

This doc compares the two mechanisms and gives rough guidelines.

<!--
See the blog for more conceptual background: [Oils is
Exterior-First](https://www.oilshell.org/blog/2023/06/ysh-design.html).
-->

<div id="toc">
</div>

## Tip: You don't have to use either

General theme:

1. No procs
1. then group into procs
1. then funcs

---

- Block literals are  a syntax for unevaluated code like `cd /tmp { echo $ PWD
  }`. They are instances of "quotation type" `value.Command`.  The  `{ }`
  syntax is niec for passing to blocks to procs, but they can be passed to
  funcs as well.

You don't define blocks.  Blocks are data types.

## At a Glance: Procs vs. Funcs

<style>
  thead {
    background-color: #eee;
    font-weight: bold;
  }
  table {
    font-family: sans-serif;
    border-collapse: collapse;
  }

  tr {
    border-bottom: solid 1px;
    border-color: #ddd;
  }

  td {
    padding: 8px;  /* override default of 5px */
  }
</style>

<table>
  <thead>
  <tr>
    <td></td>
    <td>Proc</td>
    <td>Func</td>
  </tr>
  </thead>

  <tr>
    <td>Design</td>
    <td>Shell-like</td>
    <td>

Python-like (but **pure**)

</td>
  </tr>

  <tr>
<td>

Architecture ([Oils is Exterior First](https://www.oilshell.org/blog/2023/06/ysh-design.html))

</td>
<td>

**Exterior**: processes and files.

I/O may occur anywhere.

</td>

<td>

**Interior**: functions and garbage-collected data.

Explicit I/O params.

</td>
  </tr>

  <tr>
    <td>Example Definition</td>
<td>

    proc print-max (; x, y) {
      echo $[x if x > y else y]
    }

</td>
<td>

    func myMax(x, y) {
      return (x if x > y else y)
    }

</td>
  </tr>

  <tr>
    <td>Example Call</td>
<td>

    print-max (3, 4)

Procs can be put in pipelines:

    print-max (3, 4) | tee out.txt

</td>
<td>

    var m = maxNum(3, 4)

Or throw away the return value, for mutating functions:

    call myMax(3, 4)

</td>
  </tr>

  <tr>
    <td>Naming Convention</td>
<td>

`camelCase`

</td>
<td>

`kebab-case`

</td>
  </tr>

  <tr>
<td>

[Syntax Mode](command-vs-expression-mode.html) of call site

</td>
    <td>Command Mode</td>
    <td>Expression Mode</td>
  </tr>

  <tr>
    <td>Kinds of Parameters / Arguments</td>
    <td>

1. Word aka string
1. Typed and Positional
1. Typed and Named
1. Block

</td>
    <td>

1. Positional 
1. Named

(both typed)

</td>
  </tr>


  <tr>
    <td>Return Value</td>
    <td>Integer status 0-255</td>
    <td>

Any type of value, e.g.

    return ([42, {name: 'bob'}])

</td>
  </tr>

  <tr>
    <td colspan=3 style="text-align: center; padding: 3em">More features ...</td>
  </tr>

  <tr>
    <td>Kinds of Signature</td>
    <td>

Open `proc p {` or <br/>
Closed `proc p () {`

</td>
    <td>-</td>
  </tr>

  <tr>
    <td>Lazy Args</td>
<td>

    assert [42 === x]

</td>
    <td>No</td>
  </tr>

</table>

procs:

- open or closed
  - Open procs are more like shell "functions", and support *Bernstein chaining*
- Closed procs have 4 types of args: word, positional typed, named typed, block
- Block is really last positional arg: `cd /tmp { echo $PWD }`
- lazy arg list `[]` for the typed args

## Func Calls and Defs

The design is based on Julia, which has all the power of Python, but without
the special rules around `/` and `*`.

<table>
  <thead>
  <tr>
    <td></td>
    <td>Call Site</td>
    <td>Definition</td>
  </tr>
  </thead>

  <tr>
    <td>Positional Args</td>
<td>

    var x = myMax(3, 4)

</td>
<td>

    func myMax(x, y) {
      return (x if x > y else y)
    }

</td>
  </tr>

  <tr>
    <td>Rest Args (Positional)</td>
<td>

    var x = maxMany(3, 4, 5)

</td>
<td>

    func maxMany(...args) {
      var result = args[0]
      # ...
    }

</td>
  </tr>


</td>
  </tr>

  <tr>
    <td>Named Args</td>
<td>

    var x = mySum(3, 4, start=5)

</td>
<td>

    func mySum(x, y; start=0) {
      return (x + y + start)
    }

</td>
  </tr>

  <tr>
    <td>Rest Args (named)</td>
<td>

    var x = f(start=5, end=7)

</td>
<td>

    func f(; ...opts) {
      if ('start' not in opts) {
        setvar opts.start = 0
      }
      # ...
      return (opts)
    }

</td>
  </tr>

</table>

## Proc Calls and Defs

Procs have 4 kinds of args, while funcs have 2.  This means procs have the
**same** patterns as funcs do, with respect to positional and typed args (shown
above).

The 2 other kinds of args are words and blocks.

<table>
  <thead>
  <tr>
    <td></td>
    <td>Call Site</td>
    <td>Definition</td>
  </tr>
  </thead>

  <tr>
    <td>Positional Args</td>
<td>

    print-max (3, 4)

</td>
<td>

    proc print-max (x, y) {
      echo $[x if x > y else y]
    }

</td>
  </tr>


  <tr>
    <td>Block Argument</td>
<td>

    my-cd /tmp {
      echo $PWD
      echo hi
    }

</td>
<td>

    proc my-cd (dest; ; ; block) {
      cd $dest (block)
    }

</td>
  </tr>



</table>

## Common Features

### Spread Arguments, Rest Params

- Spread list `...` at call site
- Rest params `...` at definition

### `error` builtin to raise errors

- `error ()` builtin is idiomatic in both
  - it raises an "exception"

### Out Params: `&myvar`, `value.Place`

Out params are more common in procs, because they don't have a typed return
value.

But they can also be used in funcs.


## Two Worlds: Syntax, Semantics, Composition

There are two kinds of composition / code units in YSH, procs and funcs.

procs are called with a "command line":

    my-proc arg1 arg2 arg3

funcs are called with Python/JS-like YSH expressions:

    var x = my_func(42, 'foo')
    _ my_func(42, 'foo')   # throw away the return value.

This may be legal:

    my-proc (42, 'foo')  # note space

This is NOT legal:

    my_func(42, 'foo')  # it's illegal whether there's a space or not

### More Notes on Procs. vs Funcs


procs:

- shell-like / process-like
  - have string args, stdin/stdout/stderr, and return exit code
- BUT they also have **typed args** in YSH, including BLocks
  - args are lazily evaluated?
- return status is for ERRORS
- To "return" a list of strings, you should print lines of QSN to stdout!
- they can have side effects (I/O)
- they can be run on remote machines
- they're generally for code that takes more than 10ms?

Examples:

    kebab-case (1, 2, 3)
    kebab-case {
      const block = 'literal'
    }
    HayBlock {
      const block = 'literal'
    }

funcs: Python- and JavaScript, like

- often do pure computation
- eagerly evaluated args?  not sure
- no recoverable errors?
  - well you can use 'try' around the whole thing
  - glob() can fail
- run locally?
- should be fast: should take under 10ms -- which is a typical process start time
- which means funcs should:
  - be vectorized in a row

Examples:

    var x = strip(y)
    = strip(y)  # pretty print
    _ strip(y)  # not useful
    echo $[strip(y)]
    write -- @[split(x)]
    write -- @[glob(x)]  # it's possible for this to fail


## Func 

Funcs are more  straightforward and small, so let's start here.

Procs are actually a **superset** of funcs in most ways, except for the return
value.

## Proc


### Example: A Proc That Wraps Functions

Note: procs can technicaly do everything shell functions can.  Except pure
evaluation.

Procs are more flexible.  Their features


### Lazy Evaluation of Proc Args


### Procs Can Be Open Or Closed (With a Signature)

Shell-like open procs that accept arbitrary numbers of arguments:

    proc open {
      write 'args are' @ARGV
    }
    # All valid:
    open
    open 1 
    open 1 2

Stricter closed procs:

    proc closed(x) {
      write 'arg is' $x
    }
    closed      # runtime error: missing argument
    closed 1    # valid
    closed 1 2  # runtime error: too many arguments

### Procs / Shell is the "main"

That is, procs can call funcs, but funcs won't be able to call procs (except
for some limited cases like `log` and `die`).

### Procs Compose in Two Ways

People may tend to prefer funcs because they're more familiar. But shell
composition with proc is very powerful!

They have at least two kinds of composition that functions don't have.  See
#[shell-the-good-parts]($blog-tag) on Bernstein chaining and "point-free"
pipelines.

<!--

In summary:

* func signatures look like JavaScript, Julia, and Go.
  * named and positional are separated with `;` in the signature.
  * The prefix `...` "spread" operator takes the place of Python's `*args` and `**kwargs`. 
  * There are optional type annotations
* procs are like shell functions
	* but they also allow you to name parameters, and throw errors if the arity
is wrong.
	* and they take blocks.

One issue is that procs take block arguments but not funcs.  This is something
of a syntactic issue.  But I don't think it's that high priority.

-->

Here are some complicated examples from the tests.  It's not representative of
what real code looks like, but it shows all the features.

proc:

```
proc name-with-hyphen (x, y, @names) {
  echo $x $y
  echo names: @names
}
name-with-hyphen a b c
```

## Shell Functions vs. Procs

### ARGV

Shell functions:

    f() {
      write -- "$@"
    }


Procs

    proc p {
      write -- @ARGV
    }



## Summary

TODO

## Related

- [Block Literals](block-literals.html)

<!-- vim sw=2 -->
