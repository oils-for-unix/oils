## oils_failures_allowed: 1

#### runproc
shopt --set parse_proc parse_at

f() {
  write -- f "$@"
}
proc p {
  write -- p @ARGV
}
runproc f 1 2
echo status=$?

runproc p 3 4
echo status=$?

runproc invalid 5 6
echo status=$?

runproc
echo status=$?

## STDOUT:
f
1
2
status=0
p
3
4
status=0
status=1
status=2
## END


#### runproc typed args
shopt --set parse_brace parse_proc

proc p {
  echo 'hi from p'
}

# The block is ignored for now
runproc p { 
  echo myblock 
}
echo

proc ty (w; t; n; block) {
  echo 'ty'
  pp line (w)
  pp line (t)
  pp line (n)
  echo $[type(block)]
}

ty a (42; n=99; ^(echo ty))
echo

runproc ty a (42; n=99; ^(echo ty))
echo

runproc ty a (42; n=99) {
  echo 'ty gets literal'
}

# TODO: Command vs. Block vs. Literal Block should be unified

## STDOUT:
hi from p

ty
(Str)   "a"
(Int)   42
(Int)   99
Command

ty
(Str)   "a"
(Int)   42
(Int)   99
Command

ty
(Str)   "a"
(Int)   42
(Int)   99
Block
## END


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
{"type":"BashArray","data":{"0":"a","1":"b","2":"c"}}
{"type":"BashArray","data":{"0":"a","1":"b","2":"c","5":"z"}}
{"type":"BashAssoc","data":{"k":"v","k2":"v2"}}
{"type":"BashAssoc","data":{"k":"v","k2":"v2","k3":""}}
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


#### pp (x) is like = keyword

shopt --set ysh:upgrade
source $LIB_YSH/list.ysh

# It can be piped!

pp ('foo') | cat

pp ("isn't this sq") | cat

pp ('"dq $myvar"') | cat

pp (r'\ backslash \\') | cat

pp (u'one \t two \n') | cat

# Without a terminal, default width is 80
pp (repeat([123], 40)) | cat

## STDOUT:
  pp ('foo') | cat
     ^
[ stdin ]:5: (Str)   'foo'
  pp ("isn't this sq") | cat
     ^
[ stdin ]:7: (Str)   b'isn\'t this sq'
  pp ('"dq $myvar"') | cat
     ^
[ stdin ]:9: (Str)   '"dq $myvar"'
  pp (r'\ backslash \\') | cat
     ^
[ stdin ]:11: (Str)   b'\\ backslash \\\\'
  pp (u'one \t two \n') | cat
     ^
[ stdin ]:13: (Str)   b'one \t two \n'
  pp (repeat([123], 40)) | cat
     ^
[ stdin ]:15: (List)
    [
        123, 123, 123, 123, 123, 123, 123, 123, 123, 123, 123, 123, 123, 123,
        123, 123, 123, 123, 123, 123, 123, 123, 123, 123, 123, 123, 123, 123,
        123, 123, 123, 123, 123, 123, 123, 123, 123, 123, 123, 123
    ]
## END
