#!/usr/bin/env bash
#
# For testing the Python sketch

### builtin
echo hi
# stdout: hi

### command sub 
echo $(expr 3)
# stdout: 3

### command sub with builtin
echo $(echo hi)
# stdout: hi

### pipeline
hostname | wc -l
# stdout: 1

### pipeline with builtin
echo hi | wc -l
# stdout: 1

### here doc with var
v=one
tac <<EOF
$v
"two
EOF
# stdout-json: "\"two\none\n"

### here doc without var
tac <<"EOF"
$v
"two
EOF
# stdout-json: "\"two\n$v\n"

### here doc with builtin
read var <<EOF
value
EOF
echo "var = $var"
# stdout: var = value

### Redirect external command
expr 3 > $TMP/expr3.txt
cat $TMP/expr3.txt
# stdout: 3
# stderr-json: ""

### Redirect with builtin
echo hi > _tmp/hi.txt
cat _tmp/hi.txt
# stdout: hi

### Here doc with redirect
cat <<EOF >_tmp/smoke1.txt
one
two
EOF
wc -c _tmp/smoke1.txt
# stdout: 8 _tmp/smoke1.txt

### "$@" "$*"
func () {
  argv.py "$@" "$*"
}
func "a b" "c d"
# stdout: ['a b', 'c d', 'a b c d']

### $@ $*
func() {
  argv.py $@ $*
}
func "a b" "c d"
# stdout: ['a', 'b', 'c', 'd', 'a', 'b', 'c', 'd']

### failed command
ls /nonexistent
# status: 2

### subshell
(echo 1; echo 2)
# stdout-json: "1\n2\n"
# status: 0

### for loop
for i in a b c
do
  echo $i
done
# stdout-json: "a\nb\nc\n"
# status: 0

### vars
a=5
echo $a ${a} "$a ${a}"
# stdout: 5 5 5 5
