<!-- NOTE: This file is at /release/$VERSION/index.html -->

Oil Version 0.5
-----------------

### What's New

- The [Release announcement](announcement.html) has a high-level summary of
  changes.
- Details are in the [raw git change log](changelog.html).  Some of these
  changes may not affect the release tarball (e.g. tool changes).

### Docs For End Users

- [INSTALL](doc/INSTALL.html).  How to install OSH.  This text file is also at
  the root of the tarball.
- [OSH Quick Reference](doc/osh-quick-ref.html), with Examples (in progress).
  This document underlies the OSH `help` builtin.  It also gives a rough
  overview of what features OSH implements.

### Docs For Developers

- [Github Wiki for oilshell/oil](https://github.com/oilshell/oil/wiki)

### Metrics

- Count lines of source code in different ways:
  - [oil-osh-cloc](metrics.wwz/line-counts/oil-osh-cloc.txt).  The core of Oil,
    as measured by the [cloc][] tool.
  - [src](metrics.wwz/line-counts/src.txt).  The whole Oil repo organized by
    type of source file.
  - [parser](metrics.wwz/line-counts/parser.txt).  How big is the parser?
  - [runtime](metrics.wwz/line-counts/runtime.txt).  How big is the runtime?
- Count lines of dependencies:
  - [pydeps](metrics.wwz/line-counts/pydeps.txt).  Oil code plus the Python
    standard library.
  - [nativedeps](metrics.wwz/line-counts/nativedeps.txt).  Oil code plus A
    slice of CPython.
- [Bytecode Size](metrics.wwz/pyc-bytes.txt)

[cloc]: https://github.com/AlDanial/cloc

### Tests Results

- [Spec Tests](test/spec.wwz/).  Test OSH behavior against that of existing
  shells.
- [Wild Tests](test/wild.wwz/).  Parsing and translating thousands of shell
  scripts with OSH.
- [Unit Tests](test/unit.wwz/).  Python unit test results.
- [Gold Tests](test/gold.wwz/log.txt).  Comparisons against bash (using
  implicit assertions, no golden output.)
- [osh2oil Tests](test/osh2oil.wwz/log.txt).  Test the conversion of OSH to
  Oil.

### Benchmarks

- [OSH Parser Performance](benchmarks.wwz/osh-parser/).  How fast does OSH
  parse compared to other shells?
- [OSH Runtime](benchmarks.wwz/osh-runtime/).  How fast does OSH
  run compared to other shells?
- [Virtual Memory Baseline](benchmarks.wwz/vm-baseline/).  How much memory to
  shells use at startup?
- [OHeap](benchmarks.wwz/oheap/).  Metrics for a possible AST encoding format.
- [OVM Build](benchmarks.wwz/ovm-build/).  How long does it take for end users
  to build Oil?  How big is the resulting binary?

<!-- TODO: 
/src/                       annotated/cross-referenced source code
coverage/                  code coverage in Python and C
-->
