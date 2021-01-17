# Oil xtrace

#### xtrace_details
shopt -s oil:basic
set -x

dir=/
if [[ -d $dir ]]; then
  (( a = 42 ))
fi
cd /

## stdout-json: ""
## STDERR:
+ builtin cd '/'
## END

#### proc and shell function
shopt --set oil:basic
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
[ proc shfunc 1
  + builtin ':' 1
] proc
[ proc p 2
  + builtin ':' 2
] proc
## END

#### eval
shopt --set oil:basic
set -x

eval 'echo 1; echo 2'
## STDOUT:
1
2
## END
## STDERR:
[ eval
  + builtin echo 1
  + builtin echo 2
] eval
## END

#### source
echo 'echo source-argv: "$@"' > lib.sh

shopt --set oil:basic
set -x

source lib.sh 1 2 3

## STDOUT:
source-argv: 1 2 3
## END
## STDERR:
[ source lib.sh 1 2 3
  + builtin echo 'source-argv:' 1 2 3
] source
## END

#### external and builtin
shopt --set oil:basic
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
> command 12345: env false
< command 12345: status 1
+ builtin true
+ builtin set '+x'
## END

#### subshell
shopt --set oil:basic
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
    exit 3  # this is control flow, so it's not traced?
  )
  set +x
} 2>err.txt

sed --regexp-extended 's/[[:digit:]]{2,}/12345/g' err.txt >&2

## stdout-json: ""
## STDERR:
+ builtin ':' begin
> forkwait 12345
  + 12345 builtin ':' 1
  [ 12345 proc p
    + 12345 builtin ':' p
  ] 12345 proc
< forkwait 12345: status 3
+ builtin set '+x'
## END

#### command sub
shopt --set oil:basic
set -x

{
  echo foo=$(echo bar)
  set +x
} 2>err.txt

sed --regexp-extended 's/[[:digit:]]{2,}/12345/g' err.txt >&2

## STDOUT:
foo=bar
## END
## STDERR:
> command sub 12345
  + 12345 builtin echo bar
< command sub 12345: status 0
+ builtin echo 'foo=bar'
+ builtin set '+x'
## END

#### process sub (nondeterministic)
shopt --set oil:basic
shopt --unset errexit
set -x

# we wait() for them all at the end

{
  : begin
  cat <(seq 2) <(seq 1)
  set +x
} 2>err.txt

sed --regexp-extended 's/[[:digit:]]{2,}/12345/g; s|/fd/.|/fd/N|g' err.txt >&2

## STDOUT:
1
2
1
## END
## STDERR:
+ builtin ':' begin
| procsub 12345
| procsub 12345
> command 12345: cat '/dev/fd/N' '/dev/fd/N'
< command 12345: status 0
. procsub 12345: status 0
. procsub 12345: status 0
+ builtin set '+x'
## END

#### pipeline (nondeterministic)
shopt --set oil:basic
set -x

myfunc() {
  echo 1
  echo 2
}

: begin
myfunc | sort | wc -l
: end

## stdout-json: ""
## STDERR:
## END

#### singleton pipeline

# Hm extra tracing

shopt --set oil:basic
set -x

: begin
! false
: end

## stdout-json: ""
## STDERR:
+ builtin ':' begin
[ pipeline
  + builtin false
] pipeline
+ builtin ':' end
## END

#### Background pipeline (separate code path)

shopt --set oil:basic
shopt --unset errexit
set -x

myfunc() {
  echo 2
  echo 1
}

: begin
myfunc | sort | grep ZZZ &
wait
echo status=$?

## STDOUT:
status=0
## END
## STDERR:
## END

#### Background process with fork and & (nondeterministic)
shopt --set oil:basic
set -x

sleep 0.1 &
wait

shopt -s oil:basic

fork {
  sleep 0.1
}
wait

## stdout-json: ""
## STDERR:
## END

# others: redirects?

#### here doc
shopt --set oil:basic
shopt --unset errexit
set -x

: begin
tac <<EOF
3
2
EOF

echo --

# Two here docs!
diff -u - /dev/fd/3 <<EOF 3<<EOF2
zz
yy
EOF
zz
EOF2

: end



## STDOUT:
## END
## STDERR:
## END
