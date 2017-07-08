#!/usr/bin/env bash
# 
# NOTE: The error message is different at interactive prompt:
#
# $ foo (ls)
# -bash: syntax error near unexpected token `LC_COLLATE=C'
#
# vs.
#
# bash: line 1: syntax error near unexpected token `ls'
#
# Does -bash: mean interactive?  Grep the source.

foo (ls)
