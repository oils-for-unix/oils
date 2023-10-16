# spec/ysh-methods

## our_shell: ysh
## oils_failures_allowed: 0

#### Str->startswith
= "abc"->startswith("")
= "abc"->startswith("a")
= "abc"->startswith("z")
## status: 0
## STDOUT:
(Bool)   True
(Bool)   True
(Bool)   False
## END

#### Str->startswith, no args
= "abc"->startswith()
## status: 3

#### Str->startswith, too many args
= "abc"->startswith("extra", "arg")
## status: 3

#### Missing method (Str->doesNotExist())
= "abc"->doesNotExist()
## status: 3

#### Dict->keys()
var en2fr = {}
setvar en2fr["hello"] = "bonjour"
setvar en2fr["friend"] = "ami"
setvar en2fr["cat"] = "chat"
= en2fr->keys()
## status: 0
## STDOUT:
(List)   ['hello', 'friend', 'cat']
## END

#### Separation of -> attr and () calling
const check = "abc"->startswith
= check("a")
## status: 0
## STDOUT:
(Bool)   True
## END

#### Bound methods, receiver value/reference semantics
var is_a_ref = { "foo": "bar" }
const f = is_a_ref->keys
= f()
setvar is_a_ref["baz"] = 42
= f()

var is_a_val = "abc"
const g = is_a_val->startswith
= g("a")
setvar is_a_val = "xyz"
= g("a")
## status: 0
## STDOUT:
(List)   ['foo']
(List)   ['foo', 'baz']
(Bool)   True
(Bool)   True
## END

#### List->join
var items = [1, 2, 3]

json write (items->join())  # default separator is ''
json write (items->join(" "))  # explicit separator (can be any number or chars)
json write (items->join(", "))  #  separator can be any number of chars

try {
  json write (items->join(1))  # separator must be a string
}
echo "failed with status $_status"
## STDOUT:
"123"
"1 2 3"
"1, 2, 3"
failed with status 3
## END

#### List->reverse()

var empty = []

var a = [0]
var b = [2, 1, 3]
var c = :| hello world |

_ empty->reverse()
_ a->reverse()
_ b->reverse()
_ c->reverse()

json write --pretty=F (empty)
json write --pretty=F (a)
json write --pretty=F (b)
json write --pretty=F (c)

## STDOUT:
[]
[0]
[3,1,2]
["world","hello"]
## END
