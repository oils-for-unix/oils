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


