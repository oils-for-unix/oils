pgen-native
===========

# Overview

This work in progress is an attempt to factor pgen out of python.

Right now, it's just the c-based parser runtime from python2, with the
original hard-coded grammar, plus some minor tweaks to get it to build
and run independently of the python codebase.

## Usage

Run all commands from within the `pgen-native` source tree.

To rebuild and run all the tests:

```
$ make
```

### Build


```
$ make all
```

### Run The Tests

```
./test
```

### Clean

```
make clean
```
