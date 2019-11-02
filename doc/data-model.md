---
in_progress: yes
---

Data Model for OSH and Oil
==========================

This doc internal data structure in the Oil interpreter, and gives examples of
how you manipulate them with shell or Oil code.

The interpreter is "unified".

- OSH semantics are based on:
  - POSIX shell for strings
  - bash and ksh for arrays and associative arrays.   bash largely follows ksh
    is the case of arrays.  Its associative arrays are quirkier.
- TODO: Python coercions.

<!--
TODO:

- New "Pulp"?
- Use fenced code blocks
  - and run through BOTH bash and osh
    - and link to this doc
  - bash 4.4 in a sandbox?

- Move "operations on arrays" to a legacy arrays doc?

-->


<div id="toc">
</div>


## Why Use this Information?

The goal of Oil is to replace this quirky language.  But we still made it
compatible.

If you want to write scripts compatible with OSH and bash.


## Oil's Data Model is Slightly Different Than Bash

It's meant to be more sane.

See [Known Differences](known-differences.html).

I salvaged these semantics.

Worst of the language!  Newest and most "grafted on".

### Surprising Parsing

Parsing bash is undecidable.

    A[x]
    a[x]

### Surprising Coercions

    Horrible

    a=('1 2' 3)
    b=(1 '2 3')  # two different elements

    [[ $a == $b ]]
    [[ ${a[0]} == ${b[0]} ]]

    [[ ${a[@]} == ${b[@]} ]]


Associative arrays and being undefined

- half an array type
  - strict_array removes this
  - case $x in "$@"
- half an associative array type

### Bugs

- test -v
- empty array conflicts with `set -o nounset` (in bash 4.3).  I can't recommend
  in good faith

## Memory


Shell has a stack but no heap.  It has values and locations, but no
references/pointers.

Oil adds references to data structures on the heap, which may be recurisve.


### Undef, Str, Sequential/Indexed Arrays, Associative Array

- "array" refers to both.
  - although Oil has a "homogeneous array type" that's entirely different
  - OSH array vs. Oil array
- no integers, but there is (( ))
- "$@" is an array, and "${a[@]}" too
  - not true in bash -- it's fuzzy there
  - but $@ and ${a[@]}  are NOT arrays
- flags: readonly and exported (but arrays/assoc arrays shouldn't be exported)
  - TODO: find that

### Arrays Can't Be Nested and Can't Escape Functions

- Big limitation!  Lifting it in Oil
- You have to splice
- There's no Garbage collection.

### OSH Doesn't have True Integers

We save those for Oil!

There are lots of coercions instead. 

bash has '-i' but that's true anyway.


## Operations on All Variables

### assignment

### unset

You can't unset an array in OSH?  But you can in bash.

### readonly

### export only applies to strings


## Operations on Arrays

### Initialization

    declare -a array 
    declare -a array=()

    declare -A assoc
    # there is no empty literal here

Also valid, but not necessary since `declare` is local:

    local -a array
    local -A assoc

Makes a global array:

    array=()

### Array Literals

Respects the normal rules of argv.

    prefix=foo
    myarray=(one two -{three,four}- {5..8} *.py "$prefix*.py" '$prefix*.py')

    myarray=(
      $var ${var} "$var" 
      $(echo hi) "$(echo hi)"
      $(1 + 2 * 3)
    )

### Associative Array Literals

    (['k']=v)

    Unlike bash, ([0]=v) is still an associative array literal.

    It's not an indexed array literal.  This matters when you take slices and
    so forth?


### "${a[@]}" is Evaluating (Splicing)

    echo "${array[@]}"
    echo "${assoc[@]}"

Not Allowed, unlike in bash!

    $assoc  ${assoc}  "${assoc}"
    ${!assoc}  ${assoc//pattern/replace}  # etc.


### Iteration

Note that since a for loop takes an array of words, evaluating/splicing works:

    for i in "${a1[@]}" "${a2[@]}"; do
      echo $i
    done

### ${#a[@]} is the Length


    echo ${#array[@]}
    echo ${#assoc[@]}


### Coercion to String by Joining Elements

    echo ${!array[@]}
    echo ${!assoc[@]}

    echo ${!array[*]}
    echo ${!assoc[*]}

    echo "${!array[*]}"
    echo "${!assoc[*]}"

### Look Up By Index / Key With a[]

  matrix:
    a['x'] a["x"]
    a["$x"]
    a[$x]
    a[${x}]
    a[${x#a}]

    a[x] -- allowed
    A[x] -- NOT allowed?  It should be a string

    (( 'a' )) -- parsed, but can't evaluate

    # This is a string in both cases
    a[0]
    A[0]


undef[0]=1 automatically creates an INDEXED array
undef=(1)

### Assign / Append To Location Specified by Index / Key

    a[expr]=    # int_coerce
    A[expr]=    # no integer coercion

Just like you can append to strings:

    s+='foo'

Append to elements of an array, which are strings:

    a[x+1]+=x
    a[x+1]+=$x

### Slicing With ${a[@]:5:2}

    ${array[@]:1:3}

Note the presence of DISALLOWED VALUES.


    # TODO: disallow this?  because no order
    ${assoc[@]:1:3}


NOTE: string slicing:



### Append Array to Array

    a=(1 2 3)
    a+=(4 5 6)


### Get All Indices With ${!a[@]}

    echo ${!array[@]}
    echo ${!assoc[@]}


### Vectorized String Operations

    echo ${array[@]//x/X}

    echo ${assoc[@]//x/X}


## Quirky Syntax and Semantics in Shell Sublanguages

### Command

Mentioned above: 

    a[x+1]+=x
    a[x+1]+=$x

    s+='foo'

### Word

Mentioned above:

    echo ${a[0]}
    echo "${a[0]}"
    echo ${a[i+1]}

### Arithmetic Does Integer Coercion

SURPRISING!  Avoid if you can!!!

    (( a[ x+1 ] += s ))  # 


### Boolean: [[ $a = $b ]]

Operates on strings only.  Can't compare

## Introspection

Oil supports various shell and bash operations to view the interpretr state.

- `set` prints variables and their values
- `set -o` prints options
- `declare/typeset/readonly/export -p` prints a subset of variables
- `test -v` tests if a variable is defined.

### repr (Oil only)

Pretty prints state.

## Future Work: The Oil Data Model

- Similar to Python and JavaScript
- Garbage Collection
- JSON serialization
- Typed Arrays and Data Frames

## Links

- <https://opensource.com/article/18/5/you-dont-know-bash-intro-bash-arrays>
- <https://www.thegeekstuff.com/2010/06/bash-array-tutorial>

