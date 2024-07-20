## oils_failures_allowed: 1
## our_shell: ysh

#### shSplit() respects IFS

var s = ' aa a bb b   '

argv.py @[shSplit(s)]

setvar IFS = 'a'

argv.py @[shSplit(s)]

setvar IFS = 'b'

argv.py @[shSplit(s)]

## STDOUT:
['aa', 'a', 'bb', 'b']
[' ', '', ' ', ' bb b   ']
[' aa a ', '', ' ', '   ']
## END


#### getVar() gets global or local vars

# compare with shvarGet(), which does dynamic scope

proc my-proc {
  var mylocal = 43

  echo g=$[getVar('g')]
  echo mylocal=$[getVar('mylocal')]

  # the whole purpose is dynamic variable names / dynamic binding
  var prefix = 'my'
  echo mylocal=$[getVar(prefix ++ 'local')]

  echo not_global_or_local=$[getVar('not_global_or_local')]
}

proc main {
  var not_global_or_local = 42
  my-proc
}

var g = 'global'

main

## STDOUT:
g=global
mylocal=43
mylocal=43
not_global_or_local=null
## END

#### ASCII upper() lower()

var x = 'abc-'
var y = 'XYZ!'

echo $x
echo $y
echo

echo $[x => upper()]
echo $[x => lower()]
echo $[y => upper()]
echo $[y => lower()]

## STDOUT:
abc-
XYZ!

ABC-
abc-
XYZ!
xyz!
## END

#### Unicode upper() lower()

# Adapted from spec/var-op-bash

# https://www.utf8-chartable.de/unicode-utf8-table.pl

var x = u'\u{C0}\u{C8}'  # upper grave
var y = u'\u{E1}\u{E9}'  # lower acute

echo $x
echo $y
echo

echo $[x => upper()]
echo $[x => lower()]
echo $[y => upper()]
echo $[y => lower()]

## STDOUT:
ÀÈ
áé
## END
