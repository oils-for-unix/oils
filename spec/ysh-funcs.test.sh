# spec/ysh-funcs

## our_shell: ysh
## oils_failures_allowed: 3

#### Identity function
func id(x) {
  return (x)
}

json write (id("ysh"))

## STDOUT:
"ysh"
## END

#### Too many args
func f(x) { return (x + 1) }

= f(0, 1)
## status: 3
## STDOUT:
## END

#### Too few args
func f(x) { return (x + 1) }

= f()
## status: 3
## STDOUT:
## END

#### named args
func f(; x=3) {
  echo x=$x
}

_ f()

_ f(x=4)

## STDOUT:
## END

#### named args with ...
func f(; x=3, ...named) {
  echo x=$x
  json write (named)
}

_ f()

_ f(x=4)

_ f(x=4, y=5)

## STDOUT:
## END

#### Proc-style return in a func
func t() { return 0 }

= t()
## status: 2
## STDOUT:
## END

#### Typed return in a proc
proc t() { return (0) }

= t()
## status: 2
## STDOUT:
## END

#### Redefining functions is not allowed (with shopt -u redefine_proc_func)
shopt -u redefine_proc_func
func f() { return (0) }
func f() { return (1) }
## status: 1
## STDOUT:
## END

#### Redefining functions is allowed (with shopt -s redefine_proc_func)
shopt -s redefine_proc_func
func f() { return (0) }
func f() { return (1) }
## status: 0
## STDOUT:
## END

#### Functions cannot redefine readonly vars (even with shopt -s redefine_proc_func)
shopt -s redefine_proc_func
const f = 0
func f() { return (1) }
## status: 1
## STDOUT:
## END

#### Functions can redefine non-readonly vars
var f = 0
func f() { return (1) }
## status: 0
## STDOUT:
## END

#### Vars cannot redefine functions (even with shopt -s redefine_proc_func)
shopt -s redefine_proc_func
func f() { return (1) }
const f = 0
## status: 1
## STDOUT:
## END

#### Functions do not lift their inner definitions out of scope
func f() {
  func g() { return (1) }
  echo "g()=$[g()]"
}

echo "g()=$[g()]"  # Undefined variable 'g'
## status: 1
## STDOUT:
## END

#### Calling functions still does not lift their inner definitions out of scope
func f() {
  func g() { return (1) }
  echo "g()=$[g()]"
}

# If we set scope_e.GlobalOnly, then this would define g so that is may be used below
_ f()

echo "g()=$[g()]"  # Undefined variable 'g'
## status: 1
## STDOUT:
g()=1
## END

#### Multiple func calls

func inc(x) {
  # increment

  return (x + 1)
}

func dec(x) {
  # decrement

  return (x - 1)
}

echo $[inc(1)]
echo $[inc(inc(1))]
echo $[dec(inc(inc(1)))]

var y = dec(dec(1))
echo $[dec(y)]

## STDOUT:
2
3
2
-2
## END

#### Undefined var in function

func g(x) {
  var z = y  # make sure dynamic scope is off
  return (x + z) 
}

func f() {
  var y = 42  # if dynamic scope were on, g() would see this
  return (g(0))
}

echo $[f()]

## status: 1
## STDOUT:
## END

#### Param binding semantics
# value
var x = 'foo'

func f(x) {
  setvar x = 'bar'
}

= x
= f(x)
= x

# reference
var y = ['a', 'b', 'c']

func g(y) {
  setvar y[0] = 'z'
}

= y
= g(y)
= y
## STDOUT:
(Str)   'foo'
(NoneType)   None
(Str)   'foo'
(List)   ['a', 'b', 'c']
(NoneType)   None
(List)   ['z', 'b', 'c']
## END

#### Recursive functions
func fib(n) {
  # TODO: add assert n > 0
  if (n < 2) {
    return (n)
  }

  return (fib(n - 1) + fib(n - 2))
}

json write (fib(10))
## STDOUT:
55
## END

#### Recursive functions with LRU Cache
source --builtin list.ysh

var cache = []
var maxSize = 4

func remove(l, i) {
  for i in (i .. len(l) - 1) {
    setvar l[i] = l[i + 1]
  }

  _ l->pop() # remove duplicate last element
}

func fib(n) {
  var i = len(cache) - 1
  var j = 0;
  while (i >= 0) {
    var item = cache[i]

    if (item[0] === n) {
      _ remove(cache, i)
      _ cache->append(item)

      echo hit: $n
      return (item[1])
    }

    setvar i = i - 1
    setvar j += 1
  }

  var result = 0
  if (n < 2) {
    setvar result = n
  } else {
    setvar result = fib(n - 1) + fib(n - 2)
  }

  if (len(cache) >= maxSize) {
    _ remove(cache, 0)
  }
  _ cache->append([n, result])

  return (result)
}

json write (fib(10))
#json write --pretty=F (cache)
json write (cache)

## STDOUT:
hit: 1
hit: 2
hit: 3
hit: 4
hit: 5
hit: 6
hit: 7
hit: 8
55
[
  [
    7,
    13
  ],
  [
    9,
    34
  ],
  [
    8,
    21
  ],
  [
    10,
    55
  ]
]
## END

#### Varadic arguments, no other args
func f(...args) {
  = args
}

_ f()
_ f(1)
_ f(1, 2)
_ f(1, 2, 3)
## STDOUT:
(List)   []
(List)   [1]
(List)   [1, 2]
(List)   [1, 2, 3]
## END

#### Varadic arguments, other args
func f(a, b, ...args) {
  = [a, b, args]
}

_ f(1, 2)
_ f(1, 2, 3)
_ f(1, 2, 3, 4)
## STDOUT:
(List)   [1, 2, []]
(List)   [1, 2, [3]]
(List)   [1, 2, [3, 4]]
## END

#### Varadic arguments, too few args
func f(a, b, ...args) {
  = [a, b, args]
}

_ f(1)
## status: 3
## STDOUT:
## END

#### Userland max
func mymax (...args) {
  if (len(args) === 0) {
    error ('Requires 1 arg')
  } elif (len(args) === 1) {
    # TODO: assert List
    var mylist = args[0]
    var max = mylist[0]

    for item in (mylist) {
      if (item > max) {
        setvar max = item
      }
    }

    return (max)
  } elif (len(args) === 2) {
    if (args[0] >= args[1]) {
      return (args[0])
    } else {
      return (args[1])
    }
  } else {
    # max(1, 2, 3) doesn't work in YSH, but does in Python
    error ('too many')
  }
}

= mymax(5,6)  # => 6
= mymax([5,6,7])  # => 7
= mymax(5,6,7,8)  # error
## status: 1
## STDOUT:
(Int)   6
(Int)   7
## END

#### Functions share a namespace with variables
func f(x) {
  return (x * x)
}

var g = f
echo "g(2) -> $[g(2)]"
## STDOUT:
g(2) -> 4
## END

#### We can store funcs in dictionaries
func dog_speak() {
  echo "Woof"
}

func dog_type() {
  return ("DOG")
}

const Dog = {
  speak: dog_speak,
  type: dog_type,
}

func cat_speak() {
  echo "Meow"
}

func cat_type() {
  return ("CAT")
}

const Cat = {
  speak: cat_speak,
  type: cat_type,
}

# First class "modules"!
const animals = [Dog, Cat]
for animal in (animals) {
  var type = animal.type()
  echo This is a $type
  _ animal.speak()
}
## STDOUT:
This is a DOG
Woof
This is a CAT
Meow
## END

#### Functions cannot be nested
func build(y) {
  func f(x) {
    return (x)
  }
}
## status: 2
## STDOUT:
## END

#### Functions can be shadowed
func mysum(items) {
  var mysum = 0
  for x in (items) {
    setvar mysum += x
  }
  return (mysum)
}

echo 1 + 2 + 3 = $[mysum([1, 2, 3])]

func inAnotherScope() {
  # variable mysum has not yet shadowed func mysum in evaluation
  var mysum = mysum([1, 2, 3])
  echo mysum=$mysum
}
_ inAnotherScope()

# We need a scope otherwise we'd overwrite `mysum` in the global scope
var mysum = mysum([1, 2, 3])  # will raise status=1
## status: 1
## STDOUT:
1 + 2 + 3 = 6
mysum=6
## END

#### Function names cannot be redeclared
# Behaves like: const f = ...
func f(x) {
  return (x)
}

var f = "some val"
## status: 1
## STDOUT:
## END

#### Functions cannot be mutated
func f(x) {
  return (x)
}

setvar f = "some val"
## status: 1
## STDOUT:
## END
