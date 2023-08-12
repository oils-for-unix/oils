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
