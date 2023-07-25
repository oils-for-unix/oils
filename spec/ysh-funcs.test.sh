# spec/ysh-funcs

## our_shell: ysh
## oils_failures_allowed: 0

#### Identity function
func identity(x) {
  return (x)
}

json write (identity("ysh"))

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

#### Redefining functions is not allowed
func f() { return (0) }
func f() { return (1) }
## status: 1
## STDOUT:
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
var cache = []
var maxSize = 4

func remove(l, i) {
  for i in (range(i, len(l) - 1)) {
    setvar l[i] = l[i + 1]
  }

  _ pop(l) # remove duplicate last element
}

func fib(n) {
  for rev_idx, item in (reversed(cache)) {
    if (item[0] === n) {
      const idx = len(cache) - rev_idx + 1
      _ remove(cache, idx)
      _ append(cache, item)

      echo hit: $[n]  # is this a side-effect?
      return (item[1])
    }
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
  _ append(cache, [n, result])

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
