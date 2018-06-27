Zephyr ASDL
-----------

This directory contains an implementation of Zephyr ASDL.  It consists of these components:

- `asdl.py`: the ASDL schema parser, borrowed from Python
  (`Python-3.5.2/Parser/asdl.py`)
- `py_meta.py`: library to dynamically generate Python classes (using
  metaclasses)
- `encode.py`: library to encode ASDL data structures in `oheap` format (to be
  described later)
- `gen_cpp.py`: tool to generate C++ code to read the `oheap` format

This library will be used for serializing parsed `osh` and `oil` code.

The files `arith_parse.py`, `arith.asdl`, `arith_ast.py`, and `arith_demo.cc`
are an end-to-end demo, driven by `run.sh`.

For more on Zephyr ASDL, see [this blog post](http://www.oilshell.org/blog/2016/12/11.html).

OHeap
-----

This is an experimental serialization of ASDL data structures.  See [What is
OHeap?](http://www.oilshell.org/blog/2017/01/09.html)

On Ubuntu:

    build/codegen.sh download-clang     
    build/codegen.sh extract-clang     

    # encodes and decodes arithmetic AST
    asdl/run.sh asdl-arith-oheap

    # encodes and decodes the OSH "lossless syntax tree"
    asdl/run.sh osh-demo

(NOTE: We probably shouldn't require Clang for this?  It's only necessary for
ASAN, clang-format, build time benchmarking, runtime benchmarking vs. GCC,
etc.)


### OHeap Use Cases:

- To freeze OSH LSTs (instances of types in `osh.asdl`)
  - This isn't necessary if the parser is fast enough (which is desirable)
- To freeze Python / OPy bytecode, and associated constants
  - Special case: ASDL reflection data for `osh.asdl`, so we can pretty
    print them
