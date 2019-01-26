#!/bin/bash
#
# Usage:
#   ./u.sh <function name>

#_OVM_RESOURCE_ROOT=. PYTHONPATH=. demo/bugs/u2.py
_OVM_RESOURCE_ROOT=. PYTHONPATH=. strace -e fcntl,dup2,close demo/bugs/fd_state.py
