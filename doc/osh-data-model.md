OSH Data Model
--------------

- This is for the OSH language, as opposed to the Oil language.
- OSH semantics are based on:
  - POSIX shell for strings
  - bash and ksh for arrays and associative arrays.    bash largely follows ksh
    is the  case of arrays.  Its associative arrays are quickier.
  
  POSIX shell for strings
  exisbash.  For 

Python coercions.

TODO:

- Use fenced code blocks
- and then evaluate like Pulp
  - maybe borrow from Brett
- and run through BOTH bash and osh
  - and link to this doc

  - bash 4.3 maybe?  or 4.4

### Why Use this Information?

The goal of Oil is to replace this quirkl language!  But we still made it
compatible.

If you want to write scripts compatible with OSH and bash!

TODO: The Oil language not done yet!


### Preliminary: Why Differences from bash

I SALVAGED THESE SEMANTICS.

Worst of the language!  Newest and most "grafted on".


#### Surprising Parsing

Parsing bash is undecidable.

    A[x]
    a[x]

#### Surprising Coercions

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

#### Bugs

- test -v
- empty array and nounset, in bash 4.3.  I can't recommend in good faith



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

#### Arrays Can't Be Nested and Can't Escape Functions

Big limitation!  Lifting it in Oil

You have to splice

There's no Garbage collection.

#### There are no true integers

There are lots of coercions instead. 

bash has '-i' but that's true anyway.


### Operations on All Variables

#### assignment

#### unset

#### readonly

#### export only applies to strings


### Operations on Arrays

#### Initialization

    declare -a array 
    declare -a array=()

    declare -A assoc
    # there is no empty literal here

Also valid, but not necessary since `declare` is local:

    local -a array
    local -A assoc

Makes a global array:

    array=()

#### Array Literals

Respects the normal rules of argv.

    prefix=foo
    myarray=(one two -{three,four}- {5..8} *.py "$prefix*.py" '$prefix*.py')

    myarray=(
      $var ${var} "$var" 
      $(echo hi) "$(echo hi)"
      $(1 + 2 * 3)
    )

#### Associative Array Literals

    (['k']=v)

    Unlike bash, ([0]=v) is still an associative array literal.

    It's not an indexed array literal.  This matters when you take slices and
    so forth?


#### "${a[@]}" is Evaluating (Splicing)

    echo "${array[@]}"
    echo "${assoc[@]}"

NOT Allowed, unlike in bash!

    $assoc  ${assoc}  "${assoc}"
    ${!assoc}  ${assoc//pattern/replace}  # etc.


#### Iteration

Note that since a for loop takes an array of words, evaluating/splicing works:

    for i in "${a1[@]}" "${a2[@]}"; do
      echo $i
    done

#### ${#a[@]} is the Length


    echo ${#array[@]}
    echo ${#assoc[@]}



#### Coercion to String by Joining Elements

    echo ${!array[@]}
    echo ${!assoc[@]}

    echo ${!array[*]}
    echo ${!assoc[*]}

    echo "${!array[*]}"
    echo "${!assoc[*]}"

#### Look Up By Index / Key With a[]

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

#### Assign / Append To Location Specified by Index / Key

    a[expr]=    # int_coerce
    A[expr]=    # no integer coercion

Just like you can append to strings:

    s+='foo'

Append to elements of an array, which are strings:

    a[x+1]+=x
    a[x+1]+=$x

#### Slicing With ${a[@]:5:2}

    ${array[@]:1:3}

Note the presence of DISALLOWED VALUES.


    # TODO: disallow this?  because no order
    ${assoc[@]:1:3}


NOTE: string slicing:



#### Append Array to Array

    a=(1 2 3)
    a+=(4 5 6)


#### Get All Indices With ${!a[@]}

    echo ${!array[@]}
    echo ${!assoc[@]}


#### Vectorized String Operations

    echo ${array[@]//x/X}

    echo ${assoc[@]//x/X}


### Strict Options

    set -o nounset  # bash

    shopt -s strict_array
    shopt -s strict_arith  # on by default

    shopt -s strict_word_eval  # slice args, unicode strings


### Quirky Syntax and Semantics in Shell Sublanguages

#### Command

Mentioned above: 

    a[x+1]+=x
    a[x+1]+=$x

    s+='foo'

#### Word

Mentioned above:

    echo ${a[0]}
    echo "${a[0]}"
    echo ${a[i+1]}

#### Arithmetic Does Integer Coercion

SURPRISING!  Avoid if you can!!!

    (( a[ x+1 ] += s ))  # 


#### Boolean: [[ $a = $b ]]

Operates on strings only.  Can't compare

### Introspection

#### set

Prints all variables.  Strings only?

#### declare/typeset/readonly/export -p

Prints a subset.

#### test -v

Test if a variable is defined.

Don't use this because it's incopmatible?

#### repr (OSH-specific)

### Future Work: The Oil Data Model

- similar to Python and JavaScript
- garbage collection
- JSON serialization


### Links

- <https://opensource.com/article/18/5/you-dont-know-bash-intro-bash-arrays>
- <https://www.thegeekstuff.com/2010/06/bash-array-tutorial>


