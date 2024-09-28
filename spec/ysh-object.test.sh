## our_shell: ysh
## oils_failures_allowed: 2

#### Object() creates prototype chain

func Rect_area(this) {
  return (this.x * this.y)
}

var Rect = Object(null, {area: Rect_area})

var rect1 = Object(Rect, {x: 3, y: 4})
var rect2 = Object(Rect, {x: 10, y: 20})

# This could change to show the object?
# pp test_ (rect)

# TODO: This should be a bound function
#pp asdl_ (rect)
#pp (rect.area)
#pp (rect->area)

var area1 = rect1.area()
var area2 = rect2.area()

pp test_ ([rect1.x, rect1.y])
echo "area1 = $area1"

pp test_ ([rect2.x, rect2.y])
echo "area2 = $area2"

#pp test_ (rect1.nonexistent)

## STDOUT:
(List)   [3,4]
area1 = 12
(List)   [10,20]
area2 = 200
## END

#### prototype()

func Rect_area(this) {
  return (this.x * this.y)
}

var Rect = Object(null, {area: Rect_area})

var obj = Object(Rect, {x: 3, y: 4})

pp test_ (prototype(Rect))
pp test_ (prototype(obj))

## STDOUT:
(Null)   null
(Obj)   {"area":<Func>}
## END

#### propView() 

var obj = Object(null, {x: 3, y: 4})
var props = propView(obj)

pp test_ (props)

# object can be mutated
setvar props.x = 99

pp test_ (props)

var e = propView(null)  # error

## status: 3
## STDOUT:
(Dict)   {"x":3,"y":4}
(Dict)   {"x":99,"y":4}
## END

#### Mutating method lookup with ->

func inc(self, n) {
  setvar self.i += n
}
var Counter_methods = Object(null, {'M/inc': inc})

var c = Object(Counter_methods, {i: 5})

echo $[c.i]
call c->inc(3)
echo $[c.i]

## STDOUT:
5
8
## END

#### Mutating method must be up the prototype chain, not on the object

func inc(self, n) {
  setvar self.i += n
}
var c = Object(null, {'M/inc': inc, i: 0})

call c->inc(3)

## status: 3
## STDOUT:
## END


#### Copy to Dict with dict(), and mutate

var rect = Object(null, {x: 3, y: 4})
var d = dict(rect)

pp test_ (rect)
pp test_ (d)

# Right now, object attributes aren't mutable!  Could change this.
#
setvar rect.x = 99
setvar d.x = 100

pp test_ (rect)
pp test_ (d)
## STDOUT:
(Obj)   {"x":3,"y":4}
(Dict)   {"x":3,"y":4}
(Obj)   {"x":99,"y":4}
(Dict)   {"x":100,"y":4}
## END

#### setvar obj.attr = and += and ...

var rect = Object(null, {x: 3, y: 4})
pp test_ (rect)

setvar rect.y = 99
pp test_ (rect)

setvar rect.y += 3
pp test_ (rect)

setvar rect.x *= 5
pp test_ (rect)

## STDOUT:
(Obj)   {"x":3,"y":4}
(Obj)   {"x":3,"y":99}
(Obj)   {"x":3,"y":102}
(Obj)   {"x":15,"y":102}
## END

#### can't encode objects as JSON

var Rect = Object(null, {})

json write (Rect)
echo 'nope'

## status: 1
## STDOUT:
## END

#### pretty printing of cycles

var d = {k: 42}
setvar d.cycle = d

pp test_ (d)

var o = Object(null, d)

pp test_ (o)

var o2 = Object(o, {z: 99})

pp test_ (o2)

## STDOUT:
## END

#### Can all builtin methods with s.upper()

var s = 'foo'
var x = s.upper()
var y = "--$[x.lower()]"

pp test_ (x)
pp test_ (y)

## STDOUT:
(Str)   "FOO"
(Str)   "--foo"
## END

#### Bound Proc?

proc p (word1, word2; self, int1, int2) {
  echo "sum = $[self.x + self.y]"
  pp test_ (self)
  pp test_ ([word1, word2, int1, int2])
}

p a b ({x: 5, y: 6}, 42, 43)

var methods = Object(null, {__invoke__: p})

var callable = Object(methods, {x: 98, y: 99})

# TODO: change this error message
callable a b (42, 43)

## STDOUT:
## END
