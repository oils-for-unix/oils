#!/bin/bash
#
# Tests for pipelines.

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

### |&
stdout_stderr.py |& cat
# stdout-json: "STDERR\nSTDOUT\n"
# N-I dash/mksh stdout-json: ""
