---
default_highlighter: oils-sh
---

Informal Guide to Procs and Funcs
==================

- Funcs are in expressions
  - Interior
- Procs are in commands
  - Exterior

See blog: Oils is Exterior-First for some conceptual background.

- Note: procs do everything shell functions can.


<div id="toc">
</div>

## Comparison Table

<style>
  thead {
    background-color: #eee;
    font-weight: bold;
  }
  table {
    margin-left: 3em;
    font-family: sans-serif;
    border-collapse: collapse;
  }

  /* Markdown creates <p> in <td> that we don't want */
  td > p {
    margin-left: 0;
  }
  td > pre {
    margin-left: 0;
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
    <td>Python-like (but pure)</td>
  </tr>

  <tr>
<td>

Architecture ([Oils is Exterior First](https://www.oilshell.org/blog/2023/06/ysh-design.html))

</td>
    <td>Exterior: processes and files<br/>
        I/O may occur anywhere</td>
    <td>Interior: functions and garbage-collected data<br/>
        explicit I/O params</td>
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

[Call Site Syntax](command-vs-expression-mode.html)

</td>
    <td>Command Mode</td>
    <td>Expression Mode</td>
  </tr>

  <tr>
    <td>Example Definition</td>
<td>

    proc my-cd (dest; ; ; block) {
      cd $dest (block)
    }

</td>
<td>

    func maxNum(x, y) {
      return (x if x > y else y)
    }

</td>
  </tr>

  <tr>
    <td>Kinds of Arguments</td>
    <td>Four: Word aka string, Typed and Positional, Typed and Named, Block</td>
    <td>Two: Positional and Named (both typed)</td>
  </tr>

  <tr>
    <td>Example Call</td>
<td>

    my-cd /tmp {
      echo $PWD
      echo hi
    }

(Procs can also be transparently placed in pipelines.)

</td>
<td>

    var m = maxNum(x, y)

</td>
  </tr>

  <tr>
    <td>Return Value</td>
    <td>Integer status 0-255</td>
    <td>Any type of value</td>
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


- error () -- I guess this is the same?
  - it raises an exception

## Func 

### Signatures

    func f(pos; named) {
    }

### Param Binding

## Proc

### Open Procs

### Signatures

Closed with signature

    proc proc-with-hyphens (word; pos; named; block) {
      = word
      = pos
      = named
      = block
    }

### Param Binding

## Lazy Evaluation of Proc Args


## Shell Functions vs. PRocs

### ARGV

Shell functions:

    f() {
      write -- "$@"
    }


Procs

    proc p {
      write -- @ARGV
    }

Old Notes
=========



Procs are shell like-functions, but they can have declared parameters, and lack
dynamic scope.

    proc p(name, age) {
      echo "$name is $age years old"
    }

    p alice 42  # => alice is 42 years old

Blocks are fragments of code within `{ }` that can be passed to builtins (and
eventually procs):

    cd /tmp {
      echo $PWD  # prints /tmp
    }
    echo $PWD  # prints original dir

- See [YSH Idioms](idioms.html) for examples of procs.

<div id="toc">
</div>

## Influences

It's a very rich language.  But it enables a lot of power.

- Subsumes everything in shell
  - including dynamic scope, `read x`, `printf -v a[i] 'hello %s' "$x"` etc.
- Python- and JS-like Functions
- Ruby-like blocks
- Julia positional, named, spread, rest
- Awk and R for lazy arg lists.

## Table of Features

procs:

- open or closed
  - Open procs are more like shell "functions", and support *Bernstein chaining*
- Closed procs have 4 types of args: word, positional typed, named typed, block
- Block is really last positional arg: `cd /tmp { echo $PWD }`
- lazy arg list `[]` for the typed args

Common to both:

- spread at call site `f(...myListForPos)` or `f(; ...myDictForNamed)`
- rest params at definition `...rest`

More

- TODO: `&myvar` is a place, often used with procs.

## Procs Can Be Open Or Closed (With a Signature)

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

### Proc Signatures

TODO:

* Default values for params.
* All params are required.  Prefer `''` to `null` for string argument defaults.
* `@` is "splice" at the call site. Or also "rest" parameters.
* `:` for ref params
* `&` for blocks?
  * Procs May Accept Block Arguments

<!--

* Shell vs. Python composition.
* prefix spread ... at call site. Or "rest" parameters.
* Optional params?

-->

## Block Syntax

These forms work:

    cd / {
      echo $PWD
    }
    cd / { echo $PWD }
    cd / { echo $PWD }; cd / { echo $PWD }

These are syntax errors:

    a=1 { echo bad };        # assignments can't take blocks
    >out.txt { echo bad };   # bare redirects can't take blocks
    break { echo bad };      # control flow can't take blocks

Runtime error:

    local a=1 { echo bad };  # assignment builtins can't take blocks

Caveat: Blocks Are Space Sensitive

    cd {a,b}  # brace substitution
    cd { a,b }  # tries to run command 'a,b', which probably doesn't exist

Quoting of `{ }` obeys the normal rules:

    echo 'literal braces not a block' \{ \}
    echo 'literal braces not a block' '{' '}'

## Block Semantics 

TODO: This section has to be implemented and tested.

### User Execution (like Ruby's `yield` keyword?)

    proc p(&block) {
      echo '>'
      $block    # call it?
                # or maybe just 'block' -- it's a new word in the "proc" namespace?
      echo '<'
    }

    # Invoke it
    p {
      echo 'hello'
    }
    # Output:
    # >
    # hello
    # <

### User Evaluation (e.g. for Config Files)

How to get the value?

    var namespace = evalblock('name', 1+2, up=1)

    # _result is set if there was a return statement!

    # namespace has all vars except those prefixed with _
    var result = namespace->_result

TODO: Subinterpreters?

### Errors

Generally, errors occur *inside* blocks, not outside:

    cd /tmp {
       cp myfile /bad   # error happens here
       echo 'done'
    }                   # not here

### Control Flow

- `break` and `continue` are disallowed inside blocks.
- You can exit a block early with `return` (not the enclosing function).
- `exit` is identical: it exits the program.

### Setting Variables in Enclosing Scope

Can block can set vars in enclosing scope?

```
setref('name', 1+2, up=1)
```

## Notes: Use Cases for Blocks

### Configuration Files

Evaluates to JSON (like YAML and TOML):

    server foo {
      port = 80
    }

And can also be serialized as command line flags.

Replaces anti-patterns:

- Docker has shell
- Ruby DSLs like chef have shell
- similar to HCL I think, and Jsonnet?  But it's IMPERATIVE.  Probably.  It
  might be possible to do dataflow variables... not sure.  Maybe x = 1 is a
  dataflow var?

### Awk Dialect

    BEGIN {
      end
    }

    when x {
    }

### Make Dialect

    rule foo.c : foo.bar {
      cc -o out @srcs
    }

### Flag Parsing to replace getopts

Probably use a block format.  Compare with Python's optparse.o

See issue.

### Unit Tests

Haven't decided on this yet.

    check {
    }

## Funcs

In addition to shell-like procs, YSH also has Python-like functions:

```
var x = len(ARGV) + 1
```

### User-Defined Functions are Deferred

For now, we only have a few builtin functions like `len()`.


### Two Worlds: Syntax, Semantics, Composition

There are two kinds of composition / code units in YSH:

- procs are like shell "functions".  They look like an external process, accepting an
  `argv` array and returning exit code.  I think of `proc` as *procedure* or
  *process*.
  - TODO: add notes below
- funcs are like Python or JavaScript functions. They accept and return typed
  data.

procs are called with a "command line":

    my-proc arg1 arg2 arg3

funcs are called with Python/JS-like YSH expressions:

    var x = my_func(42, 'foo')
    _ my_func(42, 'foo')   # throw away the return value.

This may be legal:

    my-proc (42, 'foo')  # note space

This is NOT legal:

    my_func(42, 'foo')  # it's illegal whether there's a space or not


### Procs / Shell is the "main"

That is, procs can call funcs, but funcs won't be able to call procs (except
for some limited cases like `log` and `die`).


### Proc Compose

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


<!-- vim: sw=2 -->