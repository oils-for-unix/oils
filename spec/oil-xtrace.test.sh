# Oil xtrace

#### Customize PS4
shopt -s oil:upgrade
set -x

# Reuse the default
PS4='$LINENO '"$PS4"
echo 1; echo 2
echo 3
## STDOUT:
1
2
3
## END
## STDERR:
5 . builtin echo 1
5 . builtin echo 2
6 . builtin echo 3
## END


#### xtrace_details doesn't show [[ ]] etc.
shopt -s oil:upgrade
set -x

dir=/
if [[ -d $dir ]]; then
  (( a = 42 ))
fi
cd /

## stdout-json: ""
## STDERR:
. builtin cd '/'
## END

#### xtrace_details AND xtrace_rich on
shopt -s oil:upgrade xtrace_details
shopt --unset errexit
set -x

{
  env false
  set +x
} 2>err.txt

sed --regexp-extended 's/[[:digit:]]{2,}/12345/g' err.txt >&2

## STDOUT:
## END
## STDERR:
| command 12345: env false
; process 12345: status 1
. builtin set '+x'
## END

#### proc and shell function
shopt --set oil:upgrade
set -x

shfunc() {
  : $1
}

proc p {
  : $1
}

shfunc 1
p 2
## stdout-json: ""
## STDERR:
> proc shfunc 1
  . builtin ':' 1
< proc shfunc
> proc p 2
  . builtin ':' 2
< proc p
## END

#### eval
shopt --set oil:upgrade
set -x

eval 'echo 1; echo 2'
## STDOUT:
1
2
## END
## STDERR:
> eval
  . builtin echo 1
  . builtin echo 2
< eval
## END

#### source
echo 'echo source-argv: "$@"' > lib.sh

shopt --set oil:upgrade
set -x

source lib.sh 1 2 3

## STDOUT:
source-argv: 1 2 3
## END
## STDERR:
> source lib.sh 1 2 3
  . builtin echo 'source-argv:' 1 2 3
< source lib.sh
## END

#### external and builtin
shopt --set oil:upgrade
shopt --unset errexit
set -x

{
  env false
  true
  set +x
} 2>err.txt

# normalize PIDs, assumed to be 2 or more digits
sed --regexp-extended 's/[[:digit:]]{2,}/12345/g' err.txt >&2

## stdout-json: ""
## STDERR:
| command 12345: env false
; process 12345: status 1
. builtin true
. builtin set '+x'
## END

#### subshell
shopt --set oil:upgrade
shopt --unset errexit
set -x

proc p {
  : p
}

{
  : begin
  ( 
    : 1
    p
    exit 3
  )
  set +x
} 2>err.txt

# Hack: sort for determinism
sed --regexp-extended 's/[[:digit:]]{2,}/12345/g' err.txt | LANG=C sort >&2

## stdout-json: ""
## STDERR:
    . 12345 builtin ':' p
  + 12345 exit 3
  . 12345 builtin ':' 1
  < 12345 proc p
  > 12345 proc p
. builtin ':' begin
. builtin set '+x'
; process 12345: status 3
| forkwait 12345
## END

#### command sub
shopt --set oil:upgrade
set -x

{
  echo foo=$(echo bar)
  set +x

} 2>err.txt

# HACK: sort because xtrace output has non-determinism.
# This is arguably a bug -- see issue #995.
# The real fix might be to sys.stderr.flush() in few places?
sed --regexp-extended 's/[[:digit:]]{2,}/12345/g' err.txt | LANG=C sort >&2

## STDOUT:
foo=bar
## END
## STDERR:
  . 12345 builtin echo bar
. builtin echo 'foo=bar'
. builtin set '+x'
; process 12345: status 0
| command sub 12345
## END

#### process sub (nondeterministic)
shopt --set oil:upgrade
shopt --unset errexit
set -x

# we wait() for them all at the end

{
  : begin
  cat <(seq 2) <(echo 1)
  set +x
} 2>err.txt

# SORT for determinism
sed --regexp-extended 's/[[:digit:]]{2,}/12345/g; s|/fd/.|/fd/N|g' err.txt |
  LC_ALL=C sort >&2
#cat err.txt >&2

## STDOUT:
1
2
1
## END

## STDERR:
  . 12345 builtin echo 1
  . 12345 exec seq 2
. builtin ':' begin
. builtin set '+x'
; process 12345: status 0
; process 12345: status 0
; process 12345: status 0
| command 12345: cat '/dev/fd/N' '/dev/fd/N'
| proc sub 12345
| proc sub 12345
## END

#### pipeline (nondeterministic)
shopt --set oil:upgrade
set -x

myfunc() {
  echo 1
  echo 2
}

{
  : begin
  myfunc | sort | wc -l
  set +x
} 2>err.txt

# SORT for determinism
sed --regexp-extended 's/[[:digit:]]{2,}/12345/g; s|/fd/.|/fd/N|g' err.txt | 
  LC_ALL=C sort >&2

## STDOUT:
2
## END
## STDERR:
      . 12345 builtin echo 1
      . 12345 builtin echo 2
    . 12345 exec sort
    < 12345 proc myfunc
    > 12345 proc myfunc
  ; process 12345: status 0
  ; process 12345: status 0
  ; process 12345: status 0
  | command 12345: wc -l
  | part 12345
  | part 12345
. builtin ':' begin
. builtin set '+x'
< pipeline
> pipeline
## END

#### singleton pipeline

# Hm extra tracing

shopt --set oil:upgrade
set -x

: begin
! false
: end

## stdout-json: ""
## STDERR:
. builtin ':' begin
> pipeline
  . builtin false
< pipeline
. builtin ':' end
## END

#### Background pipeline (separate code path)

shopt --set oil:upgrade
shopt --unset errexit
set -x

myfunc() {
  echo 2
  echo 1
}

{
	: begin
	myfunc | sort | grep ZZZ &
	wait
	echo status=$?
  set +x
} 2>err.txt

# SORT for determinism
sed --regexp-extended 's/[[:digit:]]{2,}/12345/g' err.txt |
  LC_ALL=C sort >&2

## STDOUT:
status=0
## END
## STDERR:
    . 12345 builtin echo 1
    . 12345 builtin echo 2
  . 12345 exec grep ZZZ
  . 12345 exec sort
  ; process 12345: status 0
  ; process 12345: status 0
  ; process 12345: status 1
  < 12345 proc myfunc
  > 12345 proc myfunc
. builtin ':' begin
. builtin echo 'status=0'
. builtin set '+x'
< wait
> wait
| part 12345
| part 12345
| part 12345
## END

#### Background process with fork and & (nondeterministic)
shopt --set oil:upgrade
set -x

{
  sleep 0.1 &
  wait

  shopt -s oil:upgrade

  fork {
    sleep 0.1
  }
  wait
  set +x
} 2>err.txt

# SORT for determinism
sed --regexp-extended 's/[[:digit:]]{2,}/12345/g' err.txt |
  LC_ALL=C sort >&2

## stdout-json: ""
## STDERR:
  . 12345 exec sleep 0.1
  . 12345 exec sleep 0.1
  ; process 12345: status 0
  ; process 12345: status 0
. builtin fork
. builtin set '+x'
. builtin shopt -s 'oil:upgrade'
< wait
< wait
> wait
> wait
| fork 12345
| fork 12345
## END

# others: redirects?

#### here doc
shopt --set oil:upgrade
shopt --unset errexit
set -x

{
  : begin
  tac <<EOF
3
2
EOF

  set +x
} 2>err.txt

sed --regexp-extended 's/[[:digit:]]{2,}/12345/g' err.txt >&2

## STDOUT:
2
3
## END
## STDERR:
. builtin ':' begin
| here doc 12345
| command 12345: tac
; process 12345: status 0
; process 12345: status 0
. builtin set '+x'
## END

#### Two here docs

# BUG: This trace shows an extra process?

shopt --set oil:upgrade
shopt --unset errexit
set -x

{
  cat - /dev/fd/3 <<EOF 3<<EOF2
xx
yy
EOF
zz
EOF2

  set +x
} 2>err.txt

sed --regexp-extended 's/[[:digit:]]{2,}/12345/g' err.txt >&2

## STDOUT:
xx
yy
zz
## END
## STDERR:
| here doc 12345
| here doc 12345
| command 12345: cat - '/dev/fd/3'
; process 12345: status 0
; process 12345: status 0
; process 12345: status 0
. builtin set '+x'
## END

#### Control Flow
shopt --set oil:upgrade
set -x

for i in 1 2 3 {
  echo $i
  if (i === '2') {
    break
  }
}

for j in a b {
  for k in y z {
    echo $j $k
    if (k === 'y') {
      continue
    }
  }
}

proc zero {
  return 0
}

proc one {
  return 1
}

zero
# one

## STDOUT:
1
2
a y
a z
b y
b z
## END
## STDERR:
. builtin echo 1
. builtin echo 2
+ break 1
. builtin echo a y
+ continue 1
. builtin echo a z
. builtin echo b y
+ continue 1
. builtin echo b z
> proc zero
  + return 0
< proc zero
## END

#### QSN encoded argv
shopt --set oil:upgrade
set -x

echo $'one two\n' $'\u03bc'
## STDOUT:
one two
 μ
## END
## STDERR:
. builtin echo 'one two\n' 'μ'
## END
