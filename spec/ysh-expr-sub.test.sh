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
