`cpp/` - Hand-written C++ Code
==============================

Structure of this directory:

Correspond to repo directories:

    core.{cc,h}
    osh.{cc,h}
      from osh import arith_parse
      from osh import bool_stat

    pylib.{cc,h}  # Corresponds to pylib/
      from pylib import os_path
      from pylib import path_stat

    pgen2.{cc,h}
      from pgen2 import parse

    stdlib.{cc,h}  # Python standard library modules
      import fcntl
      import time
      import posix  # forked in native/posixmodule.c

    qsn.h

Correspond to files:

    core_error.h    # Straggler for core/error.py
    core_pyerror.h  # core/pyerror.py

    libc.{cc,h}  # Corresponds to Python extension native/libc.c

    # These three are separate because there is generated code associated with
    # them, like the re2c lexer.

    frontend_flag_spec.{cc,h}
      from frontend import flag_spec

    frontend_match.{cc,h}
      from frontend import match

    osh_tdop.{cc,h}
      from frontend import tdop

TODO: We want non-leaky versions of all files!
