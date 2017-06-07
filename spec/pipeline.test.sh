#!/bin/bash
#
# Tests for pipelines.
# NOTE: Grammatically, ! is part of the pipeline:
#
# pipeline         :      pipe_sequence
#                  | Bang pipe_sequence

### Brace group in pipeline
{ echo one; echo two; } | tac
# stdout-json: "two\none\n"

### For loop in pipeline
for w in one two; do
  echo $w
done | tac
# stdout-json: "two\none\n"

### Exit code is last status
expr $0 : '.*/osh$' && exit 99  # Disabled because of spec-runner.sh issue
echo a | egrep '[0-9]+'
# status: 1

### PIPESTATUS
{ sleep 0.03; exit 1; } | { sleep 0.02; exit 2; } | { sleep 0.01; exit 3; }
echo ${PIPESTATUS[@]}
# stdout: 1 2 3
# N-I dash status: 2
# N-I zsh status: 3
# N-I dash/zsh stdout-json: ""

### |&
stdout_stderr.py |& cat
# stdout-json: "STDERR\nSTDOUT\n"
# status: 0
# N-I dash/mksh stdout-json: ""
# N-I dash status: 2

### ! turns non-zero into zero
! $SH -c 'exit 42'; echo $?
# stdout: 0
# status: 0

### ! turns zero into 1
! $SH -c 'exit 0'; echo $?
# stdout: 1
# status: 0

### ! in if
if ! echo hi; then
  echo TRUE
else
  echo FALSE
fi
# stdout-json: "hi\nFALSE\n"
# status: 0

### ! with ||
! echo hi || echo FAILED
# stdout-json: "hi\nFAILED\n"
# status: 0

### ! with { }
! { echo 1; echo 2; } || echo FAILED
# stdout-json: "1\n2\nFAILED\n"
# status: 0

### ! with ( )
! ( echo 1; echo 2 ) || echo FAILED
# stdout-json: "1\n2\nFAILED\n"
# status: 0

### ! is not a command
v='!'
$v echo hi
# status: 127

