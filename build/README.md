CPython Slice Build Steps
-------------------------

Build Python so you can dynamically discover dependencies with `app_deps.py`
and `runpy_deps.py`:

    build/prepare.sh configure
    build/prepare.sh build-python

Now invoke the top level Makefile.

    make

It will build app bundles in `_bin` and tarballs in `_release`.

Quick smoke test:

   build/test.sh hello-bundle
   build/test.sh oil-bundle

Python Behavior Changes
-----------------------

Almost all changes remove unused code, but here is a list of behavior changes:

- `Objects/typeobject.c : type_new()` -- I commented out `_Py_Mangle`.  This
  turns `self.__foo` into something else.  That won't break my code, but it
  might break third-party code?
  - TODO: Perhaps find the corresponding compile-time time check in
    `compiler2`?


