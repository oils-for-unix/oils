#!/bin/bash
#
# Usage:
#   ./pickle.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

#
# Protocol TWO
#

# PROTO 2
# GLOBAL     -- push self.find_class(mod_name, class_name)
# NEWOBJ     # build object by applying cls.__new__ to argtuple
#            # OK this still relies on __new__ fundamentally, not sure I want
             #  it.
# BINPUT     # store stack top in memo; index is string arg
# BINGET     # push item from memo on stack; index is string arg
# BININT2  -- 10043
# SETITEM  -- calls __dict__.update() or __setstate__()
# BUILD
#
# EMPTY_TUPLE
# EMPTY_DICT
#
# Hm there is no MARK!


# NOTE: There is no INST bytecode.
run() {
  local p=_tmp/instance.pickle

  demo/pickle_instance.py $p

  python3 -m pickletools $p

  # Protocol 0 is viewable as plain text, but protocol 2 isn't
  echo
  echo "--- $p ---"
  echo

  od -c $p
}

#
# Protocol ZERO
#

# The pickle VM has a stack and a memo dictionary.
#
# Oh and it also uses copy_reg and _reconstructor
# OK so what I'm missing is __new__!  I didn't know about that.
# It creates an object without initializing fields.  OK.
# Not sure I want that in OVM2.

# def _reconstructor(cls, base, state):
#     if base is object:
#         obj = object.__new__(cls)
#     else:
#         obj = base.__new__(cls, state)
#         if base.__init__ != object.__init__:
#             base.__init__(obj, state)
#     return obj


# opcodes used:
# GLOBAL
# PUT      # store stack top in memo
# MARK     # set a mark
# REDUCE   # apply a callable
# SETITEM  # add key-value pair to dict
# BUILD    # call __dict__.update()  (or __setstate__)

# TUPLE
# DICT
# INT
# NONE
# STRING


"$@"
