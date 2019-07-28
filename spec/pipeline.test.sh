#!/usr/bin/env bash
#
# Tests for pipelines.
# NOTE: Grammatically, ! is part of the pipeline:
#
# pipeline         :      pipe_sequence
#                  | Bang pipe_sequence

#### Brace group in pipeline
{ echo one; echo two; } | tac
## stdout-json: "two\none\n"

#### For loop starts pipeline
for w in one two; do
  echo $w
done | tac
## stdout-json: "two\none\n"

#### While Loop ends pipeline
seq 3 | while read i
do
  echo ".$i"
done
## stdout-json: ".1\n.2\n.3\n"

#### Redirect in Pipeline
echo hi 1>&2 | wc -l
## stdout: 0
## BUG zsh stdout: 1

#### Pipeline comments
echo abcd |    # input
               # blank line
tr a-z A-Z     # transform
## stdout: ABCD

#### Exit code is last status
echo a | egrep '[0-9]+'
## status: 1

#### PIPESTATUS
return3() {
  return 3
}
{ sleep 0.03; exit 1; } | { sleep 0.02; exit 2; } | { sleep 0.01; return3; }
echo ${PIPESTATUS[@]}
## stdout: 1 2 3
## N-I dash status: 2
## N-I dash stdout-json: ""
## N-I zsh status: 0
## N-I zsh stdout-json: "\n"

#### PIPESTATUS with shopt -s lastpipe
shopt -s lastpipe
return3() {
  return 3
}
{ sleep 0.03; exit 1; } | { sleep 0.02; exit 2; } | { sleep 0.01; return3; }
echo ${PIPESTATUS[@]}
## stdout: 1 2 3
## N-I dash status: 2
## N-I dash stdout-json: ""
## N-I zsh status: 0
## N-I zsh stdout-json: "\n"

#### |&
stdout_stderr.py |& cat
## STDOUT:
STDERR
STDOUT
## END
## status: 0
## N-I dash/mksh stdout-json: ""
## N-I dash status: 2
## N-I osh stdout-json: ""
## N-I osh status: 1

#### ! turns non-zero into zero
! $SH -c 'exit 42'; echo $?
## stdout: 0
## status: 0

#### ! turns zero into 1
! $SH -c 'exit 0'; echo $?
## stdout: 1
## status: 0

#### ! in if
if ! echo hi; then
  echo TRUE
else
  echo FALSE
fi
## stdout-json: "hi\nFALSE\n"
## status: 0

#### ! with ||
! echo hi || echo FAILED
## stdout-json: "hi\nFAILED\n"
## status: 0

#### ! with { }
! { echo 1; echo 2; } || echo FAILED
## stdout-json: "1\n2\nFAILED\n"
## status: 0

#### ! with ( )
! ( echo 1; echo 2 ) || echo FAILED
## stdout-json: "1\n2\nFAILED\n"
## status: 0

#### ! is not a command
v='!'
$v echo hi
## status: 127

#### Evaluation of argv[0] in pipeline occurs in child
${cmd=echo} hi | wc -l
echo "cmd=$cmd"
## STDOUT:
1
cmd=
## END
## BUG zsh STDOUT:
1
cmd=echo
## END

#### bash/dash/mksh run the last command is run in its own process
echo hi | read line
echo "line=$line"
## stdout: line=hi
## OK bash/dash/mksh stdout: line=

#### shopt -s lastpipe (always on in OSH)
shopt -s lastpipe
echo hi | read line
echo "line=$line"
## stdout: line=hi
## N-I dash/mksh stdout: line=

#### shopt -s lastpipe (always on in OSH)
shopt -s lastpipe
i=0
seq 3 | while read line; do
  (( i++ ))
done
echo i=$i
## stdout: i=3
## N-I dash/mksh stdout: i=0


#### SIGPIPE causes pipeline to die (regression for issue #295)
cat /dev/urandom | sleep 0.1
echo ${PIPESTATUS[@]}

# hm bash gives '1 0' which seems wrong

## STDOUT:
141 0
## END
## BUG bash STDOUT:
1 0
## END
## N-I zsh stdout:
## N-I dash status: 2
## N-I dash stdout-json: ""
