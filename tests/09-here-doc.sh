#!/bin/bash
#
# Usage:
#   ./09-here-doc.sh <function name>

foo=bar

cat <<< 'here string'
echo

# var interpolation
cat <<EOF
plain EOF terminator: $foo
EOF

echo

# no var interpolation for any quoted delimiter
cat <<'EOF'
single quoted: $foo
EOF
cat <<"EOF"
double-quoted: $foo
EOF
cat <<\EOF
E escaped: $foo
EOF
cat <<EO\F
F escaped: $foo
EOF

echo

# Strip leading tabs
	cat <<-EOF
	one tab then foo: $foo
	EOF

		cat <<-EOF
		two tabs then foo: $foo
		EOF

	cat <<-EOF
  	two spaces then a tab: $foo
	EOF

# Strip leading and no interpolation
	cat <<-\EOF
	one tab and no interpolation: $foo
	EOF

echo

# output is bar and then foo
cat <<EOF; echo 'command on same physical line as here doc'
HERE CONTENTS
EOF

echo

# Line continuation is ALLOWED in command before here doc.
cat <<EOF\
  ; echo 'command on same logical line as here delimiter, after line continuation'
HERE CONTENTS
EOF

echo

cat <<EOF | tac; echo PIPE ON SAME LINE
PIPE 1
PIPE 2
EOF
echo

cat <<EOF |
PIPE 1
PIPE 2
EOF
tac; echo PIPE ON DIFFERENT LINE
echo

tac <<EOF1 && tac <<EOF2
PIPE A1
PIPE A2
EOF1
PIPE B1
PIPE B2
EOF2
echo

cat <<EOF && echo '&&'
Here doc in first part of &&
EOF
echo

if cat <<EOF; then
here doc in IF CONDITION
EOF
  echo THEN executed
fi
echo

{ cat <<EOF; }; echo BLOCK
here doc in BLOCK
EOF
echo

( cat <<EOF ); echo SUBSHELL
here doc in SUBSHELL
EOF
echo

myfunc() {
  cat <<EOF; echo in function
here doc in FUNCTION
EOF
}
myfunc
echo

case x in
  x) cat <<EOF; echo CASE
here doc in CASE
EOF
  ;;
esac
echo

while read line; do
  echo == ${line} ==
done <<EOF
while 1
while 2
EOF
echo

# NOTE: bash gives a spurious warning here, but executes it correctly:
# tests/09-here-doc.sh: line 131: warning: here-document at line 129 delimited
# by end-of-file (wanted `EOF')
#
# Should be EOF\n) though.

for x in 1 2 $(cat <<EOF
THREE
EOF); do
  echo for word $x
done
echo

if cat <<EOF1; then echo THEN; cat <<EOF2; fi
here doc 1
EOF1
here doc 2
EOF2
echo

# NESTING
if cat <<EOF1 && cat <<EOF2; then echo THEN; cat <<EOF3; fi
here doc 1
EOF1
here doc 2
EOF2
here doc 3
EOF3
echo

# Here doc within here doc
cat <<EOF
one
two
echo $(cat <<EOF2
INNER
EOF2
)
three
four
EOF
echo

# COMPOUND here docs mixed with individual here docs
# This shows it has to be a depth first search, but POST ORDER TRAVERSAL.
while cat <<EOF1; read line; do cat <<EOF2; echo "read line: '$line'"; done <<EOF3
condition here doc
EOF1
body here doc
EOF2
while loop here doc 1
while loop here doc 2
EOF3

echo == DONE HERE DOC TESTS ==
