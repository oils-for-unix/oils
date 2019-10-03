# Test Oil expressions within ${}

#### ${f(x)}
func f() {
  return 42
}
echo ${f(x)}
## STDOUT:
42
## END

#### ${obj.attr}
var obj = /d+/
set obj.x = 42
echo ${obj.attr}
## STDOUT:
42
## END

#### ${d['key']}
var d = {}
set d['key'] = 42
echo ${d['key']}
## STDOUT:
42
## END

# NOTE: d->key is technically optional?  

#### ${d->key'}
var d = {}
set d['key'] = 42
echo $[d->key]
## STDOUT:
42
## END
