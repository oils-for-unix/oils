## oils_failures_allowed: 1

#### pp asdl

shopt -s ysh:upgrade

fopen >out.txt {
  x=42
  setvar y = {foo: x}

  pp asdl (x)
  pp asdl (y)

  # TODO, this might be nice?
  # pp asdl (x, y)
}

# Two lines with value.Str
grep -n -o value.Str out.txt

# Dict should have an address
#grep -n -o 'Dict 0x' out.txt

#cat out.txt

## STDOUT:
1:value.Str
2:value.Str
## END

#### pp asdl can handle an object cycle

shopt -s ysh:upgrade

var d = {}
setvar d.cycle = d

pp line (d) | fgrep -o '{"cycle":'

pp asdl (d) | fgrep -o 'cycle ...'

## STDOUT:
{"cycle":
cycle ...
## END

#### pp line supports BashArray, BashAssoc

declare -a array=(a b c)
pp line (array)

array[5]=z
pp line (array)

declare -A assoc=([k]=v [k2]=v2)
pp line (assoc)

# I think assoc arrays can never null / unset

assoc['k3']=
pp line (assoc)

## STDOUT:
(BashArray)   ["a","b","c"]
(BashArray)   ["a","b","c",null,null,"z"]
(BashAssoc)   {"k":"v","k2":"v2"}
(BashAssoc)   {"k":"v","k2":"v2","k3":""}
## END


#### pp gc-stats

pp gc-stats

## STDOUT:
## END


#### pp cell
x=42

pp cell x
echo status=$?

pp -- cell :x
echo status=$?

pp cell nonexistent
echo status=$?
## STDOUT:
x = (Cell exported:F readonly:F nameref:F val:(value.Str s:42))
status=0
x = (Cell exported:F readonly:F nameref:F val:(value.Str s:42))
status=0
status=1
## END

#### pp cell on indexed array with hole
declare -a array
array[3]=42
pp cell array
## STDOUT:
array = (Cell exported:F readonly:F nameref:F val:(value.BashArray strs:[_ _ _ 42]))
## END


#### pp proc
shopt --set ysh:upgrade

# This has to be a separate file because sh_spec.py strips comments!
. $REPO_ROOT/spec/testdata/doc-comments.sh

pp proc
echo ---

# print one
pp proc f

## STDOUT:
proc_name	doc_comment
f	"doc ' comment with \" quotes"
g	""
myproc	"YSH-style proc"
"true"	"Special quoting rule"
---
proc_name	doc_comment
f	"doc ' comment with \" quotes"
## END

