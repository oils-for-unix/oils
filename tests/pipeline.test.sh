#!/bin/bash
#
# Tests for pipelines.

### Basic
{ echo one; echo two; } | tac
# stdout-json: "two\none\n"

### |&
stdout_stderr.py |& cat
# stdout-json: "STDERR\nSTDOUT\n"
# N-I dash/mksh stdout-json: ""
