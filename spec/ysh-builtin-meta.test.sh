## oils_failures_allowed: 1

#### pp value

shopt -s ysh:upgrade

fopen >out.txt {
  x=42
  setvar y = {foo: x}

  pp value (x)
  pp value (y)

  # TODO, this might be nice?
  # pp value (x, y)
}

# Two lines with value.Str
grep -n -o value.Str out.txt
echo

# Dict should have an address
grep -n -o 'Dict 0x' out.txt

#cat out.txt

## STDOUT:
1:value.Str
2:value.Str

2:Dict 0x
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
shopt --set oil:upgrade

# This has to be a separate file because sh_spec.py strips comments!
. $REPO_ROOT/spec/testdata/doc-comments.sh

pp proc
echo ---
pp proc f
## STDOUT:
proc_name	doc_comment
f	'doc \' comment with " quotes'
g	''
myproc	'Oil-style proc'
---
proc_name	doc_comment
f	'doc \' comment with " quotes'
## END

