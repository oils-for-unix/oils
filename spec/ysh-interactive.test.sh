## our_shell: ysh

#### yshrc
cat >$TMP/yshrc <<EOF
proc f {
  if ('foo') {
    echo yshrc
  }
}
f
EOF
$SH --rcfile $TMP/yshrc -i -c 'echo hello'
## STDOUT:
yshrc
hello
## END

#### YSH_HISTFILE

export YSH_HISTFILE=myhist
rm -f myhist

echo 'echo 42
echo 43
echo 44' | $SH --norc -i 

cat myhist

## STDOUT:
42
43
44
^D
echo 42
echo 43
echo 44
## END
