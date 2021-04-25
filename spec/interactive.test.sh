#

#### 'exit' in oshrc (regression)
cat >$TMP/oshrc <<EOF
echo one
exit 42
echo two
EOF
$SH --rcfile $TMP/oshrc -i -c 'echo hello'
## status: 42
## STDOUT:
one
## END
## N-I dash status: 2
## N-I dash stdout-json: ""
## N-I mksh status: 1
## N-I mksh stdout-json: ""

#### fatal errors continue
# NOTE: tried here doc, but sys.stdin.isatty() fails.  Could we fake it?
$SH --rcfile /dev/null -i -c '
echo $(( 1 / 0 ))
echo one
exit 42
'
## status: 42
## STDOUT:
one
## END
## N-I dash status: 2
## N-I dash stdout-json: ""
## N-I mksh status: 1
## N-I mksh stdout-json: ""

#### interactive shell loads rcfile (when combined with -c)
$SH -c 'echo 1'
cat >$TMP/rcfile <<EOF
echo RCFILE
EOF
$SH --rcfile $TMP/rcfile -i -c 'echo 2'
## STDOUT:
1
RCFILE
2
## END
## N-I dash/mksh STDOUT:
1
## END
## N-I dash status: 2
## N-I mksh status: 1

#### interactive shell runs PROMPT_COMMAND after each command
export PS1=''  # OSH prints prompt to stdout

case $SH in
  *bash|*osh)
    $SH --rcfile /dev/null -i << EOF
PROMPT_COMMAND='echo PROMPT'
echo one
echo two
EOF
    ;;
esac

# Paper over difference with OSH
case $SH in *bash) echo '^D';; esac

## STDOUT:
PROMPT
one
PROMPT
two
PROMPT
^D
## END
## N-I dash/mksh stdout-json: ""


#### parse error in PROMPT_COMMAND
export PS1=''  # OSH prints prompt to stdout

case $SH in
  *bash|*osh)
    $SH --rcfile /dev/null -i << EOF
PROMPT_COMMAND=';'
echo one
echo two
EOF
    ;;
esac

# Paper over difference with OSH
case $SH in *bash) echo '^D';; esac

## STDOUT:
one
two
^D
## END
## N-I dash/mksh stdout-json: ""

#### runtime error in PROMPT_COMMAND
export PS1=''  # OSH prints prompt to stdout

case $SH in
  *bash|*osh)
    $SH --rcfile /dev/null -i << 'EOF'
PROMPT_COMMAND='echo PROMPT $(( 1 / 0 ))'
echo one
echo two
EOF
    ;;
esac

# Paper over difference with OSH
case $SH in *bash) echo '^D';; esac

## STDOUT:
one
two
^D
## END
## N-I dash/mksh stdout-json: ""

#### Error message with bad oshrc file (currently ignored)
cd $TMP
echo 'foo >' > bad_oshrc

$SH --rcfile bad_oshrc -i -c 'echo hi' 2>stderr.txt
echo status=$?

# bash prints two lines
grep --max-count 1 -o 'bad_oshrc:' stderr.txt

## STDOUT:
hi
status=0
bad_oshrc:
## END

## N-I dash/mksh status: 1
## N-I dash STDOUT:
status=2
## END
## N-I mksh STDOUT:
status=1
## END

#### PROMPT_COMMAND can see $?, like bash

# bug fix #853

case $SH in (dash|mksh) exit ;; esac

export PS1=''  # OSH prints prompt to stdout

case $SH in
  *bash|*osh)
    $SH --rcfile /dev/null -i << 'EOF'
myfunc() { echo last_status=$?;  }
PROMPT_COMMAND='myfunc'
( exit 42 )
( exit 43 )
echo ok
EOF
    ;;
esac

# Paper over difference with OSH
case $SH in *bash) echo '^D';; esac
## STDOUT:
last_status=0
last_status=42
last_status=43
ok
last_status=0
^D
## END
## N-I dash/mksh stdout-json: ""

#### PROMPT_COMMAND that writes to BASH_REMATCH
export PS1=''

case $SH in
  *bash|*osh)
    $SH --rcfile /dev/null -i << 'EOF'
PROMPT_COMMAND='[[ clobber =~ (.)(.)(.) ]]; echo ---'
echo one
[[ bar =~ (.)(.)(.) ]]
echo ${BASH_REMATCH[@]}
EOF
    ;;
esac

# Paper over difference with OSH
case $SH in *bash) echo '^D';; esac

## STDOUT:
---
one
---
---
bar b a r
---
^D
## END
## OK bash STDOUT:
---
one
---
---
clo c l o
---
^D
## END
## N-I dash/mksh stdout-json: ""
