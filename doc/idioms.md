---
in_progress: true
---

Oil Language Idioms
===================

This is an informal, lightly-organized list of recommended idioms for the [Oil
language]($xref:oil-language).  Use these when you don't care about
compatibility with other shells.

TODO: Go through more of the [Pure Bash
Bible](https://github.com/dylanaraps/pure-bash-bible).  Oil provides
alternatives for this quirky syntax.

<!-- cmark.py expands this -->
<div id="toc">
</div>

## Use Oil Expressions and Assignments

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

    (( i ++ ))  # interacts poorly with errexit
    i=$(( i+1 ))

Yes:

    setvar i += 1  # like Python, with a keyword

### Initialize and Assign Arrays

No:

    local -a myarray=(one two three)
    myarray[3]='THREE'

    local -A myassoc=(['key']=value ['k2']=v2)
    myassoc['key']=V

Yes:

    var myarray = %(one two three)
    setvar myarray[3] = 'THREE'

    var myassoc = %{key: 'value', k2: 'v2'}  # keys don't need to be quoted
    setvar myassoc['key'] = 'V'

Container literals start with the `%` sigil.  (TODO: Implement this.  It's `@`
right now.)

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
      echo positive
    fi

Yes:

    if (x > 0) {
      echo 'positive'
    }

## Use [Egg Expressions](eggex.html) instead of Regexes

### Test for a Match

No:

    pat='[[:digit:]]+'
    if [[ $x =~ $pat ]]; then
      echo 'number'
    fi

Yes:

    if (x ~ /digit+/) {
      echo 'number'
    }

Or extract the pattern:

    const pat = / digit+ / 
    if (x ~ pat) {
      echo 'number'
    }

### Extract Submatches

TODO: `BASH_REMATCH` alternative.

## Use Simple Word Evaluation

### Splicing Arrays

No:

    myflags=(--all --long)
    ls "${myflags[@]}" "$@" 

Yes:

    const myflags = %(--verbose -j)
    ls @myflags @ARGV

### Elision of Empty Elements

No:

    maybe_empty=''
    cp $maybe_empty other_file $dest  # omitted if empty

Yes:

    const e = ''
    cp @maybe(e) other_file $dest

### @split() and @glob()

TODO.

### Iterate a Number of Times (explicit splitting)

No:

    for x in $(seq 3); do  # No implicit splitting of unquoted words in Oil
      echo $x
    done

Yes:

    const n = 3
    for x in @(seq $n) {   # Explicit splitting
      echo $x
    }

Note that `{1..3}` works in bash and Oil, but the numbers must be constant.

## Use the `write` builtin instead of `printf` and `echo`

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

## Use Long Flags on the `read` builtin

### Read A Line

TODO: implement this.

No:

    read line     # Bad because it mangles your backslashes!
    read -r line  # Better, but easy to forget

Yes:

    read --line  # ???

### Read a Whole File

TODO: figure this out.

No:

    mapfile -d ''
    read -d ''

Yes:

    read --all
    slurp ?

## Use Blocks To Set and Restore Context

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

### Change Shell State

TODO: Implement this.

No:

    set +o errexit
    myfunc  # without error checking
    set -o errexit

Yes:

    shopt --unset errexit {
      myfunc
    }
