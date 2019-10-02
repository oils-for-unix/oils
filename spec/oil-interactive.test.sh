
#### oilrc
cat >$TMP/oilrc <<EOF
proc f {
  if ('foo') {
    echo oilrc
  }
}
f
EOF
$SH --rcfile $TMP/oilrc -i -c 'echo hello'
## STDOUT:
oilrc
hello
## END
