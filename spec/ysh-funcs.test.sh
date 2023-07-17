# spec/ysh-funcs

## our_shell: ysh
## oils_failures_allowed: 0

#### Identity function
func identity(x) {
  return (x)
}

= identity("ysh")
## STDOUT:
(Str)   'ysh'
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
