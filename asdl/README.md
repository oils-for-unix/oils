Zephyr ASDL
-----------

This directory contains an implementation of Zephyr ASDL.  It consists of these components:

- `asdl.py`: the ASDL schema parser, borrowed from Python
  (`Python-3.5.2/Parser/asdl.py`)
- `py_meta.py`: library to dynamically generated Python classes (using
  metaclasses)
- `encode.py`: library to encode ASDL data structures in `oheap` format (to be
  described later)
- `gen_cpp.py`: tool to generate C++ code to read the `oheap` format

This directory also has some tests and demos.
