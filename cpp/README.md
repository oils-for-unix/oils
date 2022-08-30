`cpp/` - Hand-written C++ Code
==============================

Structure of this directory:

Correspond to repo directories:

    leaky_core.{cc,h}
    leaky_osh.{cc,h}
      from osh import arith_parse
      from osh import bool_stat

    leaky_pylib.{cc,h}  # Corresponds to pylib/
      from pylib import os_path
      from pylib import path_stat

    leaky_pgen2.{cc,h}
      from pgen2 import parse

    leaky_stdlib.{cc,h}  # Python standard library modules
      import fcntl
      import time
      import posix  # forked in native/posixmodule.c

    qsn.h

Correspond to files:

    leaky_core_error.h    # Straggler for core/error.py
    leaky_core_pyerror.h  # core/pyerror.py

    leaky_libc.{cc,h}  # Corresponds to Python extension native/libc.c

    # These three are separate because there is generated code associated with
    # them, like the re2c lexer.

    leaky_frontend_flag_spec.{cc,h}
      from frontend import flag_spec

    leaky_frontend_match.{cc,h}
      from frontend import match

    leaky_frontend_tdop.{cc,h}
      from frontend import tdop

TODO: We want non-leaky versions of all files!
