---
in_progress: yes
css_files: ../web/base.css ../web/manual.css ../web/help.css ../web/toc.css
body_css_class: width40 help-body
---

OSH Help
========

This doc describes every aspect of OSH briefly.  It underlies the `help`
builtin, and is indexed by keywords.

Navigate it with the [index of OSH help topics](osh-help-topics.html).

<!--
IMPORTANT: This doc is processed in TWO WAYS.  Be careful when editing.

It generates both HTML and text for the 'help' builtin.
-->

<div id="toc">
</div>

<h2 id="overview">Overview</h2>

### Usage

<h4 id="osh-usage"><code>bin/osh</code> Usage</h4>

    Usage: osh [OPTION]... SCRIPT [ARG]...
           osh [OPTION]... -c COMMAND [ARG]...

The command line accepted by `bin/osh` is compatible with `/bin/sh` and `bash`.

    osh -c 'echo hi'
    osh myscript.sh
    echo 'echo hi' | osh

It also has a few enhancements:

    osh -n -c 'hello'                    # pretty-print the AST
    osh --ast-format text -n -c 'hello'  # print it full

osh accepts POSIX sh flags, with these additions:

  -n             parse the program but don't execute it.  Print the AST.
  --ast-format   what format the AST should be in

<h4 id="config">Configuring the Shell</h4>

If the --rcfile flag is specified, that file will be executed on startup.
Otherwise:

- `bin/osh` runs `~/.config/oil/oshrc`
- `bin/oil` runs `~/.config/oil/oilrc`

Pass --rcfile /dev/null to disable this behavior.

<h4 id="startup">Startup Files</h4>

History is read?

### Lexing

#### comment

A comment starts with `#` and goes until the end of the line.

    echo hi  # print a greeting

#### line-continuation

A backslash `\` at the end of a line continues the line without executing it:

    ls /usr/bin \
       /usr/lib \
       ~/src        # A single command split over three lines

<h2 id="command">Command Language</h2>

### Commands

#### simple-command

Commands are composed of words.  The first word may by the name of a shell
builtin, an Oil proc / shell "function", an external command, or an alias:

    echo hi               # a shell builtin doesn't start a process
    ls /usr/bin ~/src     # starts a new process
    myproc "hello $name"
    myshellfunc "hello $name"
    myalias -l
<!-- TODO: document lookup order -->

Redirects are also allowed in any part of the command:

    echo 'to stderr' >&2
    echo >&2 'to stderr'

    echo 'to file' > out.txt
    echo > out.txt 'to file'

<h4 id="semicolon">semicolon ;</h4>

Run two commands in sequence like this:

    echo one; echo two

or this:

    echo one
    echo two

### Conditional

#### case

Match a string against a series of glob patterns.  Execute code in the section
below the matching pattern.

    path='foo.py'
    case "$path" in
      *.py)
        echo 'python'
        ;;
      *.sh)
        echo 'shell'
        ;;
    esac

#### if

Test if a command exited with status zero (true).  If so, execute the
corresponding block of code.

Shell:

    if test -d foo; then
      echo 'foo is a directory'
    elif test -f foo; then
      echo 'foo is a file'
    else
      echo 'neither'
    fi

Oil:

    if test -d foo {
      echo 'foo is a directory'
    } elif test -f foo {
      echo 'foo is a file'
    } else {
      echo 'neither'
    }

#### true

Do nothing and return status 0.

    if true; then
      echo hello
    fi

#### false

Do nothing and return status 1.

    if false; then
      echo 'not reached'
    else
      echo hello
    fi

#### colon

Like `true`: do nothing and return status 0.

#### bang 

Invert an exit code:

    if ! test -d /tmp; then   
      echo "No temp directory
    fi

#### and

    mkdir -p /tmp && cp foo /tmp

#### or

    ls || die "failed"

### Iteration

#### while

POSIX

#### until

POSIX

#### for

For loops iterate over words.

Oil style:

    var mystr = 'one'
    var myarray = %(two three)

    for i in $mystr @myarray *.py {
      echo $i
    }


Shell style:

    local mystr='one'
    local myarray=(two three)

    for i in "mystr" "${myarray[@]}" *.py; do
      echo $i
    done

Both fragments output 3 lines and then Python files on remaining lines.

#### for-expr-sh

A bash/ksh construct:

    for (( i = 0; i < 5; ++i )); do
      echo $i
    done

### Control Flow

These are keywords in Oil, not builtins!

#### break

Break out of a loop.  (Not used for case statements!)

#### continue

Continue to the next iteration of a loop.

#### return

Return from a function.

#### exit

Exit the shell process with the given status:

    exit 2

### Grouping

#### sh-func

POSIX:

    f() {
      echo args "$@"
    }
    f 1 2 3

#### sh-block

POSIX:

    { echo one; echo two; }

Note the trailing `;` -- which isn't necessary in Oil.

#### subshell

    ( echo one; echo two )

Use [forkwait]($osh-help) in Oil instead.

### Concurrency

#### pipe

#### ampersand

    CMD &

The `&` language construct runs CMD in the background as a job, immediately
returning control to the shell.

The resulting PID is recorded in the `$!` variable.

### Redirects

#### redir-file

Three variants of redirecting stdout:

    echo foo > out.txt    # write to a file
    echo foo >> out.txt   # append to a file
    echo foo >| out.txt   # clobber the file even if set -o noclobber

Redirect stdin:

    cat < in.txt

<!-- They also take a file descriptor on the left -->


#### redir-desc

Redirect to a file descriptor:

    echo 'to stderr' >&2

<!--
NOTE: >&2 is just like <&2 
There's no real difference.
-->

#### here-doc

TODO: unbalanced HTML if we use \<\<?

    cat <<EOF
    here doc with $double ${quoted} substitution
    EOF

    myfunc() {
            cat <<-EOF
            here doc with one tab leading tab stripped
            EOF
    }

    cat <<< 'here string'

<!-- TODO: delimiter can be quoted -->
<!-- Note: Python's HTML parser thinks <EOF starts a tag -->

### Other Command

<h4 id="dparen">dparen ((</h4>

<h4>time</h4>

`time [-p] pipeline`

Measures the time taken by a command / pipeline.  It uses the `getrusage()`
function from `libc`.

Note that time is a KEYWORD, not a builtin!

<!-- Note: bash respects TIMEFORMAT -->

<h2 id="assign">Assigning Variables</h2>

### Operators

#### sh-assign

#### sh-append

### Compound Data

#### sh-array

Array literals in shell accept any sequence of words, just like a command does:

    ls $mystr "$@" *.py

    # Put it in an array
    a=(ls $mystr "$@" *.py)

In Oil, use [oil-array]($oil-help).

#### sh-assoc

In Oil, use [oil-dict]($oil-help).

### Builtins

#### local

#### export

#### unset

#### shift

#### declare

#### typeset

Alias for [declare]($osh-help).

<h2 id="word">Word Language</h2>

### Quotes

#### quotes

- Single quotes
- Double Quotes
- C-style strings: `$'\n'`

Also see [oil-string]($oil-help).

### Substitutions

#### com-sub

Evaluates to the stdout of a command.  If a trailing newline is returned, it's
stripped:

    $ hostname
    example.com

    $ x=$(hostname)
    $ echo $x
    example.com

#### var-sub

Evaluates to the value of a variable:

    $ x=X
    $ echo $x ${x}
    X X

#### arith-sub

Shell has C-style arithmetic:

    $ echo $(( 1 + 2*3 ))
    7

#### tilde-sub

Used as a shortcut for a user's home directory:

    ~/src     # my home dir
    ~bob/src  # user bob's home dir

<h3>Var Ops</h3>

#### op-test

#### op-strip

#### op-replace

#### op-index

    ${a[i+1]}

#### op-slice

#### op-format

${x@P} evaluates x as a prompt string, e.g. the string that would be printed if
PS1=$x.

<h2 id="sublang">Other Shell Sublanguages</h2>

### Arithmetic

#### arith-context

#### sh-numbers

#### sh-arith

#### sh-logical

#### sh-bitwise

### Boolean

#### dbracket

Compatible with bash.

#### bool-expr

#### bool-infix

#### bool-path

#### bool-str

#### bool-other

### Patterns

#### glob

#### extglob

#### regex

Part of [dbracket]($osh-help)

### Brace Expand

#### braces

### History

#### histsub

<h2 id="builtin">Builtin Commands</h2>

### I/O

These builtins take input and output.  They're often used with redirects.

<h4 id="read">read</h4>

    read FLAG* VAR*

Read a line from stdin, split it into tokens with the `$IFS` algorithm,
and assign the tokens to the given variables.  When no VARs are given,
assign to `$REPLY`.

Flags:

    -a ARRAY  assign the tokens to elements of this array
    -d CHAR   use DELIM as delimiter, instead of newline
    -n NUM    read up to NUM characters, respecting delimiters
    -p STR    print the string PROMPT before reading input
    -r        raw mode: don't let backslashes escape characters
    -s        silent: do not echo input coming from a terminal
    -t NUM    time out and fail after TIME seconds
              -t 0 returns whether any input is available
    -u FD     read from file descriptor FD instead of 0 (stdin)

  <!--  -N NUM    read up to NUM characters, ignoring delimiters -->
  <!--  -e        use readline to obtain the line
        -i STR    use STR as the initial text for readline -->

<h4 id="echo">echo</h4>

    echo FLAG* ARG*

Prints ARGs to stdout, separated by a space, and terminated by a newline.

Flags:

    -e  enable interpretation of backslash escapes
    -n  omit the trailing newline
<!--  -E  -->

Backslash sequences recognized by -e:

    \\         backslash
    \a         (unimplemented ?) alert (BEL)
    \b         backspace
    \c         stop processing remaining input
    \e         escape next character
    \f         form feed, equivalent to \n + 4 spaces
    \n         new line
    \r         carriage return, returns to the beggining of the line
    \t         horizontal tab
    \v         vertical tab
    \0NNN      print character specified as an octal value with 1 to 3 octal
               digits 
    \xHH       print character specified as an hexadecimal value with 1 to 2
               hex digits
    \uHHHH     Unicode character specified as an hexadecimal value with 1 to
               4 hex digits 
    \UHHHHHHHH Unicode character specified as an hexadecimal value with 1 to
               8 hex digits

<h4 id="readarray">readarray</h4>

Alias for `mapfile`.

<h4 id="mapfile">mapfile</h4>

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

### Run Code

<h4 id="source">source</h4>

    source SCRIPT ARG*

Executes SCRIPT with given ARGs in the context of the current shell.  It will
modify existing variables.

<h4 id="eval">eval</h4>

    eval ARG+

Creates a string by joining ARGs with a space, then runs it as a shell command.

Example:

     # Create the string echo "hello $name" and run it.
     a='echo'
     b='"hello $name"'
     eval $a $b

Tips:

`eval` is usually unnecessary in Oil code.  Using it can confuse code and
user-supplied data, leading to [security issues][].

Prefer passing single string ARG to `eval`.

[security issues]: https://mywiki.wooledge.org/BashFAQ/048

<h4 id="trap">trap</h4>

    trap FLAG* CMD SIGNAL*

Registers the shell string CMD to be run after the SIGNALs are received.  If
the CMD is empty, then the signal is ignored.

Flags:

    -l  Lists all signals and their signal number
    -p  Prints a list of the installed signal handlers

Tip:

Prefer passing the name of a shell function to `trap`.

### Set Options

<h4 id="set">set</h4>

The set builtin modifies the shell's configuration and behavior.

<h4 id="shopt">shopt</h4>

The shopt builtin configures the shell.

### Working Dir

<h4 id="cd">cd</h4>

    cd FLAG* DIR

Changes the working directory of the current shell process to DIR.

If DIR isn't specified, change to `$HOME`.  If DIR is `-`, change to `$OLDPWD`
(a variable that the sets to the previous working directory.)

Flags:

    -L  Follow symbolic links, i.e. change to the TARGET of the symlink.
        (default).
    -P  Don't follow symbolic links.

<h4 id="pwd">pwd</h4>

    pwd FLAG*

Prints the current working directory.

Flags:

    -L  Follow symbolic links if present (default)
    -P  Don't follow symbolic links.  Print the link instead of the target.

<h4 id="pushd">pushd</h4>

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

<h4 id="popd">popd</h4>

    popd

Removes a directory from the directory stack, and changes the working directory
to it.  Typically used with `pushd` and `dirs`.

<h4 id="dirs">dirs</h4>

    dirs FLAG*

Shows the contents of the directory stack.  Typically used with `pushd` and
`popd`.

Flags:

    -c  Clear the dir stack.
    -l  Show the dir stack, but with the real path instead of ~.
    -p  Show the dir stack, but formatted as one line per entry.
    -v  Like -p, but numbering each line.

### Completion

<h4 id="complete">complete</h4>

The complete builtin registers completion policies for different commands.

<h4 id="compgen">compgen</h4>

The compgen builtin generates completion candidates inside a user-defined
completion function.

It can also be used in scripts, i.e. outside a completion function.

<h4 id="compopt">compopt</h4>

The compopt builtin changes completion options inside a user-defined completion
function.

<h4 id="compadjust">compadjust</h4>

The compadjust builtin adjusts COMP_ARGV according to specified delimiters,
and optionally set variables cur, prev, words (an array), and cword.  May also
set 'split'.

This is an OSH extension that makes it easier to run the bash-completion
project.

<h3>Shell Process</h3>

<h4 id="exec">exec</h4>

    exec BIN_PATH ARG*

Replaces the running shell with the binary specified, which is passed ARGs.
BIN_PATH must exist on the file system; i.e. it can't be a shell builtin or
function.

<h4 id="umask">umask</h4>

    umask MODE?

Sets the bit mask that determines the permissions for new files and
directories.  The mask is subtracted from 666 for files and 777 for
directories.

Oil currently supports writing masks in octal.

If no MODE, show the current mask.

<h4 id="times">times</h4>

    times

Shows the user and system time used by the shell and its child processes.
                
### Child Process

<h4 id="jobs">jobs</h4>

    jobs

Shows all jobs running in the shell and their status.

<h4 id="wait">wait</h4>

    wait FLAG* ARG

Waits for a a process to exit, and returns its status.

The ARG can be a PID (tracked by the kernel), or a job number (tracked by the
shell).  Specify jobs with the syntax `%jobnumber`.

If there's no ARG, wait for all child processes.

Flags:

    -n  Wait for the next process to exit, rather than a specific process.

<h4 id="fg">fg</h4>

    fg JOB?

Returns a job running in the background to the foreground.  If no JOB is
specified, use the latest job.

<!--<h4 id="bg">bg</h4>

The bg builtin resumes suspend job, while keeping it in the background.

bg JOB?

JOB:
  Job ID to be resumed in the background. If none is specified, the latest job
  is chosen. -->

### External

<h4 id="test">test</h4>

    test OP ARG
    test ARG OP ARG
    [ OP ARG ]      # [ is an alias for test that requires closing ]
    [ ARG OP ARG ]

Evaluates a conditional expression and returns 0 (true) or 1 (false).

Note that [ is the name of a builtin, not an operator in the language.  Use
'test' to avoid this confusion.

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

#### printf

    printf FLAG* FMT ARGS*

Displays text according to a format string.

Flags:
    -v VAR  Write output in variable VAR instead of standard output.

FMT:
    String that can contain three types of objects: characters that will be
    printed; escape sequences that are interpreted and printed (see `escapes`);
    and format specifiers that print the strings passed to printf as ARGS after
    being formatted (if not enough ARGS are passed, zero or a nul string will
    be used).

Format specifiers:

    %%  Prints a single "%".
    %b  Interprets backslash escapes while printing.
    %q  Prints the argument escaping the characters needed to make it reusable
        as shell input.
    %d  Print as signed decimal number.
    %i  Same as %d.
    %o  Print as unsigned octal number.
    %u  Print as unsigned decimal number.
    %x  Print as unsigned hexadecimal numbe with lower-case hex-digits (a-f).
    %X  Same as %x, but with upper-case hex-digits (A-F).
    %f  Print as floating point number.
    %e  Print as a double number, in "±e" format (lower-case e).
    %E  Same as %e, but with an upper-case E.
    %g  Interprets the argument as double, but prints it like %f or %e.
    %G  Same as %g, but print it like %E.
    %c  Print as a single char, onlye the first character is printed.
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

#### getopts

    getopts SPEC VAR ARG*

Parses the options passed to the script. The character corresponding to the
detected option is stored in VAR. By default, it parses the options passed
to the shell ($1, $2...) unless an alternative options string ARG is passed.

Spec:

    SPEC contains the characters to be parsed as options. Eg, the string "abc"
    will parse the options -a, -b and -c. If the options needs an additional
    argument, a colon must be added after the character. Eg, the string "ab:c"
    will parse arguments for -a, -b arg, and -c.

    Arguments must be separated from options with spaces. ":" and "?" can't be
    used as options.

How to use:

    getopts returns success if an option is found, and fails if the end of
    options or an error is found. Every time it is run, it stores the character
    corresponding to the detected option in VAR, and also places the index of
    the next option in the variable `$OPTIND` (which is initialized to 1 every
    time a shell starts). If an option requires an argument, the argument is
    placed in the variable `$OPTARG`. This design is expected to be used in a
    loop with a case statement, like this:

    while getopts "ab:c" options; do
        case $options in
            a)
                echo "-a option passed"
                ;;
            b)
                echo "-b option passed with $OPTARG argument"
                ;;
            c)
                echo "-c option passed"
                ;;
            *)
                echo "Option $OPTARG: Unknown or argument missing"
                ;;
        esac
    done

    When an invalid option is found or a required argument is not found, VAR
    is set to '?' and `$OPTARG` is unset.

<h4 id="kill">kill</h4>

TODO

<!-- bash accepts job control syntax -->

<h4 id="enable">enable</h4>

Bash has this, but OSH won't implement it.

<h3>Introspection</h3>

<h4 id="help">help</h4>

    help oil             # list Oil language help topics
    help osh             # list OSH language help topics

    help TOPIC           # show help on a given topic

    help osh-usage       # same as osh --help
    help oil-usage       # same as oil --help

View on the web:

    https://www.oilshell.org/release/$VERSION/doc/

#### hash

    hash FLAG* NAME*

Avoids searching for the location of commands by keeping a hash cache
containing the path of previously executed commands.

Name:

    Name of the command whose path should be remembered, so they need not to be
    searched for subsequent invocations. `$PATH` is used for the search, and
    previously remembered paths are discarded. If no NAME and FLAG is supplied,
    it prints the current hash cache.

Flag:

    -r       Discard all remembered locations.
<!--    -d       Discard the remembered location of each NAME.
    -l       Display output in a format reusable as input.
    -p PATH  Inhibit path search, PATH is used as location for NAME.
    -t       Print the full path of one or more NAME.-->

#### type

    type FLAG* CMD

Prints information about the type of command that will be run as CMD:
an executable file, aliase, shell builtin, or function.

Flags:

    -f  Don't search for CMD in functions.
    -P  Force searching for CMD only in file executables.
    -t  Only print the type of command of CMD: 'alias', 'keyword', 'function',
        'builtin' or 'file'.
<!--    -a  Print all executables that can run CMD, including files, aliases,
        builtins and functions. If used with -p, only the executable file will
        be printed.-->
 
<h3>Word Lookup</h3>

### Interactive

### Oil Builtins

#### repr

Displays the internal representation of a cell.  (Cells are locations for
values like strings and arrays.)

<h2 id="option">Shell Options</h2>

### Errors

### Globbing

#### nullglob

Normally, when no files match  a glob, the glob itself is returned:

    $ echo L *.py R  # no Python files in this dir
    L *.py R

With nullglob on, the glob expands to no arguments:

    shopt -s nullglob
    $ echo L *.py R
    L R

(This option is in GNU bash as well.)

#### dashglob

Do globs return results that start with `-`?  It's on by default in `bin/osh`,
but off when Oil is enabled.

Turning it off prevents a command like `rm *` from being confused by a file
called `-rf`.

    $ touch -- myfile -rf

    $ echo *
    -rf myfile

    $ shopt -u dashglob
    $ echo *
    myfile

### Debugging

### Interactive

### Other Option

<h2 id="env">Environment Variables</h2>

### Shell Options

<!-- CONFLICT: Duplicates the above -->

<h4 id="SHELLOPTS">SHELLOPTS</h4>

For the 'set' builtin.

<h4 id="BASHOPTS">BASHOPTS</h4>

For the 'shopt' builtin.

<h3>Other Env</h3>

<h4 id="HOME">HOME</h4>

$HOME is used for:

1. ~ expansion 
2. ~ abbreviation in the UI (the dirs builtin, \W in $PS1).

Note: The shell doesn't set $HOME.  According to POSIX, the program that
invokes the login shell sets it based on /etc/passwd.

<h4 id="PATH">PATH</h4>

A colon-separated string that's used to find executables to run.

<h4 id="IFS">IFS</h4>

Used for word splitting.  And the builtin split() function.

<h3>Oil Paths</h3>

<h2 id="special">Special Variables</h2>

### Special

### POSIX Special

### Other Special

### Oil Special

### Platform

### Call Stack

### Tracing

### Process State

### Process Stack

### Shell State

<h3>Completion</h3>

<h4 id="COMP_WORDS">COMP_WORDS</h4>

An array of words, split by : and = for compatibility with bash.  New
completion scripts should use COMP_ARGV instead.

<h4 id="COMP_CWORD">COMP_CWORD</h4>

Discouraged; for compatibility with bash.

<h4 id="COMP_LINE">COMP_LINE</h4>

Discouraged; for compatibility with bash.

<h4 id="COMP_POINT">COMP_POINT</h4>

Discouraged; for compatibility with bash.

<h4 id="COMPREPLY">COMPREPLY</h4>

User-defined completion functions should Fill this array with candidates.  It
is cleared on every completion request.

<h4 id="COMP_ARGV">COMP_ARGV</h4>

An array of partial command arguments to complete.  Preferred over COMP_WORDS.
The compadjust builtin uses this variable.

(An OSH extension to bash.)

<h3>Functions</h3>


### Other Special

<h2 id="plugin">Plugins and Hooks</h2>

### Signals

### Traps

<h3>Words</h3>

<h4 id="PS1">PS1</h4>

First line of a prompt.

<h4 id="PS2">PS2</h4>

Second line of a prompt.

<h4 id="PS3">PS3</h4>

For the 'select' builtin (unimplemented).

<h4 id="PS4">PS4</h4>

For 'set -o xtrace'.  The leading character is special.

<h3>Completion</h3>

### Other Plugin

