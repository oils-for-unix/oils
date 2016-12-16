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

