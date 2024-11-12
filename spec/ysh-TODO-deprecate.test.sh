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

#### s.upper(), not s => upper() (might keep this)

echo $['foo' => upper()]

## STDOUT:
FOO
## END

#### fopen can be spelled redir 
shopt --set ysh:upgrade

fopen >out {
  echo 1
  echo 2
}

tac out

## STDOUT:
2
1
## END


#### Dict => keys()
var en2fr = {}
setvar en2fr["hello"] = "bonjour"
setvar en2fr["friend"] = "ami"
setvar en2fr["cat"] = "chat"
pp test_ (en2fr => keys())
## status: 0
## STDOUT:
(List)   ["hello","friend","cat"]
## END


#### Obj API
shopt --set ysh:upgrade

try {
  var obj = Object(null, {x: 4})
  pp test_ (obj)
}
echo $[_error.code]

try {
  pp test_ (propView(obj))
}
echo $[_error.code]

try {
  pp test_ (prototype(obj))
}
echo $[_error.code]

## STDOUT:
(Obj)   ("x":4)
0
(Dict)   {"x":4}
0
(Null)   null
0
## END
