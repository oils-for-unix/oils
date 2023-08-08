#!/usr/bin/env python
"""
const.py
"""

DEFAULT_INT_WIDTH = 3  # 24 bits

# 2^24 - 1 is used as an invalid/uninitialized value for ASDL integers.

# Why?  We have a few use cases for invalid/sentinel values:
# - span_id, line_id.  Sometimes we don't have a span ID.
# - file descriptor: 'read x < f.txt' vs 'read x 0< f.txt'
#
# Other options for representation:
#
# 1. ADSL could use signed integers, then -1 is valid.
# 2. Use a type like fd = None | Some(int fd)
#
# I don't like #1 because ASDL is lazily-decoded, and then we have to do sign
# extension on demand.  (24 bits to 32 or 64).  As far as I can tell, sign
# extension requires a branch, at least in portable C (on the sign bit).
#
# The second option is semantically cleaner.  But it needlessly
# inflates the size of both the source code and the data.  Instead of having a
# single "inline" integer, we would need a reference to another value.
#
# We could also try to do some fancy thing like fd = None |
# Range<1..max_fd>(fd), with smart encoding.  But that is overkill for these
# use cases.
#
# Using InvalidInt instead of -1 seems like a good compromise.

NO_INTEGER = (1 << (DEFAULT_INT_WIDTH * 8)) - 1

# NOTE: In Python: 1 << (n * 8) - 1 is wrong!  I thought that bit shift would
# have higher precedence.
