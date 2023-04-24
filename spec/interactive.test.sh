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

#### interactive shell loads files in rcdir (when combined with -c)
case $SH in dash|bash|mksh) exit ;; esac

$SH -c 'echo A'

cat >$TMP/rcfile <<EOF
echo 'rcfile first'
EOF

mkdir -p $TMP/rcdir

cat >$TMP/rcdir/file1 <<EOF
echo rcdir 1
EOF

cat >$TMP/rcdir/file2 <<EOF
echo rcdir 2
EOF

# --rcdir only
$SH --rcdir $TMP/rcdir -i -c 'echo B'

$SH --rcfile $TMP/rcfile --rcdir $TMP/rcdir -i -c 'echo C'

## STDOUT:
A
rcdir 1
rcdir 2
B
rcfile first
rcdir 1
rcdir 2
C
## END
## N-I dash/mksh/bash STDOUT:
## END

#### nonexistent --rcdir is ignored
case $SH in dash|bash|mksh) exit ;; esac

$SH --rcdir $TMP/__does-not-exist -i -c 'echo hi'
echo status=$?

## STDOUT:
hi
status=0
## END
## N-I dash/bash/mksh STDOUT:
## END

#### shell doesn't load rcfile/rcdir if --norc is given
case $SH in dash|mksh) exit ;; esac

$SH -c 'echo A'

cat >$TMP/rcfile <<EOF
echo rcfile
EOF

mkdir -p $TMP/rcdir
cat >$TMP/rcdir/file1 <<EOF
echo rcdir 1
EOF

cat >$TMP/rcdir/file2 <<EOF
echo rcdir 2
EOF

$SH --norc --rcfile $TMP/rcfile -c 'echo C'
case $SH in bash) exit ;; esac

$SH --norc --rcfile $TMP/rcfile --rcdir $TMP/rcdir -c 'echo D'

## STDOUT:
A
C
D
## END
## OK bash STDOUT:
A
C
## END
## N-I dash/mksh STDOUT:
## END


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
