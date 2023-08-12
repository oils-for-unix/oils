---
in_progress: yes
default_highlighter: oil-sh
---

Oil Builtins
============

<!-- TODO: This doc could be an alternative categorization to the auto-generated
     builtin-index.md ? -->

This is an **overview** of [shell builtins]($xref:shell-builtin) that are
unique to Oil.  A full description of each builtin will be available in the
[help pages](help-index.html).

What are builtins?  They look like external commands, but are included with the
shell itself.  They don't spawn an external process, and can modify the shell's
memory.

<div id="toc">
</div>

## New Builtins in Oil

### [`append`]($help) appends strings to an array

Example:

    var a = :| 1 '2 two' |
    append :a three four
    echo @a  # prints 4 lines

Here's another way to write it:

    setvar a = :| @a three four |

Note that you can append to a string like this:

    var s = 'foo'
    setvar s = "${s}suffix"

(Note: Oil doesn't currently support the equivalent of shell's `s+=suffix`.)

### [`pp`]($help) pretty prints interpreter state

- `pp cell` - shows the value of a variable, for debugging
- `pp proc` - shows doc strings

### `module`

### `use`

### `runproc`

## Shell Builtins Enhanced with Block

Done:

- [cd]($help)
- [shopt]($help)

Planned, but not implemented:

- [fork]($help) for `&`
- [forkwait]($help) for `()`
- [env]($help) to replace `PYTHONPATH=. foo.py`
- [each]($help) runs processes in parallel and replaces `xargs`

Examples of what we have in mind:

```
# this replaces an awkward idiom with eval I've seen a lot
shopt -u errexit {  # TODO: --unset
   false
   echo "temporary disable an option"
} 

# generalizes the 'NAME=value command' syntax and the 'env' prefix helps parsing
env PYTHONPATH=. {
  ./foo.py
  ./bar.py
}

# replaces sleep 5 &
fork { sleep 5 }

# replaces () syntax so we can use it for something else.
forkwait { echo subshell; sleep 5 }

# Probably used for a "syntactic pun" of Python-like "import as" functionality

use lib foo.sh {
  myfunc
  myalias otherfunc
}
```

### cd

It now takes a block:

    cd /tmp {
      echo $PWD  # prints /tmp
    }
    echo $PWD  # prints the original directory


This subsumes the functionality of bash builtins [pushd]($help) and
[popd]($help).

When a block is passed:

- `cd` doesn't set The `OLDPWD` variable (which is used to implement the `cd -`
  shortcut.)
- The directory stack for `pushd` and `popd` isn't cleared, as it is with a
  normal `cd` command.

### shopt

## Other Builtins That Take Blocks

### fork, forkwait

### argparse

## I/O Builtins

See [IO Builtins](io-builtins.html).

And [JSON](json.html).

## More

- Not implemented: log, die
