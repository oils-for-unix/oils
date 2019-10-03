# Test Oil expressions within $[]

#### $[f(x)]
func f() {
  return 42
}
echo $[f()]
## STDOUT:
42
## END

#### $[obj.attr]
var obj = /d+/
set obj.x = 42
echo $[obj.x]
## STDOUT:
42
## END

#### $[d['key']]
var d = {}
set d['key'] = 42
echo $[d['key']]
## STDOUT:
42
## END

#### $[d->key]
var d = {}
set d['key'] = 42
echo $[d->key]
## STDOUT:
42
## END

#### In Double quotes
var d = {}
set d['key'] = 42
echo "key $[d->key]"
## STDOUT:
key 42
## END
