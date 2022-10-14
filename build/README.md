`build/` directory
==================

A mix of old "OVM" scripts and new `oil-native` Ninja scripts.

## Old CPython Slice

Quick smoke test:

   build/old-ovm-test.sh test-oild-bundle

### Python Behavior Changes

Almost all changes remove unused code, but here is a list of behavior changes:

- `Objects/typeobject.c : type_new()` -- I commented out `_Py_Mangle`.  This
  turns `self.__foo` into something else.  That won't break my code, but it
  might break third-party code?
  - TODO: Perhaps find the corresponding compile-time time check in
    `compiler2`?

## Directory Structure

### Code

    build/
      ninja_main.py      # Invoked by ./NINJA-config.sh
      ninja_lib.py       # rules

      # TODO: rename to "steps"
      ninja-rules-py.sh
      ninja-rules-cpp.sh

    cpp/
      NINJA_subgraph.py

    mycpp/
      NINJA_subgraph.py  # This file describes dependencies programmatically
      TEST.sh            # test driver for unit tests and examples

      examples/
        cgi.py
        varargs.py
        varargs_preamble.h

### Data

    _gen/
      bin/ 
        osh_eval.mycpp.{h,cc}
      mycpp/
        examples/
          cgi.mycpp.cc
          cgi_raw.mycpp.cc
          cgi.pea.cc
          cgi_raw.pea.cc
          expr.asdl.{h,cc}

    _build/
      NINJA/  # part of the Ninja graph
        asdl.asdl_main/
          all-pairs.txt
          deps.txt

      obj/
        # The obj folder is a 2-tuple {cxx,clang}-{dbg,opt,asan ...}
        cxx-dbg/
          bin/
            osh_eval.mycpp.o
            osh_eval.mycpp.d     # dependency file
            osh_eval.mycpp.json  # when -ftime-trace is passed
          mycpp/
            gc_heap_test.o  # not translated
            gc_builtins.o   
          _gen/
            mycpp/
              examples/
                cgi.mycpp.o
                cgi.mycpp.o.d
                cgi.pea.o
                cgi.pea.o.d
                expr.asdl.o
                expr.asdl.o.d
        cxx-gcevery/
        cxx-opt/
        clang-coverage/

      preprocessed/
        cxx-dbg/
          cpp/
            leaky_stdlib.cc
        cxx-dbg.txt  # line counts

    _bin/

      # These are the code generators.  TODO: move to _bin/PORT/asdl/asdl_main
      shwrap/
        asdl_main
        mycpp_main
        lexer_gen
        ...

      # The _bin folder is a 3-tuple {cxx,clang}-{dbg,opt,asan ...}-{,sh}
      cxx-opt/
        osh_eval
        osh_eval.stripped              # The end user binary, with top_level = True
        osh_eval.symbols

        mycpp/
          examples/
            cgi.mycpp
            cgi.mycpp.stripped
            cgi.pea
            cgi.pea.stripped
          gc_heap_test

      cxx-opt-sh/                      # with shell script
        cxx-gcevery/
          mycpp/
            gc_heap_test

      clang-coverage/

    _test/
      tasks/        # *.txt and *.task.txt for .wwz
        typecheck/  # optionally run
        test/       # py, gcevery, asan, opt
        benchmark/

        # optionally logged?
        translate/
        compile/

### Python dev build

    # C code shared with the Python build
    # eventually this can be moved into Ninja
    _devbuild/
      gen/
        runtime_asdl.py
