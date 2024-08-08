## our_shell: ysh

#### Object() creates prototype chain

func Rect_area(this) {
  return (this.x * this.y)
}

var Rect = {area: Rect_area}

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

echo "area1 = $area1"
echo "area2 = $area2"

## STDOUT:
area1 = 12
area2 = 200
## END
