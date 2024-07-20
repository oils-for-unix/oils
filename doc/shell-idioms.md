---
default_highlighter: oils-sh
---

Shell Language Idioms
=====================

These are like the [YSH vs. Shell Idioms](idioms.html), but the advice also
applies to other Unix shells.

<div id="toc">
</div>

## Style

### Use Only `"$@"`

There's no reason to use anything but `"$@"`.  All the other forms like `$*`
can be disallowed, because if you want to join to a string, you can write:

   joined_str="$@"

The same advice applies to arrays.  You can always use `"${myarray[@]}"`; you
never need to use `${myarray[*]}` or any other form.

Related: [Thirteen Incorrect Ways and Two Awkward Ways to Use
Arrays](http://www.oilshell.org/blog/2016/11/06.html)

### Prefer `test` to `[`

Idiomatic OSH code doesn't use "puns".

No:

    [ -d /tmp ]

Yes:

    test -d /tmp

The [simple_test_builtin](ref/chap-option.html#ysh:all) option enforces this.

## Use Statically Parsed Language Constructs

Static parsing is one of the [syntactic concepts](syntactic-concepts.html).  It
leads to better error messages, earlier error messages, and lets tools
understand your code.

### `test` Should Only Have 2 or 3 Arguments

In POSIX, the `test` builtin has a lot of unnecessary flexibility, which leads
to bugs.

See [Problems With the test Builtin: What Does -a
Mean?](//www.oilshell.org/blog/2017/08/31.html)

No:

    test ! -d /tmp
    test -d /tmp -a -d /tmp/foo

Yes:

    ! test -d /tmp
    test -d /tmp && test -d /tmp/foo

The [simple_test_builtin](ref/chap-option.html#ysh:all) option enforces that
`test` receives 3 or fewer arguments.

### Prefer Shell Functions to Aliases

Functions subsume all the common uses of alias, and can be parsed statically.

No:

    alias ll='ls -l'    

Yes:

    ll() {         # Shell Style
      ls -l "$@"
    }

    proc ll {      # YSH Style
      ls -l @ARGV
    }

If you're wrapping an external command with a function of the same, use the
[command](ref/chap-builtin-cmd.html#command) builtin:

    proc ls {
      command ls --color @ARGV
    }

### Prefer `$'\n'` to `echo -e`

No:

    echo -e '\n'   # arg to -e is dynamically parsed

Yes:

    echo $'\n'     # statically parsed

## How to Fix Code That `strict_errexit` Disallows

The `strict_errexit` feature warns you when you would **lose errors** in shell
code.

### The `local d=$(date %x)` Pitfall

No:

    local d=$(date %x)   # ignores failure

Yes:

    local d
    d=$(date %x)         # fails properly

Better YSH style:

    var d = $(date %x)   # fails properly

### Variations With `readonly` and `export`

In these cases, the builtin comes after the assignment.

No:

    readonly d1=$(date %x)
    export d2=$(date %x)

Yes:

    d1=$(date %x)
    readonly d1

    d2=$(date %x)
    export d2
 

### The `if myfunc` Pitfall

No:

    if myfunc; then
      echo 'Success'
    fi

Shell workaround when the *$0 Dispatch Pattern* is used:

    myfunc() {
      echo hi
    }

    mycaller() {
      if $0 myfunc; then  # $0 starts this script as a new process
        echo 'Success'
      fi
    }

    "$@"  # invoked like myscript.sh mycaller arg1 arg2 ...


Better YSH Style:

    try {
      myfunc
    }
    if (_error.code === 0) 
      echo 'Success'
    }


## Remove Dynamic Parsing

### Replacing `declare -i`, `local -i`, ...

The `-i` flag on assignment builtins doesn't add any functionality to bash &mdash;
it's merely a different and confusing style.

OSH doesn't support it; instead it has *true integers*.

For example, don't rely on "punning" of the `+=` operator; use `$(( ))`
instead.

No:

    declare -i x=3
    x+=1            # Now it's '4' because += will do integer arithmetic

Yes (shell style):

    x=3          
    x=$(( x + 1 ))  # No -i flag needed

Yes (YSH style):

    var x = 3
    setvar x += 1

Likewise, don't rely on dynamic parsing of arithmetic.

No:

    declare -i x
    x='1 + 2'     # Now it's the string '3'

Yes (shell style):

    x=$(( 1 + 2 ))

Yes (YSH style):

    var x = 1 + 2


