---
default_highlighter: oils-sh
---

Guide to Procs and Funcs
========================

YSH has two major units of code: shell-like `proc`, and Python-like `func`.

- Roughly speaking, procs are for commands and **I/O**, while funcs are for
  pure **computation**.
- Procs are often **big**, and may call **small** funcs.  On the other hand,
  it's possible, but rarer, for funcs to call procs.
- You can write shell scripts **mostly** with procs, and perhaps a few funcs.

This doc compares the two mechanisms, and gives rough guidelines.

<!--
See the blog for more conceptual background: [Oils is
Exterior-First](https://www.oilshell.org/blog/2023/06/ysh-design.html).
-->

<div id="toc">
</div>

## Tip: Start Simple

Before going into detail, here's a quick reminder that you don't have to use
**either** procs or funcs.  YSH is a language that scales both down and up.  

You can start with just a list of plain commands:

    mkdir -p /tmp/dest
    cp --verbose *.txt /tmp/dest

Then copy those into procs as the script gets bigger:

    proc build-app {
      ninja --verbose
    }

    proc deploy {
      mkdir -p /tmp/dest
      cp --verbose *.txt /tmp/dest
    }

    build-app
    deploy

Then add funcs if you need pure computation:

    func isTestFile(name) {
      return (name => endsWith('._test.py'))
    }

    if (isTestFile('my_test.py')) {
      echo 'yes'
    }

## At a Glance

### Procs vs. Funcs

This table summarizes the difference between procs and funcs.  The rest of the
doc will elaborate on these issues.

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
    <td>Design Influence</td>
<td>

Shell-like.

</td>
<td>

Python- and JavaScript-like, but **pure**.

</td>
  </tr>

  <tr>
    <td>Shape</td>

<td>

Procs are shaped like Unix processes: with `argv`, an integer return code, and
`stdin` / `stdout` streams.

They're a generalization of Bourne shell "functions".  

</td>
<td>

Funcs are shaped like mathematical functions.

</td>
  </tr>

  <tr>
<td>

Architectural Role ([Oils is Exterior First](https://www.oilshell.org/blog/2023/06/ysh-design.html))

</td>
<td>

**Exterior**: processes and files.

</td>

<td>

**Interior**: functions and garbage-collected data structures.

</td>
  </tr>

  <tr>
    <td>I/O</td>
    <td>

Procs may start external processes and pipelines.  Can perform I/O anywhere.

</td>
    <td>

Funcs need an explicit `io` param to perform I/O.

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

    func computeMax(x, y) {
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

    var m = computeMax(3, 4)

Or throw away the return value, which is useful for functions that mutate:

    call computeMax(3, 4)

</td>
  </tr>

  <tr>
    <td>Naming Convention</td>
<td>

`kebab-case`

</td>
<td>

`camelCase`

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

Examples shown below.

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
    <td>Relation to Objects</td>
    <td>none</td>
    <td>

May be bound to objects:

    var x = obj.myMethod()
    call obj->myMutatingMethod()

   </td>
  </tr>

  <tr>
    <td>Interface Evolution</td>
<td>

**Slower**: Procs exposed to the outside world may need to evolve in a compatible or "versionless" way.

</td>
<td>

**Faster**: Funcs may be refactored internally.

</td>
  </tr>

  <tr>
    <td>Parallelism?</td>
<td>

Procs can be parallel with:

- shell constructs: pipelines, `&` aka `fork`
- external tools and the [$0 Dispatch
  Pattern](https://www.oilshell.org/blog/2021/08/xargs.html): xargs, make,
  Ninja, etc. 

</td>
<td>

Funcs are inherently **serial**, unless wrapped in a proc.

</td>
  </tr>

  <tr>
    <td colspan=3 style="text-align: center; padding: 3em">More <code>proc</code> features ...</td>
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
    <td>-</td>
  </tr>

</table>

### Func Calls and Defs

Now that we've compared procs and funcs, let's look more closely at funcs.
They're inherently **simpler**: they have 2 types of args and params, rather
than 4.

YSH argument binding is based on Julia, which has all the power of Python, but
without the "evolved warts" (e.g. `/` and `*`).

In general, with all the bells and whistles, func definitions look like:

    # pos args and named args separated with ;
    func f(p1, p2, ...rest_pos; n1=42, n2='foo', ...rest_named) {
      return (len(rest_pos) + len(rest_named))
    }

Func calls look like:

    # spread operator ... at call site
    var pos_args = [3, 4]
    var named_args = {foo: 'bar'}
    var x = f(1, 2, ...pos_args; n1=43, ...named_args)

Note that positional args/params and named args/params can be thought of as two
"separate worlds".

This table shows simpler, more common cases.


<table>
  <thead>
  <tr>
    <td>Args / Params</td>
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
    <td>Spread Pos Args</td>
<td>

    var args = [3, 4]
    var x = myMax(...args)

</td>
<td>

(as above)

</td>
  </tr>

  <tr>
    <td>Rest Pos Params</td>
<td>

    var x = myPrintf("%s is %d", 'bob', 30)

</td>
<td>

    func myPrintf(fmt, ...args) {
      # ...
    }

</td>
  </tr>

  <tr>
    <td colspan=3 style="text-align: center; padding: 3em">...</td>
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
    <td>Spread Named Args</td>
<td>

    var opts = {start: 5}
    var x = mySum(3, 4, ...opts)

</td>
<td>

(as above)

</td>
  </tr>

  <tr>
    <td>Rest Named Params</td>
<td>

    var x = f(start=5, end=7)

</td>
<td>

    func f(; ...opts) {
      if ('start' not in opts) {
        setvar opts.start = 0
      }
      # ...
    }

</td>
  </tr>

</table>

### Proc Calls and Defs

Like funcs, procs have 2 kinds of typed args/params: positional and named.

But they may also have **string aka word** args/params, and a **block**
arg/param.

In general, a proc signature has 4 sections, like this:

    proc p (
        w1, w2, ...rest_word;     # word params
        p1, p2, ...rest_pos;      # pos params
        n1, n2, ...rest_named;    # named params
        block                     # block param
    ) {
      echo 'body'
    }

In general, a proc call looks like this:

    var pos_args = [3, 4]
    var named_args = {foo: 'bar'}

    p /bin /tmp (1, 2, ...pos_args; n1=43, ...named_args) {
      echo 'block'
    }

The block can also be passed as an expression after a second semicolon:

    p /bin /tmp (1, 2, ...pos_args; n1=43, ...named_args; block)

<!--
- Block is really last positional arg: `cd /tmp { echo $PWD }`
-->

Some simpler examples:

<table>
  <thead>
  <tr>
    <td>Args / Params</td>
    <td>Call Site</td>
    <td>Definition</td>
  </tr>
  </thead>

  <tr>
    <td>Word args</td>
<td>

    my-cd /tmp

</td>
<td>

    proc my-cd (dest) {
      cd $dest
    }

</td>
  </tr>

  <tr>
    <td>Rest Word Params</td>
<td>

    my-cd -L /tmp

</td>
<td>

    proc my-cd (...flags) {
      cd @flags
    }

  <tr>
    <td>Spread Word Args</td>
<td>

    var flags = :| -L /tmp |
    my-cd @flags

</td>
<td>

(as above)

</td>
  </tr>

</td>
  </tr>

  <tr>
    <td colspan=3 style="text-align: center; padding: 3em">...</td>
  </tr>

  <tr>
    <td>Typed Pos Arg</td>
<td>

    print-max (3, 4)

</td>
<td>

    proc print-max ( ; x, y) {
      echo $[x if x > y else y]
    }

</td>
  </tr>

  <tr>
    <td>Typed Named Arg</td>
<td>

    print-max (3, 4, start=5)

</td>
<td>

    proc print-max ( ; x, y; start=0) {
      # ...
    }

</td>
  </tr>

  <tr>
    <td colspan=3 style="text-align: center; padding: 3em">...</td>
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
      cd $dest (; ; block)
    }

</td>
  </tr>

  <tr>
    <td>All Four Kinds</td>
<td>

    p 'word' (42, verbose=true) {
      echo $PWD
      echo hi
    }

</td>
<td>

    proc p (w; myint; verbose=false; block) {
      = w
      = myint
      = verbose
      = block
    }

</td>
  </tr>

</table>

## Common Features

Let's recap the common features of procs and funcs.

### Spread Args, Rest Params

- Spread arg list `...` at call site
- Rest params `...` at definition

### The `error` builtin raises exceptions

The `error` builtin is idiomatic in both funcs and procs: 

    func f(x) {   
      if (x <= 0) {
        error 'Should be positive' (status=99)
      }
    }

Tip: reserve such errors for **exceptional** situations.  For example, an input
string being invalid may not be uncommon, while a disk full I/O error is more
exceptional.

(The `error` builtin is implemented with C++ exceptions, which are slow in the
error case.)

### Out Params: `&myvar` is of type `value.Place`

Out params are more common in procs, because they don't have a typed return
value.

    proc p ( ; out) {
      call out->setValue(42)
    }
    var x
    p (&x)
    echo "x set to $x"  # => x set to 42

But they can also be used in funcs:

    func f (out) {
      call out->setValue(42)
    }
    var x
    call f(&x)
    echo "x set to $x"  # => x set to 42

Observation: procs can do everything funcs can.  But you may want the purity
and familiar syntax of a `func`.

---

Design note: out params are a nicer way of doing what bash does with `declare
-n` aka `nameref` variables.  They don't rely on [dynamic
scope]($xref:dynamic-scope).

## Proc-Only Features

Procs have some features that funcs don't have.

### Lazy Arg Lists `where [x > 10]`

A lazy arg list is implemented with `shopt --set parse_bracket`, and is syntax
sugar for an unevaluated `value.Expr`.

Longhand:

    var my_expr = ^[42 === x]  # value of type Expr
    assert (myexpr)

Shorthand:

    assert [42 === x]  # equivalent to the above

### Open Proc Signatures bind `argv`

TODO: Implement new `ARGV` semantics.

When a proc signature omits `()`, it's called **"open"** because the caller can
pass "extra" arguments:

    proc my-open {
      write 'args are' @ARGV
    }
    # All valid:
    my-open
    my-open 1 
    my-open 1 2

Stricter closed procs:

    proc my-closed (x) {
      write 'arg is' $x
    }
    my-closed      # runtime error: missing argument
    my-closed 1    # valid
    my-closed 1 2  # runtime error: too many arguments


An "open" proc is nearly is nearly identical to a shell function:

    shfunc() {
      write 'args are' @ARGV
    }

## Methods are Funcs Bound to Objects

Values of type `Obj` have an ordered set of name-value bindings, as well as a
prototype chain of more `Obj` instances ("parents").  They support these
operators:

- dot (`.`) looks for attributes or methods with a given name.
  - Reference: [ysh-attr](ref/chap-expr-lang.html#ysh-attr)
  - Attributes may be in the object, or up the chain.  They are returned
    literally.
  - Methods live up the chain.  They are returned as `BoundFunc`, so that the
    first `self` argument of a method call is the object itself.
- Thin arrow (`->`) looks for mutating methods, which have an `M/` prefix.
  - Reference: [thin-arrow](ref/chap-expr-lang.html#thin-arrow)

## The `__invoke__` method makes an Object "Proc-like"

First, define a proc, with the first typed arg named `self`:

    proc myInvoke (word_param; self, int_param) {
      echo "sum = $[self.x + self.y + int_param]"
    }

Make it the `__invoke__` method of an `Obj`:

    var methods = Object(null, {__invoke__: myInvoke})
    var invokable_obj = Object(methods, {x: 1, y: 2})

Then invoke it like a proc:

    invokable_obj myword (3)
    # sum => 6

## Usage Notes

### 3 Ways to Return a Value

Let's review the recommended ways to "return" a value:

1. `return (x)` in a `func`.
   - The parentheses are required because expressions like `(x + 1)` should
     look different than words.
1. Pass a `value.Place` instance to a proc or func.  
   - That is, out param `&out`.
1. Print to stdout in a `proc`
   - Capture it with command sub: `$(myproc)`
   - Or with `read`: `myproc | read --all; echo $_reply`

Obsolete ways of "returning":

1. Using `declare -n` aka `nameref` variables in bash.
1. Relying on [dynamic scope]($xref:dynamic-scope) in POSIX shell.

### Procs Compose in Pipelines / "Bernstein Chaining"

Some YSH users may tend toward funcs because they're more familiar. But shell
composition with procs is very powerful!

They have at least two kinds of composition that funcs don't have.

See #[shell-the-good-parts]($blog-tag):

1. [Shell Has a Forth-Like
   Quality](https://www.oilshell.org/blog/2017/01/13.html) - Bernstein
   chaining.
1. [Pipelines Support Vectorized, Point-Free, and Imperative
   Style](https://www.oilshell.org/blog/2017/01/15.html) - the shell can
   transparently run procs as elements of pipelines.

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

-->

## Summary

YSH is influenced by both shell and Python, so it has both procs and funcs.

Many programmers will gravitate towards funcs because they're familiar, but
procs are more powerful and shell-like.

Make your YSH programs by learning to use procs!

## Appendix

### Implementation Details

procs vs. funcs both have these concerns:

1. Evaluation of default args at definition time.
1. Evaluation of actual args at the call site.
1. Arg-Param binding for builtin functions, e.g. with `typed_args.Reader`.
1. Arg-Param binding for user-defined functions.

So the implementation can be thought of as a **2 &times; 4 matrix**, with some
code shared.  This code is mostly in [ysh/func_proc.py]($oils-src).

### Related

- [Variable Declaration, Mutation, and Scope](variables.html) - in particular,
  procs don't have [dynamic scope]($xref:dynamic-scope).
- [Block Literals](block-literals.html) (in progress)

<!--
TODO: any reference topics?
-->

<!--
OK we're getting close here -- #**language-design>Unifying Proc and Func Params** 

I think we need to write a quick guide first, not a reference


It might have some **tables**

It might mention concerete use cases like the **flag parser** -- #**oil-dev>Progress on argparse**


### Diff-based explanation

- why not Python -- because of `/` and `*` special cases
- Julia influence
- lazy args for procs `where` filters and `awk`
- out Ref parameters are for "returning" without printing to stdout

#**language-design>N ways to "return" a value**


- What does shell have?
  - it has blocks, e.g. with redirects
  - it has functions without params -- only named params


- Ruby influence -- rich DSLs


So I think you can say we're a mix of

- shell
- Python
- Julia (mostly subsumes Python?)
- Ruby


### Implemented-based explanation

- ASDL schemas -- #**oil-dev>Good Proc/Func refactoring**


### Big Idea: procs are for I/O, funcs are for computation

We may want to go full in on this idea with #**language-design>func evaluator without redirects and $?**


### Very Basic Advice, Up Front


Done with #**language-design>value.Place, & operator, read builtin** 

Place works with both func and proc


### Bump

I think this might go in the backlog - #**blog-ideas**


#**language-design>Simplify proc param passing?**

-->



<!-- vim sw=2 -->

## ul-table Draft

<table>

- thead
  - <!-- empty -->
  - Proc
  - Func
- tr
  - Design Influence
  - Shell-like.
  - Python- and JavaScript-like, but **pure**.
- tr
  - Shape
  - Procs are shaped like Unix processes: with `argv`, an integer return code,
    and `stdin` / `stdout` streams.

    They're a generalization of Bourne shell "functions".  
  - Funcs are shaped like mathematical functions.
- tr
  - Architectural Role ([Oils is Exterior First](https://www.oilshell.org/blog/2023/06/ysh-design.html))
  - **Exterior**: processes and files.
  - **Interior**: functions and garbage-collected data structures.
- tr
  - I/O
  - Procs may start external processes and pipelines.  Can perform I/O
    anywhere.
  - Funcs need an explicit `io` param to perform I/O.
- tr
  - Example Definition
  - ```
    proc print-max (; x, y) {
      echo $[x if x > y else y]
    }
    ```
  - ```
    func computeMax(x, y) {
      return (x if x > y else y)
    }
    ```
- tr
  - Example Call
  - ```
    print-max (3, 4)
    ```

    Procs can be put in pipelines:

    ```
    print-max (3, 4) | tee out.txt
    ```
  - ```
    var m = computeMax(3, 4)
    ```

    Or throw away the return value, which is useful for functions that mutate:

    ```
    call computeMax(3, 4)
    ```
- tr
  - Naming Convention
  - `kebab-case`
  - `camelCase`
- tr
  - [Syntax Mode](command-vs-expression-mode.html) of call site
  - Command Mode</td>
  - Expression Mode</td>
- tr
  - Kinds of Parameters / Arguments
  - <!-- empty -->
    1. Word aka string
    1. Typed and Positional
    1. Typed and Named
    1. Block

    Examples shown below.
  - <!-- empty -->
    1. Positional 
    1. Named

    (both typed)
- tr
  - Return Value
  - Integer status 0-255
  - Any type of value, e.g.

    ```
    return ([42, {name: 'bob'}])
    ```
- tr
  - Can it be a method on an object?
  - No
  - Yes, funcs may be bound to objects:

    ```
    var x = obj.myMethod()
    call obj->myMutatingMethod()
    ```
- tr
  - Interface Evolution
  - **Slower**: Procs exposed to the outside world may need to evolve in a compatible or "versionless" way.
  - **Faster**: Funcs may be refactored internally.
- tr
  - Parallelism?
  - Procs can be parallel with:
    - shell constructs: pipelines, `&` aka `fork`
    - external tools and the [$0 Dispatch
      Pattern](https://www.oilshell.org/blog/2021/08/xargs.html): xargs, make,
      Ninja, etc. 
  - Funcs are inherently **serial**, unless wrapped in a proc.
- tr
  - <!-- empty -->
  - <td-attrs colspan=3 style="text-align: center; padding: 3em" /> &nbsp;
    ...  More `proc` Features ...
  - <!-- empty -->
- tr
  - Kinds of Signature
  - Open `proc p {` or <br/>
    Closed `proc p () {`
  - <!-- dash --> -
- tr
  - Lazy Args
  - ```
    assert [42 === x]
    ```
  - <!-- dash --> -

</table>

