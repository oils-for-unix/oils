---
in_progress: yes
---

Draft
=====

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

