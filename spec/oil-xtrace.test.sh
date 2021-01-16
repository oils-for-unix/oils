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
] 
[ proc p 2
  + builtin ':' 2
] 
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
] 
## END

#### source
shopt --set oil:basic
set -x

source $REPO_ROOT/spec/testdata/source-argv.sh 1 2 3

## STDOUT:
source-argv: 1 2 3
## END

# TODO: Path shouldn't depend on file system
## STDERR:
[ source '/home/andy/git/oilshell/oil/spec/testdata/source-argv.sh' 1 2 3
  + builtin echo 'source-argv:' '1 2 3'
  + builtin shift
] 
## END

#### external and builtin
shopt --set oil:basic
set -x

env true
cd /
pwd
## stdout-json: ""
## STDERR:
| 123 external env true
. 123 status=0 env true
+ builtin cd '/'
+ builtin pwd
## END

#### subshell
shopt --set oil:basic
shopt --unset errexit
set -x

proc p {
  : p
}

( : begin
  : 2
  p
  exit 3
)
: end
## stdout-json: ""
## STDERR:
| 123 subshell
  + 123 ':' begin
  + 123 ':' 2
  + 123 exit 3
. 123 subshell (status 3)
+ ':' end
## END

#### command sub
shopt --set oil:basic
set -x

echo foo=$(echo bar)

## STDOUT:
hi
## END
## STDERR:
> command sub
  + 1234 builtin echo bar
< command sub
+ builtin echo 'foo=bar'
## END

#### process sub (nondeterministic)
shopt --set oil:basic
shopt --unset errexit
set -x

# we wait() for them all at the end

: begin
diff -u <(seq 3) <(seq 4)
: end

## stdout-json: ""
## STDERR:
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
## END


#### fork and & (nondeterministic)
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
set -x

: begin
tac <<EOF
3
2
EOF
: end
## STDOUT:
## END
## STDERR:
## END
