#!/usr/bin/env bash

echo source-argv: $@
# 'shift' will only apply to the args of 'f()' when no new args are provided.
# This can mutate the "caller's" arguments array!
shift
local foo=foo_val
