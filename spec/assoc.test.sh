#!/usr/bin/env bash

# NOTE:
# -declare -A is required.
#
# Simply doing:
# a=([aa]=b [foo]=bar ['a+1']=c)
# gets utterly bizarre behavior.
#
# Associtative Arrays are COMPLETELY bash-specific.  mksh doesn't even come
# close.  So I will probably not implement them, or implement something
# slightly different, because the semantics are just wierd.

# http://www.gnu.org/software/bash/manual/html_node/Arrays.html
# TODO: Need a SETUP section.

#### Literal syntax ([x]=y)
declare -A a
a=([aa]=b [foo]=bar ['a+1']=c)
echo ${a["aa"]}
echo ${a["foo"]}
echo ${a["a+1"]}
## STDOUT:
b
bar
c
## END

#### set associative array to indexed array literal (very surprising bash behavior)
declare -A assoc=([k1]=foo [k2]='spam eggs')
for v in "${assoc[@]}"; do echo $v; done | sort
for v in "${!assoc[@]}"; do echo $v; done | sort

# disallow this in OSH?  Changing type?

assoc=(foo 'spam eggs')
argv.py "${assoc[@]}"
argv.py "${!assoc[@]}"

## STDOUT:
foo
spam eggs
k1
k2
['foo', 'spam eggs']
['0', '1']
## END
## BUG bash STDOUT:
foo
spam eggs
k1
k2
[]
[]
## END

#### Can't initialize assoc array with indexed array
declare -A A=(1 2 3)
echo status=$?
## STDOUT:
status=1
## END

# bash prints warnings to stderr but gives no indication of the problem
## BUG bash STDOUT:
status=0
## END


#### Initializing indexed array with assoc array
declare -a a=([xx]=1 [yy]=2 [zz]=3)
echo status=$?
argv.py "${a[@]}"
## STDOUT:
status=1
[]
## END
## BUG bash STDOUT:
status=0
['3']
## END

#### create empty assoc array, put, then get
declare -A A  # still undefined
argv.py "${A[@]}"
argv.py "${!A[@]}"
A['foo']=bar
echo ${A['foo']}
## STDOUT:
[]
[]
bar
## END

#### Empty value (doesn't use EmptyWord?)
declare -A A=(["k"]= )
argv.py "${A["k"]}"
## STDOUT:
['']
## END

#### retrieve keys with !
declare -A a
var='x'
a["$var"]=b
a['foo']=bar
a['a+1']=c
for key in "${!a[@]}"; do
  echo $key
done | sort
## STDOUT:
a+1
foo
x
## END

#### retrieve values with ${A[@]}
declare -A A
var='x'
A["$var"]=b
A['foo']=bar
A['a+1']=c
for val in "${A[@]}"; do
  echo $val
done | sort
## STDOUT:
b
bar
c
## END

#### coerce to string with ${A[*]}, etc.
declare -A A
A['X X']=xx
A['Y Y']=yy
argv.py "${A[*]}"
argv.py "${!A[*]}"

argv.py ${A[@]}
argv.py ${!A[@]}
## STDOUT:
['xx yy']
['X X Y Y']
['xx', 'yy']
['X', 'X', 'Y', 'Y']
## END

#### ${A[@]/b/B} 
# but ${!A[@]/b/B} doesn't work
declare -A A
A['aa']=bbb
A['bb']=ccc
A['cc']=ddd
for val in "${A[@]//b/B}"; do
  echo $val
done | sort
## STDOUT:
BBB
ccc
ddd
## END

#### ${A[@]#prefix}
declare -A A
A['aa']=one
A['bb']=two
A['cc']=three
for val in "${A[@]#t}"; do
  echo $val
done | sort
## STDOUT:
hree
one
wo
## END

#### ${assoc} disallowed in OSH, like ${assoc[0]} in bash
declare -A a
a=([aa]=b [foo]=bar ['a+1']=c)
echo "${a}"
## stdout-json: "\n"
## OK osh stdout-json: ""
## OK osh status: 1

#### length ${#a[@]}
declare -A a
a["x"]=1
a["y"]=2
a["z"]=3
echo "${#a[@]}"
## stdout: 3

#### lookup with ${a[0]} -- "0" is a string
declare -A a
a["0"]=a
a["1"]=b
a["2"]=c
echo 0 "${a[0]}" 1 "${a[1]}" 2 "${a[2]}"
## STDOUT:
0 a 1 b 2 c
## END

#### lookup with double quoted strings "mykey"
declare -A a
a["aa"]=b
a["foo"]=bar
a['a+1']=c
echo "${a["aa"]}" "${a["foo"]}" "${a["a+1"]}"
## STDOUT:
b bar c
## END

#### lookup with single quoted string
declare -A a
a["aa"]=b
a["foo"]=bar
a['a+1']=c
echo "${a['a+1']}"
## stdout: c

#### lookup with unquoted $key and quoted "$i$i"
declare -A A
A["aa"]=b
A["foo"]=bar

key=foo
echo ${A[$key]}
i=a
echo ${A["$i$i"]}   # note: ${A[$i$i]} doesn't work in OSH
## STDOUT:
bar
b
## END

#### lookup by unquoted string doesn't work in OSH because it's a variable
declare -A a
a["aa"]=b
a["foo"]=bar
a['a+1']=c
echo "${a[a+1]}"
## stdout-json: ""
## status: 1
## BUG bash stdout: c
## BUG bash status: 0

#### bash bug: "i+1" and i+1 are the same key

i=1
array=(5 6 7)
echo array[i]="${array[i]}"
echo array[i+1]="${array[i+1]}"

# arithmetic does NOT work here in bash.  These are unquoted strings!
declare -A assoc
assoc[i]=$i
assoc[i+1]=$i+1

assoc["i"]=string
assoc["i+1"]=string+1

echo assoc[i]="${assoc[i]}" 
echo assoc[i+1]="${assoc[i+1]}"

echo assoc[i]="${assoc["i"]}" 
echo assoc[i+1]="${assoc["i+1"]}"

## status: 1
## STDOUT:
array[i]=6
array[i+1]=7
## END
## BUG bash status: 0
## BUG bash STDOUT:
array[i]=6
array[i+1]=7
assoc[i]=string
assoc[i+1]=string+1
assoc[i]=string
assoc[i+1]=string+1
## END

#### Array stored in associative array gets converted to string (without strict_array)

array=('1 2' 3)
declare -A d
d['key']="${array[@]}"
argv.py "${d['key']}"
## stdout: ['1 2 3']

#### Indexed array as key of associative array coerces to string (without shopt -s strict_array)

declare -a array=(1 2 3)
declare -A assoc
assoc[42]=43
assoc["${array[@]}"]=foo

echo "${assoc["${array[@]}"]}"
for entry in "${!assoc[@]}"; do
  echo $entry
done | sort

## STDOUT:
foo
1 2 3
42
## END

#### Append to associative array value A['x']+='suffix'
declare -A A
A['x']='foo'
A['x']+='bar'
A['x']+='bar'
argv.py "${A["x"]}"
## STDOUT:
['foobarbar']
## END

#### Slice of associative array doesn't make sense in bash
declare -A a
a[xx]=1
a[yy]=2
a[zz]=3
a[aa]=4
a[bb]=5
#argv.py ${a["xx"]}
argv.py ${a[@]: 0: 3}
argv.py ${a[@]: 1: 3}
argv.py ${a[@]: 2: 3}
argv.py ${a[@]: 3: 3}
argv.py ${a[@]: 4: 3}
argv.py ${a[@]: 5: 3}
## stdout-json: ""
## status: 1
## BUG bash STDOUT:
['2', '1', '5']
['2', '1', '5']
['1', '5', '4']
['5', '4', '3']
['4', '3']
['3']
## END
## BUG bash status: 0

#### bash variable can have an associative array part and a string part

# and $assoc is equivalent to ${assoc[0]}, just like regular arrays
declare -A assoc
assoc[1]=1
assoc[2]=2
echo ${assoc[1]} ${assoc[2]} ${assoc}
assoc[0]=zero
echo ${assoc[1]} ${assoc[2]} ${assoc}
assoc=string
echo ${assoc[1]} ${assoc[2]} ${assoc}
## STDOUT:
1 2
1 2 zero
1 2 string
## END
## N-I osh stdout-json: ""
## N-I osh status: 1

#### Associative array expressions inside (( )) with keys that look like numbers
declare -A assoc
assoc[0]=42
(( var = ${assoc[0]} ))
echo $var
(( var = assoc[0] ))
echo $var
## STDOUT:
42
42
## END
## N-I osh status: 1
## N-I osh STDOUT:
42
## END

#### (( A[5] += 42 ))
declare -A A
(( A[5] = 10 ))
(( A[5] += 6 ))
echo ${A[5]}
## STDOUT:
16
## END

#### (( A[5] += 42 )) with empty cell
shopt -u strict_arith  # default zero cell
declare -A A
(( A[5] += 6 ))
echo ${A[5]}
## STDOUT:
6
## END

#### setting key to itself (from bash-bug mailing list)
declare -A foo
foo=(["key"]="value1")
echo ${foo["key"]}
foo=(["key"]="${foo["key"]} value2")
echo ${foo["key"]}
## STDOUT:
value1
value1 value2
## END
## BUG bash STDOUT:
value1
value2
## END

#### readonly associative array can't be modified
declare -Ar A
A['x']=1
echo status=$?
## OK osh status: 1
## OK osh stdout-json: ""
## STDOUT:
status=1
## END

#### associative array and brace expansion
declare -A A=([k1]=v [k2]=-{a,b}-)
echo ${A["k1"]}
echo ${A["k2"]}
## STDOUT:
v
-{a,b}-
## END

#### bash mangles array #1
a=([k1]=v1 [k2]=v2)
echo ${a["k1"]}
echo ${a["k2"]}
## STDOUT:
v1
v2
## END
## BUG bash STDOUT:
v2
v2
## END

#### bash mangles array and brace #2
a=([k2]=-{a,b}-)
echo ${a["k2"]}
## STDOUT:
-{a,b}-
## END
## BUG bash STDOUT:
[k2]=-a-
## END

