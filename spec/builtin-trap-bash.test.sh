# builtin-trap-bash.test.sh

#### trap -l
trap -l | grep INT >/dev/null
## status: 0


#### trap -p

trap 'echo exit' EXIT
# debug trap also remains on
#trap 'echo debug' DEBUG

trap -p > parent.txt

trap -p | cat > child.txt

grep EXIT parent.txt >/dev/null
echo status=$?

grep EXIT child.txt >/dev/null
echo status=$?

#grep DEBUG parent.txt >/dev/null
#echo status=$?

#grep DEBUG child.txt >/dev/null
#echo status=$?

## STDOUT:
status=0
status=0
exit
## END

#### trap DEBUG ignores $?
debuglog() {
  echo "  [$@]"
  return 42     # IGNORED FAILURE
}

trap 'debuglog $LINENO' DEBUG

echo status=$?
echo A
echo status=$?
echo B
echo status=$?

## STDOUT:
  [8]
status=0
  [9]
A
  [10]
status=0
  [11]
B
  [12]
status=0
## END

#### but trap DEBUG respects errexit
set -o errexit

debuglog() {
  echo "  [$@]"
  return 42
}

trap 'debuglog $LINENO' DEBUG

echo status=$?
echo A
echo status=$?
echo B
echo status=$?

## status: 42
## STDOUT:
  [10]
## END

#### trap DEBUG with 'return'

debuglog() {
  echo "  [$@]"
}


trap 'debuglog $LINENO; return 42' DEBUG

echo status=$?
echo A
echo status=$?
echo B
echo status=$?

## STDOUT:
  [8]
status=0
  [9]
A
  [10]
status=0
  [11]
B
  [12]
status=0
## END

#### trap DEBUG with 'exit'
debuglog() {
  echo "  [$@]"
}

trap 'debuglog $LINENO; exit 42' DEBUG

echo status=$?
echo A
echo status=$?
echo B
echo status=$?

## status: 42
## STDOUT:
  [7]
## END



#### trap DEBUG
case $SH in (dash|mksh) exit ;; esac

debuglog() {
  echo "  [$@]"
}
trap 'debuglog $LINENO' DEBUG

echo a
echo b; echo c

echo d && echo e
echo f || echo g

(( h = 42 ))
[[ j == j ]]

## STDOUT:
  [8]
a
  [9]
b
  [9]
c
  [11]
d
  [11]
e
  [12]
f
  [14]
  [15]
## END

#### trap DEBUG and command sub / subshell
case $SH in (dash|mksh) exit ;; esac

debuglog() {
  echo "  [$@]"
}
trap 'debuglog $LINENO' DEBUG

echo "result =" $(echo command sub)
( echo subshell )
echo done

## STDOUT:
  [8]
result = command sub
subshell
  [10]
done
## END

#### trap DEBUG and pipeline
case $SH in (dash|mksh) exit 1 ;; esac

debuglog() {
  echo "  [$@]"
}
trap 'debuglog $LINENO' DEBUG

# gets run for each one of these
{ echo a; echo b; }

# only run for the last one, maybe I guess because traps aren't inherited?
{ echo x; echo y; } | wc -l

# gets run for both of these
date | wc -l

date |
  wc -l

## STDOUT:
  [8]
a
  [8]
b
  [10]
2
  [12]
  [12]
1
  [14]
  [15]
1
## END


#### trap DEBUG with compound commands
case $SH in (dash|mksh) exit 1 ;; esac

# I'm not sure if the observed behavior actually matches the bash documentation
# ...
#
# https://www.gnu.org/software/bash/manual/html_node/Bourne-Shell-Builtins.html#Bourne-Shell-Builtins
#
# "If a sigspec is DEBUG, the command arg is executed before every simple 
# command, for command, case command, select command, every arithmetic for
# command, and before the first command executes in a shell function."

debuglog() {
  echo "  [$@]"
}
trap 'debuglog $LINENO' DEBUG

f() {
  local mylocal=1
  for i in "$@"; do
    export i=$i
  done
}

echo '-- assign --'
g=1   # executes ONCE here

echo '-- function call --'
f A B C  # executes ONCE here, but does NOT go into th efunction call


echo '-- for --'
# why does it execute twice here?  because of the for loop?  That's not a
# simple command.
for i in 1 2; do
  echo for1 $i
  echo for2 $i
done

echo '-- while --'
i=0
while (( i < 2 )); do
  echo while1 
  echo while2
  (( i++ ))
done

echo '-- if --'
if true; then
  echo IF
fi

echo '-- case --'
case x in
  (x)
    echo CASE
esac

## STDOUT:
  [16]
-- assign --
  [17]
  [19]
-- function call --
  [20]
  [23]
-- for --
  [24]
  [25]
for1 1
  [26]
for2 1
  [24]
  [25]
for1 2
  [26]
for2 2
  [29]
-- while --
  [30]
  [31]
  [32]
while1
  [33]
while2
  [34]
  [31]
  [32]
while1
  [33]
while2
  [34]
  [31]
  [37]
-- if --
  [38]
  [39]
IF
  [42]
-- case --
  [43]
  [45]
CASE
## END


#### trap RETURN
profile() {
  echo "profile [$@]"
}
g() {
  echo --
  echo g
  echo --
  return
}
f() {
  echo --
  echo f
  echo --
  g
}
# RETURN trap doesn't fire when a function returns, only when a script returns?
# That's not what the manual syas.
trap 'profile x y' RETURN
f
. $REPO_ROOT/spec/testdata/return-helper.sh
## status: 42
## STDOUT:
--
f
--
--
g
--
return-helper.sh
profile [x y]
## END
