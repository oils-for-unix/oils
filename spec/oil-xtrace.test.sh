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

#### proc
shopt --set xtrace xtrace_rich

proc f {
  : $1
}
f hi
## stdout-json: ""
## STDERR:
> proc f hi
  + ':' hi
< proc f
## END

#### eval
shopt --set xtrace xtrace_rich

eval 'echo hi'
## stdout-json: ""
## STDERR:
## END

#### source
shopt --set xtrace xtrace_rich

source $REPO_ROOT/spec/testdata/source-argv.sh 1 2 3

## stdout-json: ""
## STDERR:
## END

#### external and builtin
shopt --set xtrace xtrace_rich

env true
cd /
pwd
## stdout-json: ""
## STDERR:
| 123 external env true
. 123 status=0 env true
+ builtin cd /
+ builtin pwd
## END

#### subshell
shopt --set xtrace xtrace_rich

( : 1
  : 2
  exit 3
)
: 4
## stdout-json: ""
## STDERR:
| 123 subshell
  + 123 ':' 1
  + 123 ':' 2
  + 123 exit 3
. 123 subshell (status 3)
+ ':' 4
## END

#### command sub
echo $(echo hi)

## stdout-json: ""
## STDERR:
## END

#### process sub (nondeterministic)

# we wait() for them all at the end

diff -u <(seq 3) <(seq 4)
## stdout-json: ""
## STDERR:
## END

#### pipeline (nondeterministic)
myfunc() {
  echo 1
  echo 2
}

myfunc | sort | wc -l

## stdout-json: ""
## STDERR:
## END

#### fork and & (nondeterministic)

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

