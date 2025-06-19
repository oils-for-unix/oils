## compare_shells: bash-4.4 mksh
## oils_failures_allowed: 1

#### typeset -f prints function source code
: prefix; myfunc() { echo serialized; }

code=$(typeset -f myfunc)

$SH -c "$code; myfunc"

## STDOUT:
serialized
## END

#### typeset -f with function keyword (ksh style)
: prefix; function myfunc {
	echo serialized
}

code=$(typeset -f myfunc)

$SH -c "$code; myfunc"

## STDOUT:
serialized
## END

#### typeset -f prints function source code - nested functions
outer() {
  echo outer
  : prefix; inner() {
    echo inner
  }
}

code=$(typeset -f outer)

$SH -c "$code; outer; inner"

## STDOUT:
outer
inner
## END
