## oils_failures_allowed: 3
## compare_shells: bash dash mksh

# Test numbers bigger than 255 (2^8 - 1) and bigger than 2^31 - 1
# Shells differ in their behavior here.  bash silently converts.

# I think we should implement the "unstrict" but deterministic bash behavior
# for compatibility, and then add shopt -s strict_status if we need it.

#### Truncating 'exit' status

$SH -c 'exit 255'
echo status=$?

$SH -c 'exit 256'
echo status=$?

$SH -c 'exit 257'
echo status=$?

echo ===

$SH -c 'exit -1'
echo status=$?

$SH -c 'exit -2'
echo status=$?

## STDOUT:
status=255
status=0
status=1
===
status=255
status=254
## END
## OK dash STDOUT:
status=255
status=0
status=1
===
status=2
status=2
## END

#### Truncating 'return' status
f() { return 255; }; f
echo status=$?

f() { return 256; }; f
echo status=$?

f() { return 257; }; f
echo status=$?

echo ===

f() { return -1; }; f
echo status=$?

f() { return -2; }; f
echo status=$?

## STDOUT:
status=255
status=0
status=1
===
status=255
status=254
## END

# dash aborts on bad exit code
## OK dash status: 2
## OK dash STDOUT:
status=255
status=256
status=257
===
## END


#### subshell OverflowError https://github.com/oilshell/oil/issues/996

# We have to capture stderr here 

filter_err() {
  # check for bash/dash/mksh messages, and unwanted Python OverflowError
  egrep -o 'Illegal number|bad number|return: can only|expected a small integer|OverflowError'
  return 0
}

# true; disables subshell optimization!

# exit status too big, but integer isn't
$SH -c 'true; ( return 2147483647; )' 2>err.txt
echo status=$?
cat err.txt | filter_err

# now integer is too big
$SH -c 'true; ( return 2147483648; )' 2> err.txt
echo status=$?
cat err.txt | filter_err

# even bigger
$SH -c 'true; ( return 2147483649; )' 2> err.txt
echo status=$?
cat err.txt | filter_err

## STDOUT:
## END

# osh-cpp checks overflow, but osh-py doesn't

## STDOUT:
status=255
status=1
expected a small integer
status=1
expected a small integer
## END

# dash uses '2' as its "bad status" status!

## OK dash STDOUT:
status=255
status=2
Illegal number
status=2
Illegal number
## END

# mksh uses '1' as its "bad status" status!

## OK mksh STDOUT:
status=255
status=1
bad number
status=1
bad number
## END

# bash disallows return
## OK bash STDOUT:
status=1
return: can only
status=1
return: can only
status=1
return: can only
## END


#### func subshell OverflowError https://github.com/oilshell/oil/issues/996

# We have to capture stderr here 

filter_err() {
  # check for bash/dash/mksh messages, and unwanted Python OverflowError
  egrep -o 'Illegal number|bad number|return: can only|expected a small integer|OverflowError'
  return 0
}

# exit status too big, but integer isn't
$SH -c 'f() ( return 2147483647; ); f' 2>err.txt
echo status=$?
cat err.txt | filter_err

# now integer is too big
$SH -c 'f() ( return 2147483648; ); f' 2> err.txt
echo status=$?
cat err.txt | filter_err

# even bigger
$SH -c 'f() ( return 2147483649; ); f' 2> err.txt
echo status=$?
cat err.txt | filter_err

## STDOUT:
status=255
status=1
expected a small integer
status=1
expected a small integer
## END

## OK dash STDOUT:
status=255
status=2
Illegal number
status=2
Illegal number
## END

# bash truncates it to 0 here, I guess it's using 64 bit integers
## OK bash STDOUT:
status=255
status=0
status=1
## END

## OK mksh STDOUT:
status=255
status=1
bad number
status=1
bad number
## END


# Weird case from bash-help mailing list.
#
# "Evaluations of backticks in if statements".  It doesn't relate to if
# statements but to $?, since && and || behave the same way.

# POSIX has a special rule for this.  In OSH strict_argv is preferred so it
# becomes a moot point.  I think this is an artifact of the
# "stateful"/imperative nature of $? -- it can be "left over" from a prior
# command, and sometimes the prior argv is [].  OSH has a more "functional"
# implementation so it doesn't have this weirdness.

#### If empty command
if ''; then echo TRUE; else echo FALSE; fi
## stdout: FALSE
## status: 0

#### If subshell true
if `true`; then echo TRUE; else echo FALSE; fi
## stdout: TRUE
## status: 0

#### If subshell true WITH OUTPUT is different
if `sh -c 'echo X; true'`; then echo TRUE; else echo FALSE; fi
## stdout: FALSE
## status: 0

#### If subshell true WITH ARGUMENT
if `true` X; then echo TRUE; else echo FALSE; fi
## stdout: FALSE
## status: 0

#### If subshell false -- exit code is propagated in a weird way (strict_argv prevents)
if `false`; then echo TRUE; else echo FALSE; fi
## stdout: FALSE
## status: 0
