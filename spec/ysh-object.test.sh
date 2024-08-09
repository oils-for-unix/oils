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

#### setvar obj.attr

func Rect_area(this) {
  return (this.x * this.y)
}

var Rect = Object(null, {area: Rect_area})

var rect1 = Object(Rect, {x: 3, y: 4})

pp test_ (rect1)

# Right now it's not mutable
setvar rect1.x = 99

pp test_ (rect1)

## STDOUT:
(Obj)   {"x":3,"y":4} ==> {"area":<Func>}
## END

#### Can all builtin methods with s.upper()

var s = 'foo'
var x = s.upper()
var y = "--$[x.lower()]"

pp test_ (x)
pp test_ (y)

# TODO:
# keys(d) values(d) instead of d.keys() and d.values()
#
# mutating methods are OK?
#   call d->inc(x)

## STDOUT:
(Str)   "FOO"
(Str)   "--foo"
## END
