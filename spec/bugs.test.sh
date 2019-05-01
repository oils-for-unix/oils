#!/usr/bin/env bash

#### echo keyword
echo done
## stdout: done

#### if/else
if false; then
  echo THEN
else
  echo ELSE
fi
## stdout: ELSE

#### Turn an array into an integer.
a=(1 2 3)
(( a = 42 )) 
echo $a
## stdout: 42
## N-I dash/ash stdout-json: ""
## N-I dash/ash status: 2

#### Nested % and # operators (looks like a bug, reported by Crestwave)
var=$'\n'
argv.py "${var#?}"
argv.py "${var%''}"
argv.py "${var%"${var#?}"}"
var='a'
argv.py "${var#?}"
argv.py "${var%''}"
argv.py "${var%"${var#?}"}"
## STDOUT:
['']
['\n']
['\n']
['']
['a']
['a']
## END
## N-I dash STDOUT:
['\\n']
['$\\n']
['$']
['']
['a']
['a']
## END

#### # operator with single quoted arg (dash/ash and bash/mksh disagree, reported by Crestwave)
var=a
echo -${var#'a'}-
echo -"${var#'a'}"-
var="'a'"
echo -${var#'a'}-
echo -"${var#'a'}"-
## STDOUT:
--
--
-'a'-
-'a'-
## END
## OK dash/ash STDOUT:
--
-a-
-'a'-
--
## END

#### / operator with single quoted arg (causes syntax error in regex in OSH, reported by Crestwave)
var="++--''++--''"
echo no plus or minus "${var//[+-]}"
echo no plus or minus "${var//['+-']}"
## STDOUT:
no plus or minus ''''
no plus or minus ''''
## END
## status: 0
## OK osh STDOUT:
no plus or minus ''''
## END
## OK osh status: 1
## BUG ash STDOUT:
no plus or minus ''''
no plus or minus ++--++--
## END
## BUG ash status: 0
## N-I dash stdout-json: ""
## N-I dash status: 2

#### single quotes work inside character classes
x='a[[[---]]]b'
echo "${x//['[]']}"
## STDOUT:
a---b
## END
## BUG ash STDOUT:
a[[[---]]]b
## END
## N-I dash stdout-json: ""
## N-I dash status: 2

#### comparison: :- operator with single quoted arg
echo ${unset:-'a'}
echo "${unset:-'a'}"
## STDOUT:
a
'a'
## END
