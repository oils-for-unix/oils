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
{ sleep 0.03; exit 1; } | { sleep 0.02; exit 2; } | { sleep 0.01; exit 3; }
echo ${PIPESTATUS[@]}
## stdout: 1 2 3
## N-I dash status: 2
## N-I zsh status: 3
## N-I dash/zsh stdout-json: ""

#### |&
stdout_stderr.py |& cat
## stdout-json: "STDERR\nSTDOUT\n"
## status: 0
## N-I dash/mksh stdout-json: ""
## N-I dash status: 2

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
## stdout-json: "1\ncmd=\n"
## BUG zsh stdout-json: "1\ncmd=echo\n"

#### last command is run in its own process
echo hi | read line
echo "line=$line"
## stdout: line=
## OK zsh stdout: line=hi

#### shopt -s lastpipe
shopt -s lastpipe
echo hi | read line
echo "line=$line"
## stdout: line=hi
## N-I dash/mksh stdout: line=

#### shopt -s lastpipe
shopt -s lastpipe
i=0
seq 3 | while read line; do
  (( i++ ))
done
echo i=$i
## stdout: i=3
## N-I dash/mksh stdout: i=0

