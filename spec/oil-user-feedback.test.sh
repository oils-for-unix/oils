# Oil user feedback

# From Zulip:
#
# https://oilshell.zulipchat.com/#narrow/stream/121540-oil-discuss/topic/Experience.20using.20oil

#### setvar

# This seems to work as expected?

proc get_opt(arg, :out) {
  setvar out = $arg
}
var a = ''
get_opt a 'lol'
echo hi
## status: 1
## STDOUT:
## END

#### != operator
var a = 'bar'

# NOTE: a != foo is idiomatic)
if ($a != 'foo') {
  echo 'not equal'
}

if ($a != 'bar') {
  echo 'should not get here'
}

## STDOUT:
not equal
## END


#### Regex Literal

# This seems to work as expected?

proc get_opt(arg, :out) {
  setref out = $(write -- $arg | cut -d'=' -f2)
}

var variant = ''
var arg = '--variant=foo'
if ( arg ~ / '--variant=' <word> / ) {
  get_opt $arg :variant
  echo variant=$variant
}

## STDOUT:
variant=foo
## END
