## our_shell: osh
## oils_failures_allowed: 4

#### Shell Append += with YSH Int (issue #840)

var g = 2
echo g=$g

# What should happen here?

g+=1
echo g=$g

g+=1
echo g=$g

## STDOUT:
## END


#### Shell ${x:-default} with YSH List (issue #954)

var mylist = [1, 2, 3]

echo mylist ${mylist:-default}

var myint = 42

echo myint ${myint:-default}

## STDOUT:
## END


#### Shell ${a[0]} with YSH List (issue #1092)

var a = [1, 2, 3]
echo first ${a[0]}

## STDOUT:
## END


#### Cannot splice nested List

shopt --set parse_at

var mylist = ["ls", {name: 42}]

echo @mylist

## status: 3
## STDOUT:
## END

#### Splice nested Dict

declare -A A=([k]=v [k2]=v2)
echo ${A[@]}

var d ={name: [1, 2, 3]}
echo ${d[@]}

## STDOUT:
v v2
## END


#### Concatenate shell arrays and ${#a}

var a = :|a|
var b = :|b|

echo "len a ${#a[@]}"
echo "len b ${#b[@]}"

pp cell a

var c = a ++ b
pp cell c

echo len c ${#c[@]}

## STDOUT:
len a 1
len b 1
a = (Cell exported:F readonly:F nameref:F val:(value.MaybeStrArray strs:[a]))
c = (Cell exported:F readonly:F nameref:F val:(value.MaybeStrArray strs:[a b]))
len c 2
## END


#### List length

var L = [1,2,3]

echo List ${#L[@]}
echo List ${#L}
# Not supported.  TODO: could be a problem
#echo List ${#L[0]}

declare -a a=(abc d)

echo array ${#a[@]}
echo array ${#a}
echo array ${#a[0]}

## STDOUT:
List 3
List 3
array 2
array 3
array 3
## END
#
#### Dict length

var d = {k: 'v', '0': 'abc'}

echo Dict ${#d[@]}
echo Dict ${#d}
# Not supported.  TODO: could be a problem
#echo Dict ${#d[0]}

declare -A d=([k]=v [0]=abc)

echo Assoc ${#d[@]}
echo Assoc ${#d}
echo Assoc ${#d[0]}

## STDOUT:
Dict 2
Dict 2
Assoc 2
Assoc 3
Assoc 3
## END
