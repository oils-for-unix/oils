---
in_progress: yes
---

Oil Builtins
============

<div id="toc">
</div>

- use
- push, repr
- wait, fork

## Enhanced with Block

- cd

(not done)

- wait
- env (not done)
- shopt


Shell-Like Builtins

    Builtins Accept Long Options
    Changed: echo
    New: use, push, repr

Builtins Can Take Ruby-Like Blocks (partially done)

    cd, env, and shopt Have Their Own Stack
    wait and fork builtins Replace () and & Syntax
    each { } Runs Processes in Parallel and Replaces xargs


### cd

It now takes a block:

```
cd ~/src {
  echo $PWD
  ls -l
}

# current directory restored here

echo $PWD
ls -l
```

(This subsumes the functinoality of bash builtins `pushd` and `popd`.)

When a block is passed:

- `cd` doesn't set The `OLDPWD` variable (which is used to implement the `cd -`
  shortcut.)
- The directory stack for `pushd` and `popd` isn't cleared, as it is with a
	normal `cd` command.

### push

Append one or more strings to an array.

```
var a = @(1 '2 two')
push :a three four
echo @a # prints 4 lines
```

`push` is a shortcut for:

```
setvar a = @( @a three four )
```

<!-- 

### append

You can append to a string like this:

```
var s = 'foo'
setvar s = "${s}suffix"
```

Or maybe:

```
append :s suffix
```

But I think the more logical thing is:

    echo ${s}suffix

or

    push :parts foo bar baz

    write -sep '' -end '' @parts

(Note: Oil doesn't currently support the equivalent of shell's `s+=suffix`.)

-->

## Builtin Flag Syntax

Oil's builtins accept long flags like `--verbose` and short flags like `-v`.

They behave like the popular GNU utilities on Linux distros, except that
`-long` (single hyphen) means the same thing as `--long`.  It's not a shortcut
for `-l -o -n -g` or `-l=ong`.  (This rule is consistent with the [Go flags
  package][goflags].)

[goflags]: https://golang.org/pkg/flag/

In addition, all of these are equivalent:

- `-sep x`
- `-sep=x`
- `--sep x`
- `--sep=x`

The first is preferred because it's the simplest and shortest.

(Trivia: Oil's flag syntax avoids the issue where `set -oo errexit nounset` is
a confusing equivalent to `set -o errexit -o nounset`.)

## I/O Builtins

Oil uses `write` and `getline` along with the `CSTR` format.  `echo` looks more
familiar and is OK in many cases, but isn't strictly necessary.

Shell:

- uses `echo` and `read`
- `echo` isn't good because `echo $x` is a bug
- `read` isn't good because `-r` isn't the default.  And the `\` format doesn't
  occupy one line.

Oil:

- `write -- @items`
  - `--sep $'\t'`, `--end $'\n'`  (do we need shorthand?)
  - `-n` is a shortcut `--end ''`
  - `write --cstr -- @items`
- `getline`
  - `--cstr`


### echo

- `-sep`: Characters to separate each argument.  (Default: newline)
- `-end`: Characters to terminate the whole invocation.  (Default: newline)
- `-n`: A synonym for `-end ''`.


## More

Future work, not implemented

- fork, wait
- log, die
- write
