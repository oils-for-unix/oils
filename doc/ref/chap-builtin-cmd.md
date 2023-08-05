---
in_progress: yes
css_files: ../../web/base.css ../../web/manual.css ../../web/help.css ../../web/toc.css
body_css_class: width40 help-body
default_highlighter: oil-sh
---

Builtin Commands
===

This chapter in the [Oils Reference](index.html) describes builtin commands for OSH and YSH.

<div id="toc">
</div>

## Memory

### append

Append a string to an array of strings:

    var mylist = :| one two |
    append :mylist three

This is a command-mode synonym for the expression:

    _ mylist->append('three')

### pp

Pretty prints interpreter state.  Some of these are implementation details,
subject to change.

Examples:

    pp proc  # print all procs and their doc comments

    var x = :| one two |
    pp cell x  # print a cell, which is a location for a value

## Handle Errors

### try

Run a block of code, stopping at the first error (i.e. errexit is enabled).
Set the `_status` variable to the exit status of the block, and returns 0.

    try {
      ls /nonexistent

      ls | wc -l

      diff <(sort left.txt) <(sort right.txt)

      var x = 1 / 0
    }
    if (_status !== 0) {
      echo 'error'
    }

    # Shortcut for a single command
    try grep PATTERN FILE.txt
    case $_status in
      (0) echo 'found' ;;
      (1) echo 'not found' ;;
      (*) echo "error $_status" ;;
    esac

### boolstatus

Runs a command and requires the exit code to be 0 or 1.

    if boolstatus egrep '[0-9]+' myfile {  # may abort
      echo 'found'               # status 0 means found
    } else {
      echo 'not found'           # status 1 means not found
    }



## Shell State

### ysh-cd

It takes a block:

    cd / {
      echo $PWD
    }

### ysh-shopt

It takes a block:

    shopt --unset errexit {
      false
      echo 'ok'
    }

### shvar

Execute a block with a global variable set.

    shvar IFS=/ {
      echo "ifs is $IFS"
    }
    echo "ifs restored to $IFS"

### push-registers

Save global registers like $? on a stack.  It's useful for preventing plugins
from interfering with user code.  Example:

    status_42         # returns 42 and sets $?
    push-registers {  # push a new frame
      status_43       # top of stack changed here
      echo done
    }                 # stack popped
    echo $?           # 42, read from new top-of-stack

Current list of registers:

    BASH_REMATCH        aka  _match()
    $?             
    _status             set by the try builtin
    PIPESTATUS          aka  _pipeline_status
    _process_sub_status


## Modules

### runproc

Runs a named proc with the given arguments.  It's often useful as the only top
level statement in a "task file":

    proc p {
      echo hi
    }
    runproc @ARGV
    
Like 'builtin' and 'command', it affects the lookup of the first word.

### module

Registers a name in the global module dict.  Returns 0 if it doesn't exist, or
1 if it does.

Use it like this in executable files:

    module main || return 0   

And like this in libraries:

    module myfile.oil || return 0   

### use

Make declarations about the current file.

For files that contain embedded DSLs:

    use dialect ninja  # requires that _DIALECT is set to 'ninja'

An accepted declaration that tools can use, but isn't used by Oil:

    use bin grep sed

## I/O

### ysh-read

Oil adds buffered, line-oriented I/O to shell's `read`.

    read --line             # default var is $_line
    read --line --with-eol  # keep the \n
    read --line --qsn       # decode QSN too
    read --all              # whole file including newline; var is $_all
    read -0                 # read until NUL, synonym for read -r -d ''

When --qsn is passed, the line is check for an opening single quote.  If so,
it's decoded as QSN.  The line must have a closing single quote, and there
can't be any non-whitespace characters after it.

### write

write fixes problems with shell's `echo` builtin.

The default separator is a newline, and the default terminator is a
newline.

Examples:

    write -- ale bean        # write two lines
    write --qsn -- ale bean  # QSN encode, guarantees two lines
    write -n -- ale bean     # synonym for --end '', like echo -n
    write --sep '' --end '' -- a b        # write 2 bytes
    write --sep $'\t' --end $'\n' -- a b  # TSV line

### fork

The preferred alternative to shell's `&`.

    fork { sleep 1 }
    wait -n

### forkwait

The preferred alternative to shell's `()`.  Prefer `cd` with a block if possible.

    forkwait {
      not_mutated=zzz
    }
    echo $not_mutated



## Data Formats

### json

Write JSON:

    var d = {name: 'bob', age: 42}
    json write (d)

Read JSON into a variable:

    var x = ''
    json read :x < myfile.txt


## Testing

TODO: describe

## External Lang

TODO: when
