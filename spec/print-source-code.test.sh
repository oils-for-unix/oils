## compare_shells: bash-4.4 mksh
## oils_failures_allowed: 2

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

#### OSH doesn't print non { } function bodies (rare)

f() ( echo 'subshell body' )

code=$(typeset -f f)

#$SH -c "$code; f"

echo "$code"


## STDOUT:
f () 
{ 
    ( echo 'subshell body' )
}
## END

## OK mksh STDOUT:
f() ( echo "subshell body" ) 
## END
