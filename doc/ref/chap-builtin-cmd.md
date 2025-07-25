---
title: Builtin Commands (Oils Reference)
all_docs_url: ..
body_css_class: width40
default_highlighter: oils-sh
preserve_anchor_case: yes
---

<div class="doc-ref-header">

[Oils Reference](index.html) &mdash; Chapter **Builtin Commands**

</div>

This chapter in the [Oils Reference](index.html) describes builtin commands for OSH and YSH.

<span class="in-progress">(in progress)</span>

<div id="dense-toc">
</div>

## Memory

### cmd/append

Append word arguments to a list:

    var mylist = :| hello |

    append *.py (mylist)  # append all Python files

    var myflags = []
    append -- -c 'echo hi' (myflags)  # -- to avoid ambiguity

It's a shortcut for:

    call myflags->append('-c')
    call myflags->append('echo hi')

Similar names: [append][]

[append]: chap-index.html#append

### pp

The `pp` builtin pretty prints values and interpreter state.

Pretty printing expressions is the most common:

    $ var x = 42
    $ pp (x + 5)
    myfile.ysh:1: (Int)   47   # print value with code location

You can pass an unevaluated expression:

    $ pp [x + 5]
    myfile.ysh:1: (Int)   47   # evaluate first

The `value` command is a synonym for the interactive `=` operator:

    $ pp value (x)
    (Int)   42

    $ = x 
    (Int)   42

Print proc names and doc comments:

    $ pp proc  # subject to change

You can also print low-level interpreter state.  The trailing `_` indicates
that the exact format may change:

Examples:

    $ var x = :| one two |

    $ pp asdl_ (x)  # dump the ASDL "guts"

    $ pp test_ (x)  # single-line stable format, for spec tests

    # dump the ASDL representation of a "Cell", which is a location for a value
    # (not the value itself)
    $ pp cell_ x


## Handle Errors

### error

The `error` builtin interrupts shell execution.

If there's a surrounding `try` block, the `_error` register is set, and
execution proceeds after the block.

Otherwise, the shell exits with a non-zero status.

Examples:

    error 'Missing /tmp'            # program fails with status 10

    try {
       error 'Another problem'
    }
    echo $[error.code] # => 10

Override the default error code of `10` with a named argument:

    error 'Missing /tmp' (code=99)  # program fails with status 99

Named arguments add arbitrary properties to the resulting `_error` register:

    error 'Oops' (path='foo.json')

See [YSH Error Handling](../ysh-error-handling.html) for more examples.

### failed

A shortcut for `(_error.code !== 0)`:

    try {
      ls /tmp
    }
    if failed {
      echo 'ls failed'
    }

It saves you 7 punctuation characters: `( _ . !== )`

See [YSH Error Handling](../ysh-error-handling.html) for more examples.

### try

Run a block of code, stopping at the first error.  (This is implemented with
`shopt --set errexit`)

`try` sets the `_error` register to a dict, and always returns 0.

    try {
      ls /nonexistent
    }
    if (_error.code !== 0) {
      echo 'ls failed'
    }

Handle expression errors:

    try {
      var x = 42 / 0
    }

And errors from compound commands:

    try {
      ls | wc -l
      diff <(sort left.txt) <(sort right.txt)
    }

The case statement can be useful:

    try {
      grep PATTERN FILE.txt
    }
    case (_error.code) {
      (0)    { echo 'found' }
      (1)    { echo 'not found' }
      (else) { echo "grep returned status $[_error.code]" }
    }

See [YSH Error Handling](../ysh-error-handling.html) for more examples.

### boolstatus

Runs a command, and requires the exit code to be 0 or 1.

    if boolstatus egrep '[0-9]+' myfile {  # e.g. aborts on status 2
      echo 'found'               # status 0 means found
    } else {
      echo 'not found'           # status 1 means not found
    }

It's meant for external commands that "return" more than 2 values, like true /
false / fail, rather than pass / fail.

### assert

Evaluates and expression, and fails if it is not truthy.

    assert (false)   # fails
    assert [false]   # also fails (the expression is evaluated)

It's common to pass an unevaluated expression with `===`:

    func f() { return (42) }

    assert [43 === f()]

In this special case, you get a nicer error message:

> Expected: 43
> Got:      42

That is, the left-hand side should be the expected value, and the right-hand
side should be the actual value.

## Shell State

### ysh-cd

It takes a block:

    cd / {
      echo $PWD
    }

### ysh-shopt

Sets shell options, e.g.

    shopt --unset errexit
    shopt --set errexit

You can set or unset multiple options with the groups `strict:all`,
`ysh:upgrade`, and `ysh:all`.  Example:

    shopt --set ysh:upgrade

If a block is passed, then:

1. the mutated options are pushed onto a stack
2. the block is executed
3. the options are restored to their original state (even if the block fails to
   execute)

Example:

    shopt --unset errexit {
      false
      echo 'ok'
    }

Note that setting `ysh:upgrade` or `ysh:all` may initialize the [ENV][] dict.

Related: [shopt](#shopt)

[ENV]: chap-special-var.html#ENV

### shvar

Execute a block with a global variable set.

    shvar IFS=/ {
      echo "ifs is $IFS"
    }
    echo "ifs restored to $IFS"

### ctx

Execute a block with a shared "context" that can be updated using the `ctx`
built-in.

    var mydict = {}
    ctx push (mydict) {
       # = mydict => {}
       ctx set (mykey='myval')
    }
    # = mydict => { mykey: 'myval' }

The context can be modified with `ctx set (key=val)`, which updates or inserts
the value at the given key.

The context can also be updated with `ctx emit field (value)`.

    ctx push (mydict) {
       # = mydict => {}
       ctx emit mylist (0)
       # = mydict => { mylist: [0] }
       ctx emit mylist (1)
    }
    # = mydict => { mylist: [0, 1] }

Contexts can be nested, resulting in a stack of contexts.

    ctx push (mydict1) {
        ctx set (dict=1)
        ctx push (mydict2) {
            ctx set (dict=2)
        }
    }
    # = mydict1 => { dict: 1 }
    # = mydict2 => { dict: 2 }

`ctx` is useful for creating DSLs, such as a mini-parseArgs.

    proc parser (; place ; ; block_def) {
      var p = {}
      ctx push (p, block_def)
      call place->setValue(p)
    }

    proc flag (short_name, long_name; type; help) {
      ctx emit flag ({short_name, long_name, type, help})
    }

    proc arg (name) {
      ctx emit arg ({name})
    }

    parser (&spec) {
      flag -t --tsv (Bool, help='Output as TSV')
      flag -r --recursive (Bool, help='Recurse into the given directory')
      flag -N --count (Int, help='Process no more than N files')
      arg path
    }

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

    Regex data underlying BASH_REMATCH, _group(), _start(), _end()
    $?             
    _error                # set by the try builtin
    PIPESTATUS            # aka  _pipeline_status
    _process_sub_status


## Modules

### source-guard

Registers a name in the global "module" dict.  Returns 0 if it doesn't exist,
or 1 if it does.

Use it like this in executable files:

    source-guard main || return 0   

And like this in libraries:

    source-guard myfile.ysh || return 0   

### is-main

The `is-main` builtin returns 1 (false) if the current file was executed with
the `source` builtin.

In the "main" file, including `-c` or `stdin` input, it returns 0 (true).

Use it like this:

    if is-main {
      runproc @ARGV
    }

### use

The `use` builtin evaluates a source file in a new `Frame`, and then creates an
`Obj` that is a namespace.

    use my-dir/mymodule.ysh

    echo $[mymodule.my_integer]   # the module Obj has attributes
    mymodule my-proc              # the module Obj is invokable

The evaluation of such files is cached, so it won't be re-evaluated if `use` is
called again.

To import a specific name, use the `--pick` flag:

    use my-dir/mymodule.ysh --pick my-proc other-proc

    my-proc 1 2
    other-proc 3 4

Note: the `--pick` flag must come *after* the module, so this isn't valid:

    use --pick my-proc mymodule.sh  # INVALID

<!--
# TODO:

use mod.ysh --all-provided    # relies on __provide__ or provide builtin
use mod.ysh --all-for-testing
-->

---

The `--extern` flag means that `use` does nothing.  These commands can be used
by tools to analyze names.

    use --extern grep sed awk

---

Notes:

- To get a reference to `module-with-hyphens`, you may need to use
  `getVar('module-with-hyphens')`. 
  - TODO: consider backtick syntax as well
- `use` must be used at the top level, not within a function.
  - This behavior is unlike Python.
- The `use` builtin populates the new module with references to these values in
  the calling module:
  - [ENV][] - to mutate and set environment vars
  - [PS4][] - for cross-module tracing in OSH

[ENV]: chap-special-var.html#ENV
[PS4]: chap-plugin.html#PS4

Warnings:

- `use` **copies** the module bindings into a new `Obj`.  This means that if
  you rebind `mymodule.my_integer`, it will **not** be visible to code in the
  module.
  - This behavior is unlike Python.
- `use` allows "circular imports".  That is `A.ysh` can `use B.ysh`, and vice
  versa.
  - To eliminate confusion over uninitialized names, use **only** `const`,
    `func`, and `proc` at the top level of `my-module.ysh`.  Don't run
    commands, use `setvar`, etc.

## I/O

### ysh-read

YSH adds long flags to shell's `read`.  These two flags are fast and
recommended:

    read --all               # whole file including trailing \n, fills $_reply
    read --all (&x)          # fills $x

    read --num-bytes 3       # read N bytes, fills _reply
    read --num-bytes 3 (&x)  # fills $x

---

This flag replaces shell's `IFS= read -r` idiom, reading one byte a time in an
unbuffered fashion:

    read --raw-line             # unbuffered read of line, omitting trailing \n
    read --raw-line (&x)        # fills $x

    read --raw-line --with-eol  # include the trailing \n

A loop over [io.stdin][] allows buffered reading of lines, which is faster.

[io.stdin]: chap-type-method.html#stdin

You may want to use `fromJson8()` or `fromJson()` after reading a line.

---

The `-0` flag also reads one byte at a time:

    read -0                 # read until NUL, synonym for read -r -d ''

Notes:

- Unlike OSH [read](#read), none of these features remove NUL bytes.
- Performance summary: [YSH Input/Output > Three Types of I/O][ysh-io-three]

[ysh-io-three]: ../ysh-io.html#three-types-of-io

<!--

TODO:

- read --netstr
- io.stdin0 coudl be a buffered version of read -0 ?
- JSON
  - @() is related - it reads J8 lines
  - JSON lines support?
  - fromJ8Line() is different than from fromJson8() ?  It's like @()

-->

<!--

What about write?  These would be the same:

    write --json -- $s
    write --j8 -- $s

    write -- $[toJson(s)]
    write -- $[toJson8(s)]

    write --json -- @strs
    write --j8 -- @strs

    write -- @[toJson(s) for s in strs]
    write -- @[toJson8(s) for s in strs]

It's an argument for getting rid --json and --j8?  I already implemented them,
but it makes the API smaller.

I guess the main thing would be to AVOID quoting sometimes?

    $ write --j8 -- unquoted
    unquoted

    $ write --j8 -- $'\'' '"'
    "'"
    "\""

I think this could be the shell style?

    $ write --shell-str -- foo bar baz

Or it could be

    $ write -- @[toShellString(s) for s in strs]

I want this to be "J8 Lines", but it can be done in pure YSH.  It's not built
into the interpreter.

  foo/bar
 "hi"
b'hi'
u'hi'

But what about

 Fool's Gold
a'hi'  # This feels like an error?
a"hi"  # what about this?

Technically we CAN read those as literal strings
-->

### ysh-echo

Print arguments to stdout, separated by a space.

    ysh$ echo hi there
    hi there

The [simple_echo][] option means that flags aren't accepted, and `--` is not
accepted.

    ysh$ echo -n
    -n

See the [YSH FAQ entry on echo][echo-en] for details.

[simple_echo]: chap-option.html#ysh:all
[echo-en]: ../ysh-faq.html#how-do-i-write-the-equivalent-of-echo-e-or-echo-n

### ysh-test

The YSH [test](#test) builtin supports these long flags:

    --dir            same as -d
    --exists         same as -e
    --file           same as -f
    --symlink        same as -L

    --true           Is the argument equal to the string "true"?
    --false          Is the argument equal to the string "false"?

The `--true` and `--false` flags can be used to combine commands and
expressions:

    if test --file a && test --true $[bool(mydict)] {
      echo ok
    }

This works because the boolean `true` *stringifies* to `"true"`, and likewise
with `false`.

That is, `$[true] === "true"` and `$[false] === "false"`.

### write

write fixes problems with shell's `echo` builtin.

The default separator is a newline, and the default terminator is a
newline.

Examples:

    write -- ale bean         # write two lines

    write -n -- ale bean      # synonym for --end '', like echo -n
    write --sep '' --end '' -- a b        # write 2 bytes
    write --sep $'\t' --end $'\n' -- a b  # TSV line

You may want to use `toJson8()` or `toJson()` before writing:

    write -- $[toJson8(mystr)]
    write -- $[toJson(mystr)]


<!--
    write --json -- ale bean  # JSON encode, guarantees two lines
    write --j8 -- ale bean    # J8 encode, guarantees two lines
-->


### fork

Run a command, but don't wait for it to finish.

    fork { sleep 1 }
    wait -n

In YSH, use `fork` rather than shell's `&` ([ampersand][]).

[ampersand]: chap-cmd-lang.html#ampersand

### forkwait

The preferred alternative to shell's `()`.  Prefer `cd` with a block if possible.

    forkwait {
      not_mutated=zzz
    }
    echo $not_mutated

### redir

Runs a block passed to it.  It's designed to enable a **prefix** syntax when
redirecting:

    redir >out.txt {
      echo 1
      echo 2
    }

When a block is long, it's more readable than shell's postfix style:

    { echo 1
      echo 2
    } >out.txt

## Private

Private builtins are not enabled by default:

    sleep 0.1          # runs external process; private builtin not found
    builtin sleep 0.1  # runs private builtin

### cat

`cat` is a *private* builtin that reads from files and writes to stdout.

    cat FILE+  # Read from each file, and write to stdout
               # If the file is -, read from stdin (not the file called -)
    cat        # equivalent to cat -

- Related: [rewrite_extern][]

[rewrite_extern]: chap-option.html#rewrite_extern

### rm

`rm` is a *private* builtin that removes files.

    rm FLAG* FILE*

Flags:

    -f   Don't fail if the file exist, and don't fail if no arguments are
         passed.

Return 0 on success, and non-zero otherwise.

- Related: [rewrite_extern][]

### sleep

`sleep` is a *private* builtin that puts the shell process to sleep for the
given number of seconds.

Example:

    builtin sleep 0.1  # wait 100 milliseconds

It respects signals:

- `SIGINT` / Ctrl-C cancels the command, with the standard behavior:
  - in an interactive shell, you return to the prompt
  - a non-interactive shell is cancelled
- Upon receiving other signals, Oils run pending traps, and then continues to
  sleep.

It's compatible with the POSIX `sleep` utility:

    sleep 2            # wait 2 seconds

## Hay Config

### hay

### haynode


## Data Formats

### json

Write JSON:

    var d = {name: 'bob', age: 42}
    json write (d)                     # default indent of 2, type errors
    json write (d, space=0)            # no indent
    json write (d, type_errors=false)  # non-serializable types become null
                                       # (e.g. Obj, Proc, Eggex)

Read JSON:

    echo hi | json read  # fills $_reply by default

Or use an explicit place:

    var x = ''
    json read (&x) < myfile.txt

Related: [err-json-encode][] and [err-json-decode][]

[err-json-encode]: chap-errors.html#err-json-encode
[err-json-decode]: chap-errors.html#err-json-decode

### json8

Like `json`, but on the encoding side:

- Falls back to `b'\yff'` instead of lossy Unicode replacement char

On decoding side:

- Understands `b'' u''` strings

Related: [err-json8-encode]() and [err-json8-decode]()

[err-json8-encode]: chap-errors.html#err-json8-encode
[err-json8-decode]: chap-errors.html#err-json8-decode

## I/O

These builtins take input and output.  They're often used with redirects.

### read

    read FLAG* VAR*

Read input from `stdin`, and assign pieces of input to variables.  Without
flags, `read` uses this algorithm:

1. Read bytes from `stdin`, one at a time, until a newline `\n`.
   - Respect `\` escapes and line continuations.
   - Any NUL bytes are removed from the input.
1. Use the `$IFS` algorithm to split the line into N pieces, where `N` is the
   number of `VAR` specified.  Each piece is assigned to the corresponding
   variable.
   - If no VARs are given, assign to the `$REPLY` var.

The `-r` flag is useful to disable backslash escapes.

POSIX mandates the slow behavior of reading one byte at a time.  In YSH, you
can avoid this by using [io.stdin][], or a `--long-flag` documented in
[ysh-read](#ysh-read).

Flags:

    -a ARRAY  assign the tokens to elements of this array
    -d CHAR   use DELIM as delimiter, instead of newline
    -n NUM    read up to NUM characters, respecting delimiters. When -r is not
              specified, backslash escape of the form "\?" is counted as one
              character. This is the Bash behavior, but other shells such as
              ash and mksh count the number of bytes with "-n" without
              considering backslash escaping.
    -p STR    print the string PROMPT before reading input
    -r        raw mode: don't let backslashes escape characters
    -s        silent: do not echo input coming from a terminal
    -t NUM    time out and fail after TIME seconds
              -t 0 returns whether any input is available
    -u FD     read from file descriptor FD instead of 0 (stdin)

  <!--  -N NUM    read up to NUM characters, ignoring delimiters -->
  <!--  -e        use readline to obtain the line
        -i STR    use STR as the initial text for readline -->

Performance summary: [YSH Input/Output > Three Types of I/O][ysh-io-three]

### echo

    echo FLAG* ARG*

Prints ARGs to stdout, separated by a space, and terminated by a newline.

Flags:

    -e  enable interpretation of backslash escapes
    -n  omit the trailing newline
<!--  -E  -->

`echo` in YSH does **not** accept these flags.  See [ysh-echo](#ysh-echo) and
[the FAQ entry][echo-en].  (This is unusual because YSH doesn't usually "break"
OSH.)

See [char-escapes](chap-mini-lang.html#char-escapes) to see what's supported
when `-e` is passed.

### printf

    printf FLAG* FMT ARG*

Formats values and prints them.  The FMT string contain three types of objects:

1. Literal Characters
2. Character escapes like `\t`.  See [char-escapes](chap-mini-lang.html#char-escapes).
3. Percent codes like `%s` that specify how to format each each ARG.

If not enough ARGS are passed, the empty string is used.  If too many are
passed, the FMT string will be "recycled".

Flags:

    -v VAR  Write output in variable VAR instead of standard output.

Format specifiers:

    %%  Prints a single "%".
    %b  Interprets backslash escapes while printing.
    %q  Prints the argument escaping the characters needed to make it reusable
        as shell input.
    %d  Print as signed decimal number.
    %i  Same as %d.
    %o  Print as unsigned octal number.
    %u  Print as unsigned decimal number.
    %x  Print as unsigned hexadecimal number with lower-case hex-digits (a-f).
    %X  Same as %x, but with upper-case hex-digits (A-F).
    %f  Print as floating point number.
    %e  Print as a double number, in "±e" format (lower-case e).
    %E  Same as %e, but with an upper-case E.
    %g  Interprets the argument as double, but prints it like %f or %e.
    %G  Same as %g, but print it like %E.
    %c  Print as a single char, only the first character is printed.
    %s  Print as string
    %n  The number of characters printed so far is stored in the variable named
        in the argument.
    %a  Interprets the argument as double, and prints it like a C99 hexadecimal
        floating-point literal.
    %A  Same as %a, but print it like %E.
    %(FORMAT)T  Prints date and time, according to FORMAT as a format string
                for strftime(3). The argument is the number of seconds since
                epoch. It can also be -1 (current time, also the default value
                if there is no argument) or -2 (shell startup time).

### readarray

Alias for `mapfile`.

### mapfile

    mapfile FLAG* ARRAY?

Reads lines from stdin into the variable named ARRAY (default
`${MAPFILE[@]}`).

Flags:

    -t       Remove the trailing newline from every line
<!--
  -d CHAR  use CHAR as delimiter, instead of the default newline
  -n NUM   copy up to NUM lines
  -O NUM   begins copying lines at the NUM element of the array
  -s NUM   discard the first NUM lines
  -u FD    read from FD file descriptor instead of the standard input
  -C CMD   run CMD every NUM lines specified in -c
  -c NUM   every NUM lines, the CMD command in C will be run
-->

## Run Code

These builtins accept shell code and run it.

### source

    source SCRIPT ARG*

Execute SCRIPT with the given ARGs, in the context of the current shell.  That is,
existing variables will be modified.

---

Oils extension: If the SCRIPT starts with `///`, we look for scripts embedded in
the `oils-for-unix` binary.  Example:

    source ///osh/two.sh     # load embedded script

    : ${LIB_OSH=fallback/dir}
    source $LIB_OSH/two.sh   # same thing

The [LIB_OSH][] form is useful for writing a script that works under both bash
and OSH.

- Related: the [cat-em][] tool prints embedded scripts.

[LIB_OSH]: chap-special-var.html#LIB_OSH
[cat-em]: chap-front-end.html#cat-em


### cmd/eval

    eval ARG+

Creates a string by joining ARGs with a space, then runs it as a shell command.

Example:

     # Create the string echo "hello $name" and run it.
     a='echo'
     b='"hello $name"'
     eval $a $b

Tips:

- Using `eval` can confuse code and user-supplied data, leading to [security
issues][].
- Prefer passing single string ARG to `eval`.

[security issues]: https://mywiki.wooledge.org/BashFAQ/048

### trap

    trap FLAG* CMD SIGNAL*

Registers the shell string CMD to be run after the SIGNALs are received.  If
the CMD is empty, then the signal is ignored.

Flags:

    -l  Lists all signals and their signal number
    -p  Prints a list of the installed signal handlers

Tip:

Prefer passing the name of a shell function to `trap`.

See [Chapter: Plugins and Hooks > Traps](chap-plugin.html#Traps) for a list of
traps, like `trap '' EXIT`.

## Set Options

The `set` and `shopt` builtins set global shell options.  YSH code should use
the more natural `shopt`.

### set

    set FLAG* ARG*

Sets global shell options. Short style:

    set -e

Long style:

    set -o errexit

Set the arguments array:

    set -- 1 2 3

See [Chapter: Global Shell Options](chap-option.html) for a list of options.

### shopt

    shopt FLAG* OPTION* BLOCK?

Sets global shell options.

Flags:

    -s --set    Turn the named options on
    -u --unset  Turn the named options off
    -p          Print option values, and 1 if any option is unset
    -o          Use older set of options, normally controlled by 'set -o'
    -q          Return 0 if the option is true, else 1

This command is compatible with `shopt` in bash.  See [ysh-shopt](#ysh-shopt) for
details on YSH enhancements.

See [Chapter: Global Shell Options](chap-option.html) for a list of options.

## Working Dir

These 5 builtins deal with the working directory of the shell.

### cd

    cd FLAG* DIR

Changes the working directory of the current shell process to DIR.

If DIR isn't specified, change to `$HOME`.  If DIR is `-`, change to `$OLDPWD`
(a variable that the sets to the previous working directory.)

Flags:

    -L  Follow symbolic links, i.e. change to the TARGET of the symlink.
        (default).
    -P  Don't follow symbolic links.

### pwd

    pwd FLAG*

Prints the current working directory.

Flags:

    -L  Follow symbolic links if present (default)
    -P  Don't follow symbolic links.  Print the link instead of the target.

### pushd

<!--pushd FLAGS DIR-->
    pushd DIR
<!--pushd +/-NUM-->

Add DIR to the directory stack, then change the working directory to DIR.
Typically used with `popd` and `dirs`.

<!--FLAGS:
  -n  Don't change the working directory, just manipulate the stack 
NUM:
  Rotates the stack the number of places specified. Eg, given the stack
  '/foo /bar /baz', where '/foo' is the top of the stack, pushd +1 will move
  it to the bottom, '/bar /baz /foo'-->

### popd

    popd

Removes a directory from the directory stack, and changes the working directory
to it.  Typically used with `pushd` and `dirs`.

### dirs

    dirs FLAG*

Shows the contents of the directory stack.  Typically used with `pushd` and
`popd`.

Flags:

    -c  Clear the dir stack.
    -l  Show the dir stack, but with the real path instead of ~.
    -p  Show the dir stack, but formatted as one line per entry.
    -v  Like -p, but numbering each line.

## Completion

These builtins implement our bash-compatible autocompletion system.

### complete

Registers completion policies for different commands.

### compgen

Generates completion candidates inside a user-defined completion function.

It can also be used in scripts, i.e. outside a completion function.

### compopt

Changes completion options inside a user-defined completion function.

### compadjust

Adjusts `COMP_ARGV` according to specified delimiters, and optionally set
variables cur, prev, words (an array), and cword.  May also set 'split'.

This is an OSH extension that makes it easier to run the bash-completion
project.

### compexport

Complete an entire shell command string.  For example,

    compexport -c 'echo $H'

will complete variables like `$HOME`.  And

    compexport -c 'ha'

will complete builtins like `hay`, as well as external commands.


## Shell Process

These builtins mutate the state of the shell process.

### exec

    exec BIN_PATH ARG*

Replaces the running shell with the binary specified, which is passed ARGs.
BIN_PATH must exist on the file system; i.e. it can't be a shell builtin or
function.

### umask

    umask MODE?

Sets the bit mask that determines the permissions for new files and
directories.  The mask is subtracted from 666 for files and 777 for
directories.

Oils currently supports writing masks in octal.

If no MODE, show the current mask.

### ulimit

    ulimit --all
    ulimit -a
    ulimit FLAGS* -RESOURCE_FLAG VALUE?

    ulimit FLAGS* VALUE?  # discouraged

Show and modify process resource limits.

Flags:

    -S  for soft limit
    -H  for hard limit

    -c -d -f ...  # ulimit --all shows all resource flags

Show a table of resources:

    ulimit --all
    ulimit -a

For example, the table shows that `-n` is the flag that controls the number
file descriptors, the soft and hard limit for `-n`, and the multiplication
"factor" for the integer VALUE you pass.

---

Here are examples of using resource flags.

Get the soft limit for the number of file descriptors:
 
    ulimit -S -n
    ulimit -n     # same thing

Get the hard limit:

    ulimit -H -n

Set the soft or hard limit:

    ulimit -S -n 100
    ulimit -H -n 100

Set both limits:

    ulimit -n 100

A special case that's discouraged: with no resource flag, `-f` is assumed:

    ulimit      # equivalent to ulimit -f
    ulimit 100  # equivalent to ulimit -f 100

### times

    times

Shows the user and system time used by the shell and its child processes.

## Child Process

### jobs

    jobs

Shows all jobs running in the shell and their status.

### wait

Wait for jobs to finish, in a few different ways.  (A job is a process or a
pipeline.)

    wait  # no arguments

Wait for all jobs to terminate.  The exit status is 0, unless a signal occurs.

    wait -n

Wait for the next job to terminate, and return its status.

    wait $pid1 $pid2 ...

Wait for the jobs specified by PIDs to terminate.  Return the status of the
last one.

    wait %3 %2 ...

Wait for the jobs specified by "job specs" to terminate.  Return the status of
the last one.

---

If wait is interrupted by a signal, the exit status is the signal number + 128.

---

When using `set -e` aka `errexit`, `wait --all` is useful.  See topic
[ysh-wait](#ysh-wait).

<!--
The ARG can be a PID (tracked by the kernel), or a job number (tracked by the
shell).  Specify jobs with the syntax `%jobnumber`.
-->

### ysh-wait

YSH extends the `wait` builtin with 2 flags:

    wait --all      # wait for all jobs, like 'wait'
                    # but exit 1 if any job exits non-zero

    wait --verbose  # show a message on each job completion

    wait --all --verbose  # show a message, and also respect failure

### fg

    fg JOB?

Continues a stopped job in the foreground.  This means it can receive signals
from the keyboard, like Ctrl-C and Ctrl-Z.

If no JOB is specified, use the latest job.

### bg

UNIMPLEMENTED

    bg JOB?

Continues a stopped job, while keeping it in the background.  This means it
**can't** receive signals from the keyboard, like Ctrl-C and Ctrl-Z.

If no JOB is specified, use the latest job.

### kill

UNIMPLEMENTED

<!-- Note: 'kill' accepts job specs like %2 -->

## External

### test

    test OP ARG
    test ARG OP ARG
    [ OP ARG ]      # [ is an alias for test that requires closing ]
    [ ARG OP ARG ]

Evaluates a conditional expression and returns 0 (true) or 1 (false).

Note that `[` is the name of a builtin, not an operator in the language.  Use
`test` to avoid this confusion.

String expressions:

    -n STR           True if STR is not empty.
                     'test STR' is usually equivalent, but discouraged.
    -z STR           True if STR is empty.
    STR1 = STR2      True if the strings are equal.
    STR1 != STR2     True if the strings are not equal.
    STR1 < STR2      True if STR1 sorts before STR2 lexicographically.
    STR1 > STR2      True if STR1 sorts after STR2 lexicographically.
                     Note: < and > should be quoted like \< and \>

File expressions:

    -a FILE          Synonym for -e.
    -b FILE          True if FILE is a block special file.
    -c FILE          True if FILE is a character special file.
    -d FILE          True if FILE is a directory.
    -e FILE          True if FILE exists.
    -f FILE          True if FILE is a regular file.
    -g FILE          True if FILE has the sgid bit set.
    -G FILE          True if current user's group is also FILE's group.
    -h FILE          True if FILE is a symbolic link.
    -L FILE          True if FILE is a symbolic link.
    -k FILE          True if FILE has the sticky bit set.
    -O FILE          True if current user is the file owner.
    -p FILE          True if FILE is a named pipe (FIFO).
    -r FILE          True if FILE is readable.
    -s FILE          True if FILE has size bigger than 0.
    -S FILE          True if FILE is a socket file.
    -t FD            True if file descriptor FD is open and refers to a terminal.
    -u FILE          True if FILE has suid bit set.
    -w FILE          True if FILE is writable.
    -x FILE          True if FILE is executable.
    FILE1 -nt FILE2  True if FILE1 is newer than FILE2 (mtime).
    FILE1 -ot FILE2  True if FILE1 is older than FILE2 (mtime).
    FILE1 -ef FILE2  True if FILE1 is a hard link to FILE2.
<!--    -N FILE  True if FILE was modified since last read (mtime newer than atime).-->

Arithmetic expressions coerce arguments to integers, then compare:

    INT1 -eq INT2    True if they're equal.
    INT1 -ne INT2    True if they're not equal.
    INT1 -lt INT2    True if INT1 is less than INT2.
    INT1 -le INT2    True if INT1 is less or equal than INT2.
    INT1 -gt INT2    True if INT1 is greater than INT2.
    INT1 -ge INT2    True if INT1 is greater or equal than INT2.

Other expressions:

    -o OPTION        True if the shell option OPTION is set.
    -v VAR           True if the variable VAR is set.

The test builtin also supports POSIX conditionals like -a, -o, !, and ( ), but
these are discouraged.

<!--    -R VAR     True if the variable VAR has been set and is a nameref variable. -->

---

See [ysh-test](#ysh-test) for log flags like `--file` and `--true`.

### getopts

    getopts SPEC VAR ARG*

A single iteration of flag parsing.  The SPEC is a sequence of flag characters,
with a trailing `:` to indicate that the flag takes an argument:

    ab    # accept  -a and -b
    xy:z  # accept -x, -y arg, and -z

The input is `"$@"` by default, unless ARGs are passed.

On each iteration, the flag character is stored in VAR.  If the flag has an
argument, it's stored in `$OPTARG`.  When an error occurs, VAR is set to `?`
and `$OPTARG` is unset.

Returns 0 if a flag is parsed, or 1 on end of input or another error.

Example:

    while getopts "ab:" flag; do
        case $flag in
            a)   flag_a=1 ;;
            b)   flag_b=$OPTARG" ;;
            '?') echo 'Invalid Syntax'; break ;;
        esac
    done

Notes:
- `$OPTIND` is initialized to 1 every time a shell starts, and is used to
  maintain state between invocations of `getopts`.
- The characters `:` and `?` can't be flags.


## Conditional

### cmd/true

Do nothing and return status 0.

    if true; then
      echo hello
    fi

### cmd/false

Do nothing and return status 1.

    if false; then
      echo 'not reached'
    else
      echo hello
    fi

<h3 id="colon" class="osh-topic">colon :</h3>

Like `true`: do nothing and return status 0.

## Introspection

<h3 id="help" class="osh-topic ysh-topic" oils-embed="1">
  help
</h3>

<!-- pre-formatted for help builtin -->

```
Usage: help TOPIC?

Examples:

    help               # this help
    help echo          # help on the 'echo' builtin
    help command-sub   # help on command sub $(date)

    help oils-usage    # identical to oils-for-unix --help
    help osh-usage     #              osh --help
    help ysh-usage     #              ysh --help
```

### hash

    hash

Display information about remembered commands.

    hash FLAG* CMD+

Determine the locations of commands using `$PATH`, and remember them.

Flag:

    -r       Discard all remembered locations.
<!--    -d       Discard the remembered location of each NAME.
    -l       Display output in a format reusable as input.
    -p PATH  Inhibit path search, PATH is used as location for NAME.
    -t       Print the full path of one or more NAME.-->

### cmd/type

    type FLAG* NAME+

Print the type of each NAME, if it were the first word of a command.  Is it a
shell keyword, builtin command, shell function, alias, or executable file on
$PATH?

Flags:

    -a  Show all possible candidates, not just the first one
    -f  Don't search for shell functions
    -P  Only search for executable files
    -t  Print a single word: alias, builtin, file, function, proc, keyword

Note: [`invoke --show`][invoke] is more general than `type`.

Similar names: [type][]

[type]: chap-index.html#type

<!-- TODO:
- procs are counted as shell functions, should be their own thing
- Hay nodes ('hay define x') also live in the first word namespace, and should
  be recognized
-->

Modeled after the [bash `type`
builtin](https://www.gnu.org/software/bash/manual/bash.html#index-type).
 
## Word Lookup

### invoke

The `invoke` builtin allows more control over name lookup than [simple
commands][simple-command].

[simple-command]: chap-cmd-lang.html#simple-command

Usage:

    invoke --show NAME*          # Show info about EACH name
    invoke NAMESPACE_FLAG+ ARG*  # Run a single command with this arg array

Namespace flags:

    --proc      Run YSH procs 
                including invokable obj
    --sh-func   Run shell functions
    --builtin   Run builtin commands (of any kind)
                eval : POSIX special
                cd   : normal
                sleep: private (Oils)
    --extern    Run external commands, like /bin/ls

Multiple namespace flags may be passed.  They are searched in that order:
procs, shell functions, builtins, then extern.  The first one wins.  (This is
different than [command-lookup-order][].)

[command-lookup-order]: chap-cmd-lang.html#command-lookup-order

If the name isn't found, then `invoke` returns status 127.

---

Run `invoke --show NAME` to see all categories a name is found in.

- The `--show` flag respects the [command-lookup-order][]
- Shell keywords and aliases are shown, but `invoke` doesn't run them.

---

Examples:

    invoke ls                          # usage error: no namespace flags

    invoke --builtin          echo hi  # like builtin echo hi
    invoke --builtin --extern ls /tmp  # like command ls /tmp (no function lookup)

    invoke --show true sleep ls        # similar to type -a true sleep ls

Related:

- [builtin][] - like `--builtin`
- [command][] - like `--builtin --extern`
- [runproc][] - like `--proc --sh-func`
- [type][cmd/type] - like `--show`

[builtin]: chap-builtin-cmd.html#builtin
[command]: chap-builtin-cmd.html#command
[runproc]: chap-builtin-cmd.html#runproc
[cmd/type]: chap-builtin-cmd.html#cmd/type
[command-lookup-order]: chap-cmd-lang.html#command-lookup-order

### runproc

Runs a named proc with the given arguments.  It's often useful as the only top
level statement in a "task file":

    proc p {
      echo hi
    }
    runproc @ARGV
    
Like 'builtin' and 'command', it affects the lookup of the first word.

### command

    command FLAG* CMD ARG*

Look up CMD as a shell builtin or executable file, and execute it with the
given ARGs.

Flags:

    -v  Instead of executing CMD, print a description of it.
<!--    -p  Use a default value for PATH that is guaranteed to find all of the
        standard utilities.
    -V  Print a more verbose description of CMD.-->

Note: [`invoke --show`][invoke] is more general than `command -v`.

[invoke]: chap-builtin-cmd.html#invoke

### builtin

    builtin CMD ARG*

Look up CMD as a shell builtin, and execute it with the given ARGs.

## Interactive

### alias

    alias NAME=CODE

Make NAME a shortcut for executing CODE, e.g. `alias hi='echo hello'`.

    alias NAME

Show the value of this alias.

    alias

Show a list of all aliases.

Tips:

Prefer shell functions like:

    ls() {
      command ls --color "$@"
    }

to aliases like:

    alias ls='ls --color'
    
Functions are less likely to cause parsing problems.

- Quoting like `\ls` or `'ls'` disables alias expansion
- To remove an existing alias, use [unalias](chap-builtin-cmd.html#unalias).

### unalias

    unalias NAME

Remove the alias NAME.

<!--Flag:

    -a  Removes all existing aliases.-->

### history

    history FLAG*

Display and manipulate the shell's history entries.

    history NUM

Show the last NUM history entries.

Flags:

    -c      Clears the history.
    -d POS  Deletes the history entry at position POS.
<!--    -a
    -n
    -r
    -w
    -p
    -s -->

### fc

    fc FLAG* FIRST? LAST?

"Fix a command" from the shell's history.

`fc -l` displays commands.  FIRST and LAST specify a range of command numbers,
where:

- A positive number is an index into the history list.
- A negative number is an offset from the current command.
- If FIRST is omitted, the value `-16` is used.
- If LAST is omitted, the current command is used.

Flags:

    -l  List commands (rather than editing)
    -n  Omit line numbers
    -r  Use reverse order (newest first)

<!-- 
Not implemented

-e EDITOR
-s
-->

## Unsupported

### enable

Bash has this, but OSH won't implement it.

