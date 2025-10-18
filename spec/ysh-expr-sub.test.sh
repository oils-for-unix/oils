## our_shell: ysh

# Test YSH expressions within $[]

#### $[f(x)]
var a = %(a b c)
echo $[len(a)]
## STDOUT:
3
## END

#### $[d['key']]
var d = {}
setvar d['key'] = 42
echo $[d['key']]
## STDOUT:
42
## END

#### $[d.key]
var d = {}
setvar d['key'] = 42
echo $[d.key]
## STDOUT:
42
## END

#### In Double quotes
var a = %(a b c)
var obj = /d+/
var d = {}
setvar d['key'] = 42
echo "func $[len(a)]"
echo "key $[d['key']]"
echo "key $[d.key]"
echo "dq $[d["key"]]"
## STDOUT:
func 3
key 42
key 42
dq 42
## END

#### @[expr splice]

var x = [1, 2, 3]

var y = @[x] ++ ['99']

#= y

# note: related bug in parsing [[ in test/ysh-parse-errors.sh
#assert [['1', '2', '3'] === y]

assert [ ['1', '2', '3', '99'] === y]

pp test_ (y)

pp test_ (@[[4, 5, 6]])

var bad = [42, []]
pp test_ (@[ bad ])  # cannot be stringified

## status: 3
## STDOUT:
(List)   ["1","2","3","99"]
(List)   ["4","5","6"]
## END
