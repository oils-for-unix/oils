## compare_shells: bash-4.4 mksh zsh
## oils_failures_allowed: 0

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

if false; then
  echo ---
  echo $code
  echo ---
fi

$SH -c "$code; outer; inner"

## STDOUT:
outer
inner
## END

#### non-{ } function bodies can be serialized (rare)

# TODO: we can add more of these

f() ( echo 'subshell body' )

code=$(typeset -f f)

$SH -c "$code; f"

## STDOUT:
subshell body
## END
