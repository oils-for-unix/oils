---
in_progress: yes
css_files: ../web/base.css ../web/manual.css ../web/help.css ../web/toc.css
body_css_class: width40 help-body
---

YSH Help
========

This doc describes every aspect of YSH briefly.  It underlies the `help`
builtin, and is indexed by keywords.

Navigate it with the [index of YSH help topics](oil-help-topics.html).

<!--
IMPORTANT: This doc is processed in TWO WAYS.  Be careful when editing.

It generates both HTML and text for the 'help' builtin.
-->

<div id="toc">
</div>

<h2 id="command">Command Language</h2>

#### proc

Procs are shell-like functions, but with named parameters, and without dynamic
scope (TODO):

    proc copy(src, dest) {
      cp --verbose --verbose $src $dest
    }

Compare with [sh-func]($osh-help).

#### ysh-if

Command or expression:

    if (x > 0) {
      echo 'positive'
    }

#### ysh-case

    case $x {
      # balanced parens around patterns
      (*.py)     echo 'Python' ;;
      ('README') echo 'README' ;;  # consatnt words must be quoted
      (*)        echo 'Other'  ;;
    }

#### ysh-while

Command or expression:

    var x = 5
    while (x < 0) {
      setvar x -= 1
    }

#### ysh-for

Two forms for shell-style loops:

    for name in *.py {
      echo "$name"
    }

    for i, name in *.py {
      echo "$i $name"
    }

Two forms for expressions that evaluate to a `List`:

    for item in (mylist) {
      echo "$item"
    }

    for i, item in (mylist) {
      echo "$i $item"
    }

Three forms for expressions that evaluate to a `Dict`:

    for key in (mydict) {
      echo "$key"
    }

    for key, value in (mydict) {
      echo "$key $value"
    }

    for i, key, value in (mydict) {
      echo "$i $key $value"
    }

#### equal

The `=` keyword evaluates an expression and shows the result:

    oil$ = 1 + 2*3
    (Int)   7

It's meant to be used interactively.  Think of it as an assignment with no
variable on the left.

#### underscore

The `_` keyword evaluates an expression and throws away the result:

    var x = :| one two |
    _ x.append('three')

Think of it as a shortcut for `_ = expr` (throwaway assignment).

#### typed-arg

Internal commands (procs and builtins) accept typed arguments.

    json write (myobj)

TODO: Implement these

    eval (myblock)
    assert (x > 0)

#### block-arg

Blocks can be passed to builtins (and procs eventually):

    cd /tmp {
      echo $PWD  # prints /tmp
    }
    echo $PWD

Compare with [sh-block]($osh-help).

<h2 id="expr">Expression Language and Assignments</h2>


### Keywords

#### const 

Initializes a constant name to the Oil expression on the right.

    const c = 'mystr'        # equivalent to readonly c=mystr
    const pat = / digit+ /   # an eggex, with no shell equivalent

It's either a global constant or scoped to the current function.

#### var

Initializes a name to the Oil expression on the right.

    var s = 'mystr'        # equivalent to declare s=mystr
    var pat = / digit+ /   # an eggex, with no shell equivalent

It's either global or scoped to the current function.

#### setvar

At the top-level, setvar creates or mutates a variable.

Inside a proc, it mutates a local variable declared with var.

#### setglobal

Creates or mutates a global variable.

#### setref

Mutates a variable through a named reference.  See examples in
doc/variables.md.


### Literals

#### bool-literal

Oil uses JavaScript-like spellings for these three "atoms":

    true   false   null

Note that the empty string is a good "special" value in some cases.  The `null`
value can't be interpolated into words.

#### int-literal

    var myint = 42
    var myfloat = 3.14
    var float2 = 1e100

#### rune-literal

    #'a'   #'_'   \n   \\   \u{3bc}

#### str-literal

Oil strings appear in expression contexts, and look like shell strings:

    var s = 'foo'
    var double = "hello $world and $(hostname)"

However, strings with backslashes are forced to specify whether they're **raw**
strings or C-style strings:

    var s = 'line\n'    # parse error: ambiguous

    var s = $'line\n'   # C-style string

    var s = r'[a-z]\n'  # raw strings are useful for regexes (not eggexes)

    var unicode = 'mu = \u{3bc}'

#### list-literal

Lists have a Python-like syntax:

    var mylist = ['one', 'two', 3]

And a shell-like syntax:

    var list2 = %| one two |

The shell-like syntax accepts the same syntax that a command can:

    ls $mystr @ARGV *.py {foo,bar}@example.com

    # Rather than executing ls, evaluate and store words
    var cmd = :| ls $mystr @ARGV *.py {foo,bar}@example.com |

#### dict-literal

    {name: 'value'}

#### block-literal

    var myblock = ^(echo $PWD)

#### expr-lit

    var myexpr = ^[1 + 2*3]

### Operators

#### concat

    var s = 's'
    var concat1 = s ++ '_suffix'
    var concat2 = "${s}_suffix"  # similar

    var c = :| one two |
    var concat3 = c ++ :| three 4 |
    var concat4 = :| @c three 4 |

    var mydict = {a: 1, b: 2}
    var otherdict = {a: 10, c: 20}
    var concat5 = mydict ++ otherdict


#### ysh-compare

    a == b        # Python-like equality, no type conversion
    3 ~== 3.0     # True, type conversion
    3 ~== '3'     # True, type conversion
    3 ~== '3.0'   # True, type conversion

#### ysh-logical

    not  and  or

Note that these are distinct from `!  &&  ||`.

#### ysh-arith

    +  -  *  /   //   %   **

#### ysh-bitwise

    ~  &  |  ^

#### ysh-ternary

Like Python:

    display = 'yes' if len(s) else 'empty'

#### ysh-index

Like Python:

    myarray[3]
    mystr[3]

TODO: Does string indexing give you an integer back?

#### ysh-slice

Like Python:

    myarray[1 : -1]
    mystr[1 : -1]

#### func-call

Like Python:

    f(x, y)


#### match-ops

    ~   !~   ~~   !~~

### Eggex

#### re-literal

#### re-compound

#### re-primitive

#### named-class

#### class-literal

#### re-flags

#### re-multiline

Not implemented.


<h2 id="word">Word Language</h2>

#### inline-call

#### expr-sub

#### expr-splice

#### var-splice


<h2 id="builtins">Builtin Commands</h2>

### Memory

#### append

Append a string to an array of strings:

    var mylist = :| one two |
    append :mylist three

This is a command-mode synonym for the expression:

    _ mylist.append('three')

#### pp

Pretty prints interpreter state.  Some of these are implementation details,
subject to change.

Examples:

    pp proc  # print all procs and their doc comments

    var x = :| one two |
    pp cell x  # print a cell, which is a location for a value

### Handle Errors

#### try

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

#### boolstatus

Runs a command and requires the exit code to be 0 or 1.

    if boolstatus egrep '[0-9]+' myfile {  # may abort
      echo 'found'               # status 0 means found
    } else {
      echo 'not found'           # status 1 means not found
    }



### Shell State

#### ysh-cd

It takes a block:

    cd / {
      echo $PWD
    }

#### ysh-shopt

It takes a block:

    shopt --unset errexit {
      false
      echo 'ok'
    }

#### shvar

Execute a block with a global variable set.

    shvar IFS=/ {
      echo "ifs is $IFS"
    }
    echo "ifs restored to $IFS"

#### push-registers

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


### Modules

#### runproc

Runs a named proc with the given arguments.  It's often useful as the only top
level statement in a "task file":

    proc p {
      echo hi
    }
    runproc @ARGV
    
Like 'builtin' and 'command', it affects the lookup of the first word.

#### module

Registers a name in the global module dict.  Returns 0 if it doesn't exist, or
1 if it does.

Use it like this in executable files:

    module main || return 0   

And like this in libraries:

    module myfile.oil || return 0   

#### use

Make declarations about the current file.

For files that contain embedded DSLs:

    use dialect ninja  # requires that _DIALECT is set to 'ninja'

An accepted declaration that tools can use, but isn't used by Oil:

    use bin grep sed

### I/O

#### ysh-read

Oil adds buffered, line-oriented I/O to shell's `read`.

    read --line             # default var is $_line
    read --line --with-eol  # keep the \n
    read --line --qsn       # decode QSN too
    read --all              # whole file including newline; var is $_all
    read -0                 # read until NUL, synonym for read -r -d ''

When --qsn is passed, the line is check for an opening single quote.  If so,
it's decoded as QSN.  The line must have a closing single quote, and there
can't be any non-whitespace characters after it.

#### write

write fixes problems with shell's `echo` builtin.

The default separator is a newline, and the default terminator is a
newline.

Examples:

    write -- ale bean        # write two lines
    write --qsn -- ale bean  # QSN encode, guarantees two lines
    write -n -- ale bean     # synonym for --end '', like echo -n
    write --sep '' --end '' -- a b        # write 2 bytes
    write --sep $'\t' --end $'\n' -- a b  # TSV line

#### fork

The preferred alternative to shell's `&`.

    fork { sleep 1 }
    wait -n

#### forkwait

The preferred alternative to shell's `()`.  Prefer `cd` with a block if possible.

    forkwait {
      not_mutated=zzz
    }
    echo $not_mutated



### Data Formats

#### json

Write JSON:

    var d = {name: 'bob', age: 42}
    json write (d)

Read JSON into a variable:

    var x = ''
    json read :x < myfile.txt


### Testing

TODO: describe

### External Lang

TODO: when

<h2 id="option">Shell Options</h2>

### Option Groups

<!-- note: explicit anchor necessary because of mangling -->
<h4 id="strict:all">strict:all</h4>

Option in this group disallow problematic or confusing shell constructs.  The
resulting script will still run in another shell.

    shopt --set strict:all  # turn on all options
    shopt -p strict:all     # print their current state

<h4 id="ysh:upgrade">ysh:upgrade</h4>

Options in this group enable Oil features that are less likely to break
existing shell scripts.

For example, `parse_at` means that `@myarray` is now the operation to splice
an array.  This will break scripts that expect `@` to be literal, but you can
simply quote it like `'@literal'` to fix the problem.

    shopt --set ysh:upgrade   # turn on all options
    shopt -p ysh:upgrade      # print their current state

<h4 id="ysh:all">ysh:all</h4>

Enable the full Oil language.  This includes everything in the `ysh:upgrade`
group.

    shopt --set ysh:all     # turn on all options
    shopt -p ysh:all        # print their current state

### Strictness

#### strict_control_flow

Disallow `break` and `continue` at the top level, and disallow empty args like
`return $empty`.

#### strict_tilde

Failed tilde expansions cause hard errors (like zsh) rather than silently
evaluating to `~` or `~bad`.

#### strict_word_eval

TODO

#### strict_nameref

When `strict_nameref` is set, undefined references produce fatal errors:

    declare -n ref
    echo $ref  # fatal error, not empty string
    ref=x      # fatal error instead of decaying to non-reference

References that don't contain variables also produce hard errors:

    declare -n ref='not a var'
    echo $ref  # fatal
    ref=x      # fatal

#### parse_ignored

For compatibility, Oil will parse some constructs it doesn't execute, like:

    return 0 2>&1  # redirect on control flow

When this option is disabled, that statement is a syntax error.

### Oil Basic

#### parse_at

TODO

#### parse_brace

TODO

#### parse_paren

TODO

#### parse_raw_string

Allow the r prefix for raw strings in command mode:

    echo r'\'  # a single backslash

Since shell strings are already raw, this means that Oil just ignores the r
prefix.

#### command_sub_errexit

TODO

#### process_sub_fail

TODO

#### sigpipe_status_ok

If a process that's part of a pipeline exits with status 141 when this is
option is on, it's turned into status 0, which avoids failure.

SIGPIPE errors occur in cases like 'yes | head', and generally aren't useful.

#### simple_word_eval

TODO:

<!-- See doc/simple-word-eval.html -->

### Oil Breaking

#### copy_env

#### parse_equals

<h2 id="special">Special Variables</h2>

### Shell Vars

#### `ARGV`

Replacement for `"$@"`

#### `_DIALECT`

Name of a dialect being evaluated.

#### `_this_dir`

The directory the current script resides in.  This knows about 3 situations:

- The location of `oshrc` in an interactive shell
- The location of the main script, e.g. in `osh myscript.sh`
- The location of script loaded with the `source` builtin

It's useful for "relative imports".

### Platform

#### OIL_VERSION

The version of Oil that is being run, e.g. `0.9.0`.

<!-- TODO: specify comparison algorithm. -->

### Exit Status


#### `_status`

Set by the `try` builtin.

    try ls /bad
    if (_status !== 0) {
      echo 'failed'
    }

#### `_pipeline_status`

Alias for [PIPESTATUS]($osh-help).

#### `_process_sub_status`

The exit status of all the process subs in the last command.

### Tracing

#### SHX_indent

#### SHX_punct

#### SHX_pid_str

<h2 id="lib">Oil Libraries</h2>

### Pattern

#### `_match()`

#### `_start()`

#### `_end()`

### Collections

#### len()

- `len(mystr)` is its length in bytes
- `len(myarray)` is the number of elements
- `len(assocarray)` is the number of pairs

### String

#### find 

#### sub 

#### join 

Given an array of strings, returns a string.

    var x = ['a', 'b', 'c']

    $ echo $[join(x)]
    abc

    $ echo $[join(x, ' ')]  # optional delimiter
    a b c

#### split

<!--
Note: This is currently SplitForWordEval.  Could expose Python-type splitting?
-->

### Word

<!--
Note: glob() function conflicts with 'glob' language help topic
-->

#### maybe

### Arrays

- `index(A, item)` is like the awk function
- `append()` is a more general version of the `append` builtin
- `extend()`

### Assoc Arrays

- `keys()`
- `values()`

### Introspection

#### `shvar_get()`

TODO

### Config Gen

### Better Syntax

These functions give better syntax to existing shell constructs.

- `shquote()` for `printf %q` and `${x@Q}`
- `lstrip()` for `${x#prefix}` and  `${x##prefix}`
- `rstrip()` for `${x%suffix}` and  `${x%%suffix}` 
- `lstripglob()` and `rstripglob()` for slow, legacy glob
- `upper()` for `${x^^}`
- `lower()` for `${x,,}`
- `strftime()`: hidden in `printf`


### Codecs

TODO

### Hashing

TODO

