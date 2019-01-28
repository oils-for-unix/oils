#!/usr/bin/env bash
#
# Miscellaneous tests for the command language.

#### Command block
{ which ls; }
## stdout: /bin/ls

#### Permission denied
touch $TMP/text-file
$TMP/text-file
## status: 126

#### Not a dir
$TMP/not-a-dir/text-file
## status: 127

#### Name too long
./0123456789012345678901234567890123456789012345678901234567890123456789012345678901234567890123456789012345678901234567890123456789012345678901234567890123456789012345678901234567890123456789012345678901234567890123456789012345678901234567890123456789012345678901234567890123456789012345678901234567890123456789012345678901234567890123456789012345678901234567890123456789012345678901234567890123456789012345678901234567890123456789012345678901234567890123456789012345678901234567890123456789012345678901234567890123456789012345678901234567890123456789012345678901234567890123456789012345678901234567890123456789012345678901234567890123456789
## status: 127
## OK dash status: 2
## OK bash status: 126

#### External programs don't have _OVM in environment
# bug fix for leakage
env | grep _OVM
echo status=$?
## stdout: status=1

#### File Descriptor State is clean when running script
# bug fix for leakage

# tail -n + 2: get rid of first line
cat >$TMP/script.sh <<'EOF'
out=$1
ls -l /proc/$$/fd | tail -n +2 > $out
EOF

# Run it and count output
$SH $TMP/script.sh $TMP/fd.txt
count=$(cat $TMP/fd.txt | wc -l)
echo "count=$count"

# bash and dash are very orderly: there are 3 pipes and then 10 or 255
# has the script.sh.
# mksh and zsh have /dev/tty saved as well.  Not sure why.

# for debugging failures
if test "$count" -ne 4; then
  cat $TMP/fd.txt >&2
fi
## stdout: count=4
## OK mksh/zsh stdout: count=5

#### File with no shebang is executed
# most shells execute /bin/sh; bash may execute itself
echo 'echo hi' > $TMP/no-shebang
chmod +x $TMP/no-shebang
$SH -c '$TMP/no-shebang'
## stdout: hi
## status: 0
