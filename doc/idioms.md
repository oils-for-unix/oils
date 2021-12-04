---
default_highlighter: oil-sh
---

Oil vs. Shell Idioms
====================

This is an informal, lightly-organized list of recommended idioms for the [Oil
language]($xref:oil-language).  Each section has snippets labeled *No* and
*Yes*.

- Use the *Yes* style when you want to write in Oil, and don't care about
  compatibility with other shells.
- The *No* style is discouraged in new code, but Oil will run it.  The [OSH
  language]($xref:osh-language) is compatible with
  [POSIX]($xref:posix-shell-spec) and [bash]($xref).

[QSN]: qsn.html
[QTT]: qtt.html

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

    var myflags = %( --all --long )
    ls @myflags @ARGV

### Explicitly Split, Glob, and Omit Empty Args

Oil doesn't split arguments after variable expansion.

No:

    local packages='python-dev gawk'
    apt install $packages

Yes:

    var packages = 'python-dev gawk'
    apt install @split(packages)

Even better:

    var packages = %(python-dev gawk)  # array literal
    apt install @packages              # splice array

---

Oil doesn't glob after variable expansion.

No:

    local pat='*.py'
    echo $pat


Yes:

    var pat = '*.py'
    echo @glob(pat)   # explicit call

---

Oil doesn't omit unquoted words that evaluate to the empty string.

No:

    local e=''
    cp $e other $dest            # cp gets 2 args, not 3, in sh

Yes:

    var e = ''
    cp @maybe(e) other $dest     # explicit call

### Iterate a Number of Times (Split Command Sub)

No:

    local n=3
    for x in $(seq $n); do  # No implicit splitting of unquoted words in Oil
      echo $x
    done

Yes:

    var n = 3
    for x in @(seq $n) {   # Explicit splitting
      echo $x
    }

Note that `{1..3}` works in bash and Oil, but the numbers must be constant.


## Avoid Ad Hoc Parsing and Splitting

In other words, avoid *groveling through backslashes and spaces* in shell.  

Instead, emit and consume the [QSN][] and [QTT][] interchange formats.

- QSN is a JSON-like format for byte string literals
- QTT is a convention for embedding QSN in TSV files (not yet implemented)

Custom parsing and serializing should be limited to "the edges" of your Oil
programs.

### Use New Builtins That Support Structured I/O

These are discussed in the next two sections, but here's a summary.

    write --qsn        # also -q
    read --qsn :mystr  # also -q

    read --line --qsn :myline     # read a single line

That is, take advantage of the invariants that the [IO
builtins](io-builtins.html) respect.  (doc in progress)

<!--
    read --lines --qsn :myarray   # read many lines
-->

### More Strategies For Structured Data

- **Wrap** and Adapt External Tools.  Parse their output, and emit [QSN][] and
  [QTT][].
  - These can be one-off, "bespoke" wrappers in your program, or maintained
    programs.  Use the `proc` construct and `flagspec`!
  - Example: [uxy](https://github.com/sustrik/uxy) wrappers.
  - TODO: Examples written in Oil and in other languages.
- **Patch** Existing Tools.
   - Enhance GNU grep, etc. to emit [QSN][] and [QTT][].  Add a `--qsn` flag.
- **Write Your Own** Structured Versions.
  - For example, you can write a structured subset of `ls` in Python with
    little effort.

<!--

  ls -q and -Q already exist, but --qsn is probably fine
  or --qtt
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

    var myarray = %(one two three)
    write -- @myarray

## New Long Flags on the `read` builtin

### Read a Line

No:

    read line     # Bad because it mangles your backslashes!
    read -r line  # Better, but easy to forget

Yes:

    read --line   # also faster because it's a buffered read

### Read a Whole File

No:

    read -d ''      # harder to read, easy to forget -r

Yes:

    read --all :mystr

### Read Until `\0` (consume `find -print0`)

No:

    # Obscure syntax that bash accepts, but not other shells
    read -r -d '' myvar

Yes:

    read -0 :myvar

## Oil Enhancements to Builtins

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

Oil accepts this optional "pseudo-sigil" to make code more explicit.

No:

    read -0 record < file.bin
    echo $record

Yes:

    read -0 :record < file.bin
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

    ( not_mutated=foo )
    echo $not_mutated

Yes:

    var not_mutated = 'bar'
    forkwait {
      setvar not_mutated = 'foo'
    }
    echo $not_mutated

### Use the `fork` builtin for async, not `&`

No:

    myproc &

    { sleep 1; echo one; sleep 2; } &

Yes:

    fork { myproc }

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

In Oil, you have to pass params explicitly:

    proc bar {
      echo $foo_var  # error, not defined
    }

Shell functions can also **mutate** variables in their caller!  But procs can't
do this, which makes code easier to reason about.

## Use Modules

Oil has a few lightweight features that make it easier to organize code into
files.  It doesn't have "namespaces".

### Relative Imports

No:

    # All of these are common idioms, with caveats
    source $(dirname $0)/lib/foo.sh
    source $(dirname ${BASH_SOURCE[0]})/lib/foo.sh
    source $(cd $($dirname $0); pwd)/lib/foo.sh

Yes:

    source $_this_dir/lib/foo.sh

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

### If, shell functions, and `errexit`

This is a bug in POSIX shell, which Oil's `strict_errexit` warns you of:

    if myfunc; then  # oops, errors not checked in myfunc
      echo 'success'
    fi

The workaround is to use the *`$0` Dispatch Pattern*, which works in all
shells:

    if $0 myfunc; then  # invoke a new shell
      echo 'success'
    fi

    "$@"

Oil has a `try` builtin, which re-enables errexit without the extra process:

    if try myfunc; then
      echo 'success'
    fi

The explicit `try` avoids breaking existing shell programs.  You have to opt in
to the better behavior.

### Use the `try` Builtin With `!`, `||`, and `&&`

These constructs require an explicit `try`:

No:

    ! myfunc
    myfunc || fail
    myfunc && echo 'success'

Yes:

    ! try myfunc
    try myfunc || fail
    try myfunc && echo 'success'

Although `||` and `&&` are rare in idiomatic Oil code.

### Don't use `&&` Outside of `if` / `while`

It's implicit because `errexit` is on in Oil.

No:

    mkdir /tmp/dest && cp foo /tmp/dest

Yes:

    mkdir /tmp/dest
    cp foo /tmp/dest


## Use Oil Expressions, Initializations, and Assignments (var, setvar)

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

Container literals in Oil look like `%(one two)` and `%{key: 'value'}`.

No:

    local -a myarray=(one two three)
    myarray[3]='THREE'

Yes:

    var myarray = %(one two three)
    setvar myarray[3] = 'THREE'

No:

    local -A myassoc=(['key']=value ['k2']=v2)
    myassoc['key']=V


Yes:

    # keys don't need to be quoted
    var myassoc = %{key: 'value', k2: 'v2'}
    setvar myassoc['key'] = 'V'

### Expressions on Arrays

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

    echo flag=$[1 + a[i] * 3]    # Arbitrary Oil expressions

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

    if (x ~ / 'foo-' <d+> /) {   # <> is capture
      echo $_match(1)             # first submatch
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
  other than Oil.
- [Shell Language Deprecations](deprecations.html).  Shell constructs that Oil
  users should avoid.
- [Error Handling with `set -e` / `errexit`](errexit.html).  Oil fixes the
  flaky error handling in POSIX shell and bash.
- TODO: Go through more of the [Pure Bash
  Bible](https://github.com/dylanaraps/pure-bash-bible).  Oil provides
  alternatives for such quirky syntax.

