---
in_progress: yes
---

Interpreter State
=================

<style>
/* override language.css */
.sh-command {
  font-weight: unset;
}
</style>

The Oil project has a single interpreter that supports both the OSH and Oil
languages.

In other words, It's useful to think of Unix shell in historical layers:

- [OSH]($xref:osh-language): A compatible but cleaned-up shell language.
  1. Thompson Shell (pipelines, exit status)
  2. Bourne Shell (variables, functions)
  3. [Korn Shell]($xref:ksh) (indexed arrays)
  4. [Bash]($xref:bash) (`shopt`, associative arrays)
- [Oil]($xref:oil-language): A new shell language that manipulates the same
  interpreter state in a cleaner way.

<!--
TODO:

- New "Pulp"?
- Use fenced code blocks
  - and run through BOTH bash and osh
    - and link to this doc
  - bash 4.4 in a sandbox?
-->


<div id="toc">
</div>

## Example

Shell has many syntaxes for the same semantics, which can be confusing.  For
example, in bash, these four statements do similar things:

```sh-prompt
$ foo='bar'
$ declare -g foo=bar
$ x='foo=bar'; typeset $x
$ printf -v foo bar

$ echo $foo
bar
```

In addition Oil, adds JavaScript-like syntax:

```
var foo = 'bar'
```

Oil's syntax can express more data types, but it may also confuse new users.

So the sections below describe the shell from a **semantic** perspective, which
should help users reason about their programs.

Quick tip: Use the [repr]($help) builtin to inspect shell variables.

## Design Goals

### Simplify and Rationalize bash

POSIX shell has a fairly simple model: everything is a string, and `"$@"` is a
special case.

Bash adds many features on top of POSIX, including arrays and associative
arrays.  Oil implements those features, and a few more.

However, it also significantly simplifies the model.

A primary difference is mentioned in [Known Differences](known-differences.html):

- In bash, the *locations* of values are tagged with types, e.g. `declare -A
  unset_assoc_array`.
- In Oil, *values* are tagged with types.  This is how common dynamic languages
  like Python and JavaScript behave.

In other words, Oil "salvages" the confusing semantics of bash and produces
something simpler, while still being very compatible.

### Add New Features and Types

TODO

- eggex type
- later: floating point type

## High Level Description

### Memory Is a Stack

- Shell has a stack but no heap.  The stack stores:
  - Variables that are local to a function.
  - The **arguments array** which is spelled `"$@"` in shell, and `@ARGV` in
    Oil.
- Shell's memory has values and locations, but **no** references/pointers.

<!--
later: Oil adds references to data structures on the heap, which may be recurisve.
-->

### Enviroment Variables Become Global Variables

On initialization, environment variables like `PYTHONPATH=.` are copied into
the shell's memory as global variables, with the `export` flag set.

Global variables are stored in the first stack frame, i.e. the one at index
`0`.

### Functions and Variables Are Separate

There are two distinct namespaces.  For example:

```
foo() {
  echo 'function named foo'
}
foo=bar   # a variable; doesn't affect the function
```

### Variable Name Lookup with "Dynamic Scope"

OSH has it, but Oil limits it.

### Limitations of Arrays And Compound Data Structures

Shell is a value-oriented language.

- Can't Be Nested 
- Can't Be Passed to Functions or Returned From Functions
- Can't Take References; Must be Copied

Example:

```
declare -a myarray=("${other_array[@]}")   # shell

var myarray = @( @other_array )            # Oil
```

Reason: There's no Garbage collection.

### Integers and Coercion

- Strings are coerced to integers to do math.
- What about `-i` in bash?


### Unix `fork()` Has Copy-On-Write Semantics

See the [Process Model](process-model.html) document.


## Key Data Types

TODO: [core/runtime.asdl]($oil-src)

<!-- 
TODO:
- Make a graphviz diagram once everything is settled?
-->

### `cell`

TODO

- [export]($help) only applies to **strings**

### `value`

Undef, Str, Sequential/Indexed Arrays, Associative Array

- "array" refers to both.
  - although Oil has a "homogeneous array type" that's entirely different
  - OSH array vs. Oil array
- no integers, but there is (( ))
- "$@" is an array, and "${a[@]}" too
  - not true in bash -- it's fuzzy there
  - but $@ and ${a[@]}  are NOT arrays
- flags: readonly and exported (but arrays/assoc arrays shouldn't be exported)
  - TODO: find that

### `cmd_value` for shell builtins

Another important type:

```
  assign_arg = (lvalue lval, value? rval, int spid)

  cmd_value =
    Argv(string* argv, int* arg_spids, command__BraceGroup? block)
  | Assign(builtin builtin_id,
           string* argv, int* arg_spids,
           assign_arg* pairs)
```


## Printing State

### Shell Builtins

Oil supports various shell and bash operations to view the interpretr state.

- `set` prints variables and their values
- `set -o` prints options
- `declare/typeset/readonly/export -p` prints a subset of variables
- `test -v` tests if a variable is defined.

### [repr]($help) in Oil

Pretty prints a cell.

This is cleaner!

TODO: What about functions




## Modifying State

### Oil Keywords

TODO: See Oil Keywords doc.

### Shell Assignment Builtins: declare/typeset, readonly, export

...

### [unset]($help)

You can't unset an array in OSH?  But you can in bash.

### Other Builtins

- [read]($help).  Sometimes sets the magic `$REPLY` variable.
- [getopts]($help)


## Links

- [Process Model](process-mode.html)
- <https://opensource.com/article/18/5/you-dont-know-bash-intro-bash-arrays>
- <https://www.thegeekstuff.com/2010/06/bash-array-tutorial>


## Appendix: Bash Issues

<!--
### Surprising Parsing

Parsing bash is undecidable.

    A[x]
    a[x]
-->

### Strings and Arrays Are Confused

    Horrible

    a=('1 2' 3)
    b=(1 '2 3')  # two different elements

    [[ $a == $b ]]
    [[ ${a[0]} == ${b[0]} ]]

    [[ ${a[@]} == ${b[@]} ]]


Associative arrays and being undefined

- half an array type
  - strict_array removes this
  - case $x in "$@"
- half an associative array type

### Indexed Arrays and Associative Arrays Are Confused

### Empty and Unset Are Confused

- empty array conflicts with `set -o nounset` (in bash 4.3).  I can't recommend
  in good faith.

<!--
test -v (???)  Was there a bug here?
-->



<!--

## Quirky Syntax and Semantics in Shell Sublanguages

### Command

Mentioned above: 

    a[x+1]+=x
    a[x+1]+=$x

    s+='foo'

### Word

Mentioned above:

    echo ${a[0]}
    echo "${a[0]}"
    echo ${a[i+1]}

### Arithmetic Does Integer Coercion

SURPRISING!  Avoid if you can!!!

    (( a[ x+1 ] += s ))  # 


### Boolean: [[ $a = $b ]]

Operates on strings only.  Can't compare

-->

