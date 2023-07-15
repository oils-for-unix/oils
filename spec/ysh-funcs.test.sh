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
## status: 1
## STDOUT:
## END

#### Redefining functions is not allowed
func f() { return (0) }
func f() { return (1) }
## status: 1
## STDOUT:
## END
