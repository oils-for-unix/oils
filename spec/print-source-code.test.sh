## compare_shells: bash-4.4 mksh
## oils_failures_allowed: 3

#### typeset -f prints function source code
myfunc() { echo serialized; }

code=$(typeset -f myfunc)

$SH -c "$code; myfunc"

## STDOUT:
serialized
## END

#### typeset -f with function keyword (ksh style)
function myfunc {
	echo serialized
}

code=$(typeset -f myfunc)

$SH -c "$code; myfunc"

## STDOUT:
serialized
## END

#### typeset -f prints function source code - nested functions
outer() {
  inner() {
    echo inner
  }
}

outer

code=$(typeset -f inner)

$SH -c "$code; inner"

## STDOUT:
inner
## END
