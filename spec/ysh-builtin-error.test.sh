#### try usage error

# Irony: we can't fail that hard here because errexit is disabled before
# we enable it.
# TODO: We could special case this perhaps

try
echo status=$?

try -z
echo status=$?

try --zoo
echo status=$?

# -- is allowed
try -- echo hi

## STDOUT:
status=2
status=2
status=2
hi
## END

#### try sets _status
myproc() {
  echo 'myproc'
  return 42
}

try myproc
echo dollar=$?
echo _status=$_status

( exit 9 )
echo dollar=$?
echo _status=$_status

## STDOUT:
myproc
dollar=0
_status=42
dollar=9
_status=42
## END


#### try with and without errexit
shopt --set parse_brace parse_proc

myproc() {
  echo before
  false
  echo after
}

try myproc
echo status=$_status

echo ---
try {
  echo 'block'
  myproc
}
echo status=$_status

echo ===
set -o errexit

try myproc
echo status=$_status

echo ---
try {
  echo 'block'
  myproc
}
echo status=$_status

## STDOUT:
before
status=1
---
block
before
status=1
===
before
status=1
---
block
before
status=1
## END

#### try takes a block
shopt --set parse_brace

myproc() {
  echo 'myproc'
  return 42
}

try {
  myproc
}
echo dollar=$?
echo _status=$_status

# It works the same with errexit
set -o errexit

try {
  myproc
}
echo dollar=$?
echo _status=$_status

## STDOUT:
myproc
dollar=0
_status=42
myproc
dollar=0
_status=42
## END

#### try with _pipeline_status and PIPESTATUS
shopt --set parse_brace parse_at
set -o errexit

try {
  ls /bad | wc -l
}
echo p @_pipeline_status
echo p ${PIPESTATUS[@]}
echo _status=$_status  # 0 because pipefail is off

echo ---
set -o pipefail
try {
  ls /bad | wc -l
}
echo p @_pipeline_status
echo p ${PIPESTATUS[@]}
echo _status=$_status  # changed to 2 because of pipefail

## STDOUT:
0
p 2 0
p 2 0
_status=0
---
0
p 2 0
p 2 0
_status=2
## END

#### try with _process_sub_status
shopt --set parse_brace parse_at
set -o errexit

touch right.txt

try {
  diff -q <(sort OOPS) <(sort right.txt)
}
echo p @_process_sub_status
echo _status=$_status

echo ---
shopt --set process_sub_fail
try {
  diff -q <(sort OOPS) <(sort right.txt)
}
echo p @_process_sub_status
echo _status=$_status  # changed to 2 because of process_sub_fail

## STDOUT:
p 2 0
_status=0
---
p 2 0
_status=2
## END

#### try error handling idioms
shopt --set parse_paren parse_brace parse_at

myproc() {
  return 42
}

try myproc
if (_status === 0) {
  echo 'OK'
}

try myproc
if (_status !== 0) {
  echo 'fail'
}

try {
  ls /nonexistent | wc -l
}
# make sure it's integer comparison
if (_pipeline_status[0] !== 0) {
  echo 'pipeline failed:' @_pipeline_status
}

try {
  diff <(sort XX) <(sort YY)
}
# make sure it's integer comparison
if (_process_sub_status[0] !== 0) {
  echo 'process sub failed:' @_process_sub_status
}

## STDOUT:
fail
0
pipeline failed: 2 0
process sub failed: 2 2
## END

#### try can handled failed var, setvar, etc.
shopt --set parse_brace parse_proc

try {
  echo hi
  var x = 1 / 0
  echo 'should not get here'
}
echo div $_status

try {
  var a = []
  setvar item = a[1]
  echo 'should not get here'
}
echo index $_status

try {
  var d = {}
  setvar item = d['mykey']
  echo 'should not get here'
}
echo key $_status

try {
  setvar item = d->mykey
  echo 'should not get here'
}
echo arrow $_status

## STDOUT:
hi
div 3
index 3
key 3
arrow 3
## END

# nothing on stderr because it's caught!

## STDERR:
## END

#### try can handled failed expr sub
shopt --set parse_brace parse_proc

try {
  echo hi

  var d = {}
  echo "result = $[d->BAD]"
  echo 'should not get here'
}
echo _status=$_status
## STDOUT:
hi
_status=3
## END
## STDERR:
## END

#### try with failed command sub within expression 
shopt --set parse_brace parse_proc

try {
  echo hi
  var x = $(exit 42)  # errexit
  echo bye
}
echo try $_status

# Note that there's no way to retrieve this status WITHOUT try
# var x = $(exit 42)  # errexit

## STDOUT:
hi
try 42
## END

#### try allows command sub (bug #1608)
shopt --set ysh:all

try {
  var x = $(echo hi)
}
echo $x

## STDOUT:
hi
## END

#### Uncaught expression error exits status 3
$SH -c '
shopt --set parse_proc

# errexit does not need to be!

var x = 42 / 0
echo inside=$?
'
echo outside=$?
## STDOUT:
outside=3
## END

#### boolstatus with external command

set -o errexit

echo hi > file.txt

if boolstatus grep pat file.txt; then
  echo 'match'
else 
  echo 'no match'
fi

# file doesn't exist
if boolstatus grep pat BAD; then
  echo 'match'
else 
  echo 'no match'
fi

echo DONE
## status: 2
## STDOUT:
no match
## END

#### boolstatus disallows procs with strict_errexit
set -o errexit
shopt -s strict_errexit

echo hi > file.txt

not-found() {
  echo not-found
  grep pat file.txt
  echo not-found
}

bad() {
  echo bad
  grep pat BAD  # exits with code 2
  echo bad
}

if boolstatus not-found; then
  echo 'match'
else 
  echo 'no match'
fi

if boolstatus bad; then
  echo 'match'
else 
  echo 'no match'
fi

## status: 1
## STDOUT:
## END

#### boolstatus can call a function without strict_errexit (not recommended)
set -o errexit

echo hi > file.txt

not-found() {
  echo not-found
  grep pat file.txt
  local status=$?
  if test "$status" -ne 0; then
    return $status
  fi
  echo not-found
}

bad() {
  echo bad
  grep pat BAD  # exits with code 2
  local status=$?
  if test "$status" -ne 0; then
    return $status
  fi
  echo bad
}

if boolstatus not-found; then
  echo 'match'
else 
  echo 'no match'
fi

if boolstatus bad; then
  echo 'match'
else 
  echo 'no match'
fi

## status: 2
## STDOUT:
not-found
no match
bad
## END

