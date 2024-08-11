---
default_highlighter: oils-sh
---

YSH vs. Shell Idioms
====================

This is an informal, lightly-organized list of recommended idioms for the
[YSH]($xref) language.  Each section has snippets labeled *No* and *Yes*.

- Use the *Yes* style when you want to write in YSH, and don't care about
  compatibility with other shells.
- The *No* style is discouraged in new code, but YSH will run it.  The [OSH
  language]($xref:osh-language) is compatible with
  [POSIX]($xref:posix-shell-spec) and [bash]($xref).

[J8 Notation]: j8-notation.html

<!-- cmark.py expands this -->
<div id="toc">
</div>

## Use [Simple Word Evaluation](simple-word-eval.html) to Avoid "Quoting Hell"

### Substitute Variables

No:

    local x='my song.mp3'
    ls "$x"  # quotes required to avoid mangling

Yes:

    var x = 'my song.mp3'
    ls $x  # no quotes needed

### Splice Arrays

No:

    local myflags=( --all --long )
    ls "${myflags[@]}" "$@"

Yes:

    var myflags = :| --all --long |
    ls @myflags @ARGV

### Explicitly Split, Glob, and Omit Empty Args

YSH doesn't split arguments after variable expansion.

No:

    local packages='python-dev gawk'
    apt install $packages

Yes:

    var packages = 'python-dev gawk'
    apt install @[split(packages)]

Even better:

    var packages = :| python-dev gawk |  # array literal
    apt install @packages                # splice array

---

YSH doesn't glob after variable expansion.

No:

    local pat='*.py'
    echo $pat


Yes:

    var pat = '*.py'
    echo @[glob(pat)]   # explicit call

---

YSH doesn't omit unquoted words that evaluate to the empty string.

No:

    local e=''
    cp $e other $dest            # cp gets 2 args, not 3, in sh

Yes:

    var e = ''
    cp @[maybe(e)] other $dest   # explicit call

### Iterate a Number of Times (Split Command Sub)

No:

    local n=3
    for x in $(seq $n); do  # No implicit splitting of unquoted words in YSH
      echo $x
    done

OK:

    var n = 3
    for x in @(seq $n) {   # Explicit splitting
      echo $x
    }

Better;

    var n = 3
    for x in (1 .. n+1) {  # Range, avoids external program
      echo $x
    }

Note that `{1..3}` works in bash and YSH, but the numbers must be constant.

## Avoid Ad Hoc Parsing and Splitting

In other words, avoid *groveling through backslashes and spaces* in shell.  

Instead, emit and consume [J8 Notation]($xref:j8-notation):

- J8 strings are [JSON]($xref) strings, with an upgrade for byte string
  literals
- [JSON8]($xref) is [JSON]($xref), with this same upgrade
- [TSV8]($xref) is TSV with this upgrade (not yet implemented)

Custom parsing and serializing should be limited to "the edges" of your YSH
programs.

### More Strategies For Structured Data

- **Wrap** and Adapt External Tools.  Parse their output, and emit [J8 Notation][].
  - These can be one-off, "bespoke" wrappers in your program, or maintained
    programs.  Use the `proc` construct and `flagspec`!
  - Example: [uxy](https://github.com/sustrik/uxy) wrappers.
  - TODO: Examples written in YSH and in other languages.
- **Patch** Existing Tools.
   - Enhance GNU grep, etc. to emit [J8 Notation][].  Add a
     `--j8` flag.
- **Write Your Own** Structured Versions.
  - For example, you can write a structured subset of `ls` in Python with
    little effort.

<!--
  ls -q and -Q already exist, but --j8 or --tsv8 is probably fine
-->

## The `write` Builtin Is Simpler Than `printf` and `echo`

### Write an Arbitrary Line

No:

    printf '%s\n' "$mystr"

Yes:

    write -- $mystr

The `write` builtin accepts `--` so it doesn't confuse flags and args.

### Write Without a Newline

No:

    echo -n "$mystr"  # breaks if mystr is -e

Yes:

    write --end '' -- $mystr
    write -n -- $mystr  # -n is an alias for --end ''

### Write an Array of Lines

    var myarray = :| one two three |
    write -- @myarray

## New Long Flags on the `read` builtin

### Read a Line

No:

    read line          # Mangles your backslashes!

Better:

    read -r line       # Still messes with leading and trailing whitespace

    IFS= read -r line  # OK, but doesn't work in YSH

Yes:

    read --raw-line    # Gives you the line, without trailing \n

(Note that `read --raw-line` is still an unbuffered read, which means it slowly
reads a byte at a time.  We plan to add buffered reads as well.)

### Read a Whole File

No:

    read -d ''           # harder to read, easy to forget -r

Yes:

    read --all           # sets $_reply
    read --all (&myvar)  # sets $myvar

### Read Lines of a File

No:    

    # The IFS= idiom doesn't work in YSH, because of dynamic scope!
    while IFS= read -r line; do
      echo $line
    done

Yes:

    while read --raw-line {
      echo $_reply
    }
    # this reads a byte at a time, unbuffered, like shell

Yes:

    for line in (io.stdin) {
      echo $line
    }
    # this reads buffered lines, which is much faster

### Read a Number of Bytes

No:

    read -n 3            # slow because it respects -d delim
                         # also strips whitespace

Better:

    read -N 3            # good behavior, but easily confused with -n

Yes:

    read --num-bytes 3           # sets $_reply
    read --num-bytes 3 (&myvar)  # sets $myvar


### Read Until `\0` (consume `find -print0`)

No:

    # Obscure syntax that bash accepts, but not other shells
    read -r -d '' myvar

Yes:

    read -0 (&myvar)

## YSH Enhancements to Builtins

### Use `shopt` Instead of `set`

Using a single builtin for all options makes scripts easier to read:

Discouraged:

    set -o errexit  
    shopt -s dotglob

Idiomatic:

    shopt --set errexit
    shopt --set dotglob

(As always, `set` can be used when you care about compatibility with other
shells.)

### Use `:` When Mentioning Variable Names

YSH accepts this optional "pseudo-sigil" to make code more explicit.

No:

    read -0 record < file.bin
    echo $record

Yes:

    read -0 (&myvar) < file.bin
    echo $record


### Consider Using `--long-flags`

Easier to write:

    test -d /tmp
    test -d / && test -f /vmlinuz

    shopt -u extglob

Easier to read:

    test --dir /tmp
    test --dir / && test --file /vmlinuz

    shopt --unset extglob

## Use Blocks to Save and Restore Context

### Do Something In Another Directory

No:

    ( cd /tmp; echo $PWD )  # subshell is unnecessary (and limited)

No:

    pushd /tmp
    echo $PWD
    popd

Yes:

    cd /tmp {
      echo $PWD
    }

### Batch I/O

No:

    echo 1 > out.txt   
    echo 2 >> out.txt  # appending is less efficient
                       # because open() and close()

No:

    { echo 1
      echo 2
    } > out.txt

Yes:

    fopen > out.txt {
      echo 1
      echo 2
    }

The `fopen` builtin is syntactic sugar -- it lets you see redirects before the
code that uses them.

### Temporarily Set Shell Options

No:

    set +o errexit
    myfunc  # without error checking
    set -o errexit

Yes:

    shopt --unset errexit {
      myfunc
    }

### Use the `forkwait` builtin for Subshells, not `()`

No:

    ( cd /tmp; rm *.sh )

Yes:

    forkwait {
      cd /tmp
      rm *.sh
    }

Better:

    cd /tmp {  # no process created
      rm *.sh
    }

### Use the `fork` builtin for async, not `&`

No:

    myfunc &

    { sleep 1; echo one; sleep 2; } &

Yes:

    fork { myfunc }

    fork { sleep 1; echo one; sleep 2 }

## Use Procs (Better Shell Functions)

### Use Named Parameters Instead of `$1`, `$2`, ...

No:

    f() {
      local src=$1
      local dest=${2:-/tmp}

      cp "$src" "$dest"
    }

Yes:

    proc f(src, dest='/tmp') {   # Python-like default values
      cp $src $dest
    }

### Use Named Varargs Instead of `"$@"`

No:

    f() {
      local first=$1
      shift

      echo $first
      echo "$@"
    }

Yes:

    proc f(first, @rest) {  # @ means "the rest of the arguments"
      write -- $first
      write -- @rest        # @ means "splice this array"
    }

You can also use the implicit `ARGV` variable:

    proc p {
      cp -- @ARGV /tmp
    }

### Use "Out Params" instead of `declare -n`

Out params are one way to "return" values from a `proc`.

No:

    f() {
      local in=$1
      local -n out=$2

      out=PREFIX-$in
    }

    myvar='init'
    f zzz myvar         # assigns myvar to 'PREFIX-zzz'


Yes:

    proc f(in, :out) {  # : is an out param, i.e. a string "reference"
      setref out = "PREFIX-$in"
    }

    var myvar = 'init'
    f zzz :myvar        # assigns myvar to 'PREFIX-zzz'.
                        # colon is required

### Note: Procs Don't Mess With Their Callers

That is, [dynamic scope]($xref:dynamic-scope) is turned off when procs are
invoked.

Here's an example of shell functions reading variables in their caller:

    bar() {
      echo $foo_var  # looks up the stack
    }

    foo() {
      foo_var=x
      bar
    }

    foo

In YSH, you have to pass params explicitly:

    proc bar {
      echo $foo_var  # error, not defined
    }

Shell functions can also **mutate** variables in their caller!  But procs can't
do this, which makes code easier to reason about.

## Use Modules

YSH has a few lightweight features that make it easier to organize code into
files.  It doesn't have "namespaces".

### Relative Imports

Suppose we are running `bin/mytool`, and we want `BASE_DIR` to be the root of
the repository so we can do a relative import of `lib/foo.sh`.

No:

    # All of these are common idioms, with caveats
    BASE_DIR=$(dirname $0)/..

    BASE_DIR=$(dirname ${BASH_SOURCE[0]})/..

    BASE_DIR=$(cd $($dirname $0)/.. && pwd)

    BASE_DIR=$(dirname (dirname $(readlink -f $0)))

    source $BASE_DIR/lib/foo.sh

Yes:

    const BASE_DIR = "$this_dir/.."

    source $BASE_DIR/lib/foo.sh

    # Or simply:
    source $_this_dir/../lib/foo.sh

The value of `_this_dir` is the directory that contains the currently executing
file.

### Include Guards

No:

    # libfoo.sh
    if test -z "$__LIBFOO_SH"; then
      return
    fi
    __LIBFOO_SH=1

Yes:

    # libfoo.sh
    module libfoo.sh || return 0

### Taskfile Pattern

No:

    deploy() {
      echo ...
    }
    "$@"

Yes

    proc deploy() {
      echo ...
    }
    runproc @ARGV  # gives better error messages

## Error Handling

[YSH Fixes Shell's Error Handling (`errexit`)](error-handling.html) once and
for all!  Here's a comprehensive list of error handling idioms.

### Don't Use `&&` Outside of `if` / `while`

It's implicit because `errexit` is on in YSH.

No:

    mkdir /tmp/dest && cp foo /tmp/dest

Yes:

    mkdir /tmp/dest
    cp foo /tmp/dest

It also avoids the *Trailing `&&` Pitfall* mentioned at the end of the [error
handling](error-handling.html) doc.

### Ignore an Error

No:

    ls /bad || true  # OK because ls is external
    myfunc || true   # suffers from the "Disabled errexit Quirk"

Yes:

    try { ls /bad }
    try { myfunc }

### Retrieve A Command's Status When `errexit` is On

No:

    # set -e is enabled earlier

    set +e
    mycommand  # this ignores errors when mycommand is a function
    status=$?  # save it before it changes
    set -e

    echo $status

Yes:

    try {
      mycommand
    }
    echo $[_error.code]

### Does a Builtin Or External Command Succeed?

These idioms are OK in both shell and YSH:

    if ! cp foo /tmp {
      echo 'error copying'  # any non-zero status
    }

    if ! test -d /bin {
      echo 'not a directory'
    }

To be consistent with the idioms below, you can also write them like this:

    try {
      cp foo /tmp
    }
    if failed {  # shortcut for (_error.code !== 0)
      echo 'error copying'
    }

### Does a Function Succeed?

When the command is a shell function, you shouldn't use `if myfunc` directly.
This is because shell has the *Disabled `errexit` Quirk*, which is detected by
YSH `strict_errexit`.

**No**:

    if myfunc; then  # errors not checked in body of myfunc
      echo 'success'
    fi

**Yes**.  The *`$0` Dispatch Pattern* is a workaround that works in all shells.

    if $0 myfunc; then  # invoke a new shell
      echo 'success'
    fi

    "$@"  # Run the function $1 with args $2, $3, ...

**Yes**.  The YSH `try` builtin sets the special `_error` variable and returns
`0`.

    try {
      myfunc  # doesn't abort
    }
    if failed {
      echo 'success'
    }

### Does a Pipeline Succeed?

No:

    if ps | grep python; then
      echo 'found'
    fi

This is technically correct when `pipefail` is on, but it's impossible for
YSH `strict_errexit` to distinguish it from `if myfunc | grep python` ahead
of time (the ["meta" pitfall](error-handling.html#the-meta-pitfall)).  If you
know what you're doing, you can disable `strict_errexit`.

Yes:

    try {
      ps | grep python
    }
    if failed {
      echo 'found'
    }

    # You can also examine the status of each part of the pipeline
    if (_pipeline_status[0] !== 0) {
      echo 'ps failed'
    }

### Does a Command With Process Subs Succeed?

Similar to the pipeline example above:

No:

    if ! comm <(sort left.txt) <(sort right.txt); then
      echo 'error'
    fi

Yes:

    try {
      comm <(sort left.txt) <(sort right.txt)
    }
    if failed {
      echo 'error'
    }

    # You can also examine the status of each process sub
    if (_process_sub_status[0] !== 0) {
      echo 'first process sub failed'
    }

(I used `comm` in this example because it doesn't have a true / false / error
status like `diff`.)

### Handle Errors in YSH Expressions

    try {
      var x = 42 / 0
      echo "result is $[42 / 0]"
    }
    if failed {
      echo 'divide by zero'
    }

### Test Boolean Statuses, like `grep`, `diff`, `test`

The YSH `boolstatus` builtin distinguishes **error** from **false**.

**No**, this is subtly wrong.  `grep` has 3 different return values.

    if grep 'class' *.py {       
      echo 'found'               # status 0 means found
    } else {
      echo 'not found OR ERROR'  # any non-zero status
    }

**Yes**.  `boolstatus` aborts the program if `egrep` doesn't return 0 or 1.

    if boolstatus grep 'class' *.py {  # may abort
      echo 'found'               # status 0 means found
    } else {
      echo 'not found'           # status 1 means not found
    }

More flexible style:

    try {
      grep 'class' *.py
    }
    case (_error.code) {
      (0)    { echo 'found' }
      (1)    { echo 'not found' }
      (else) { echo 'fatal' }
    }

## Use YSH Expressions, Initializations, and Assignments (var, setvar)

### Initialize and Assign Strings and Integers

No:

    local mystr=foo
    mystr='new value'

    local myint=42  # still a string in shell

Yes:

    var mystr = 'foo'
    setvar mystr = 'new value'

    var myint = 42  # a real integer

### Expressions on Integers

No:

    x=$(( 1 + 2*3 ))
    (( x = 1 + 2*3 ))

Yes:

    setvar x = 1 + 2*3

### Mutate Integers

No:

    (( i++ ))  # interacts poorly with errexit
    i=$(( i+1 ))

Yes:

    setvar i += 1  # like Python, with a keyword

### Initialize and Assign Arrays

Arrays in YSH look like `:| my array |` and `['my', 'array']`.

No:

    local -a myarray=(one two three)
    myarray[3]='THREE'

Yes:

    var myarray = :| one two three |
    setvar myarray[3] = 'THREE'

    var same = ['one', 'two', 'three']
    var typed = [1, 2, true, false, null]


### Initialize and Assign Dicts

Dicts in YSH look like `{key: 'value'}`.

No:

    local -A myassoc=(['key']=value ['k2']=v2)
    myassoc['key']=V


Yes:

    # keys don't need to be quoted
    var myassoc = {key: 'value', k2: 'v2'}
    setvar myassoc['key'] = 'V'

### Get Values From Arrays and Dicts

No:

    local x=${a[i-1]}
    x=${a[i]}

    local y=${A['key']}

Yes:

    var x = a[i-1]
    setvar x = a[i]

    var y = A['key']

### Conditions and Comparisons

No:

    if (( x > 0 )); then
      echo 'positive'
    fi

Yes:

    if (x > 0) {
      echo 'positive'
    }

### Substituting Expressions in Words

No:

    echo flag=$((1 + a[i] * 3))  # C-like arithmetic

Yes:

    echo flag=$[1 + a[i] * 3]    # Arbitrary YSH expressions

    # Possible, but a local var might be more readable
    echo flag=$['1' if x else '0']


## Use [Egg Expressions](eggex.html) instead of Regexes

### Test for a Match

No:

    local pat='[[:digit:]]+'
    if [[ $x =~ $pat ]]; then
      echo 'number'
    fi

Yes:

    if (x ~ /digit+/) {
      echo 'number'
    }

Or extract the pattern:

    var pat = / digit+ /
    if (x ~ pat) {
      echo 'number'
    }

### Extract Submatches

No:

    if [[ $x =~ foo-([[:digit:]]+) ]] {
      echo "${BASH_REMATCH[1]}"  # first submatch
    }

Yes:

    if (x ~ / 'foo-' <capture d+> /) {   # <> is capture
      echo $[_group(1)]                  # first submatch
    }

## Glob Matching

No:

    if [[ $x == *.py ]]; then
      echo 'Python'
    fi

Yes:

    if (x ~~ '*.py') {
      echo 'Python'
    }


No:

    case $x in
      *.py)
        echo Python
        ;;
      *.sh)
        echo Shell
        ;;
    esac

Yes (purely a style preference):

    case $x {          # curly braces
      (*.py)           # balanced parens
        echo 'Python'
        ;;
      (*.sh)
        echo 'Shell'
        ;;
    }

## TODO

### Distinguish Between Variables and Functions

- `$RANDOM` vs. `random()`
- `LANG=C` vs.  `shopt --setattr LANG=C`

## Related Documents

- [Shell Language Idioms](shell-idioms.html).  This advice applies to shells
  other than YSH.
- [What Breaks When You Upgrade to YSH](upgrade-breakage.html).  Shell constructs that YSH
  users should avoid.
- [YSH Fixes Shell's Error Handling (`errexit`)](error-handling.html).  YSH fixes the
  flaky error handling in POSIX shell and bash.
- TODO: Go through more of the [Pure Bash
  Bible](https://github.com/dylanaraps/pure-bash-bible).  YSH provides
  alternatives for such quirky syntax.

