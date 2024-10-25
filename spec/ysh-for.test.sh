## our_shell: ysh
## oils_failures_allowed: 0

#### For loop over expression: List
var mylist = [1, 2, 3]
for item in (mylist) {
  echo "item $item"
}

## STDOUT:
item 1
item 2
item 3
## END

#### For loop over expression: Dict, not BashAssoc

var mydict = {name: 'bob', age: 40}
for key in (mydict) {
  echo "key $key"
}

declare -A A=([name]=bob)
for key in (A) {
  echo "key $key"
}

## status: 3
## STDOUT:
key name
key age
## END


#### For loop over range
var myrange = 0 ..< 3
for i in (myrange) {
  echo "i $i"
}

## STDOUT:
i 0
i 1
i 2
## END

#### Shell for loop with index (equivalent of enumerate())
for i, item in a b c {
  echo "$i $item"
}
## STDOUT:
0 a
1 b
2 c
## END

#### 3 indices with (mylist) is a runtime error
for i, item bad in (['foo', 'bar']) {
  echo "$i $item $bad"
}
## status: 2

#### Shell for loop can't have 3 indices 
for i, bad, bad in a b c {
  echo $i $item
}
## status: 2

#### Any for loop can't have 4 indiecs
for a, b, c, d in (['foo']) {
  echo $i $item
}
## status: 2

#### Expression for loop with index: List
for i, item in (['spam', 'eggs']) {
  echo "$i $item"
}
## STDOUT:
0 spam
1 eggs
## END

#### Expression for loop with index: Dict (TODO: define dict iter order)
for key, value in ({name: 'bob', age: 40}) {
  echo "pair $key $value"
}
## STDOUT:
pair name bob
pair age 40
## END

#### Dict: index key value loop (TODO: define dict iter order)
for i, key, value in ({name: 'bob', age: 40}) {
  echo "entry $i $key $value"
}
## STDOUT:
entry 0 name bob
entry 1 age 40
## END


#### Equivalent of zip()

var array = :| d e f |

for i, item in a b c {
  echo "$i $item $[array[i]]"
}

## STDOUT:
0 a d
1 b e
2 c f
## END

#### parse_bare_word eliminates confusion

shopt --unset parse_bare_word

for x in mylist {  # THIS FAILS
  echo "BAD $x"
}

## status: 2
## STDOUT:
## END


#### Object that's not iterable

echo hi
for x in (42) {
  echo $x
}

## status: 3
## STDOUT:
hi
## END

#### YSH for with brace substitution and glob

touch {foo,bar}.py
for i, file in *.py {README,foo}.md {
  echo "$i $file"
}
## STDOUT:
0 bar.py
1 foo.py
2 README.md
3 foo.md
## END

#### for x in (io.stdin) { 

# to avoid stdin conflict

$SH $REPO_ROOT/spec/testdata/ysh-for-stdin.ysh

## STDOUT:
-1-
-2-
-3-

0 1
1 2
2 3

empty
done

empty2
done2

space
hi
## END

#### I/O error in for x in (stdin) { 

set +o errexit

# EISDIR - stdin descriptor is dir
$SH -c 'for x in (io.stdin) { echo $x }' < /
if test $? -ne 0; then
  echo pass
fi

## STDOUT:
pass
## END
