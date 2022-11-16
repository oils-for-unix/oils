`cpp/` - Hand-written C++ Code
==============================

Structure of this directory:

Correspond to Python standard library modules:

    stdlib{.h,.cc,_test.cc}
      import fcntl
      import time
      import posix  # forked in pyext/posixmodule.c

Correspond to repo directories:

    core{.h,.cc,_test.cc}

    osh{.h,.cc,_test.cc}
      from osh import arith_parse
      from osh import bool_stat

    pylib{.h,.cc,_test.cc}
      from pylib import os_path
      from pylib import path_stat

    pgen2{.h,.cc,_test.cc}
      from pgen2 import parse

    qsn{.h,_test.cc}

Corresponds to our Python extensions:

    libc{.h,.cc,_test.cc}  # Python module pyext/libc.c

Correspond to individual files:

    core_error.h    # corresponds to core/error.py
    core_pyerror.h  # corresponds to core/pyerror.py

    # These three are separate because there is generated code associated with
    # them, like the re2c lexer.

    frontend_flag_spec{.h,.cc,_test.cc}
      from frontend import flag_spec

    frontend_match{.h,.cc,_test.cc}
      from frontend import match

    osh_tdop.{h,cc}
      from frontend import tdop

Other files:

    preamble.h           # for the big mycpp translation unit
    translation_stubs.h      

