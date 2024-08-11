# TODO-deprecate: Code we want to get rid of!


#### oil:upgrade as alias for ysh:upgrade

shopt -p | grep simple_word
shopt --set oil:upgrade
shopt -p | grep simple_word

shopt --unset ysh:upgrade
shopt -p | grep simple_word

## STDOUT:
shopt -u simple_word_eval
shopt -s simple_word_eval
shopt -u simple_word_eval
## END


#### %() array literal

shopt --set parse_at

var x = %(one two)
echo @x

## STDOUT:
one two
## END

#### _match() instead of _group()

shopt --set ysh:upgrade

if ('foo42' ~ / <capture d+> /) {
  echo $[_match(0)]
  echo $[_group(0)]
}

## STDOUT:
42
42
## END

#### _status instead of _error.code

shopt --set ysh:upgrade

f() {
  return 42
}

try {
  f
}
echo status=$_status

## STDOUT:
status=42
## END


#### source ///osh/two.sh rather than source --builtin osh/two.sh

source --builtin osh/two.sh
echo status=$?

## STDOUT:
status=0
## END

#### OILS_VERSION, not OIL_VERSION

if test -n "$OIL_VERSION"; then
  echo OIL
fi

## STDOUT:
OIL
## END


#### stdin is now io.stdin

seq 3 | for line in (io.stdin) {
  echo $line
}
## STDOUT:
1
2
3
## END


#### Old _io builtin

echo $[_io=>captureStdout(^(echo hi))]

## STDOUT:
hi
## END

#### s.upper(), not s => upper()

echo $['foo' => upper()]

## STDOUT:
FOO
## END


#### Mutating methods must be ->, not => or .

var mylist = []
call mylist=>append('foo')
call mylist.append('bar')

pp test_ (mylist)

## STDOUT:
(List)   ["foo","bar"]
## END

