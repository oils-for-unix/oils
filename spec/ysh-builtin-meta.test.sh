## oils_failures_allowed: 2

#### shvm guts
x=42
setvar y = {foo: x}

shvm guts (x)
shvm guts (y)

#### shvm gc-stats

shvm gc-stats

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

