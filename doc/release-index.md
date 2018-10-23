<!-- NOTE: This file is at /release/$VERSION/index.html -->

Oil Version 0.6.pre8
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

- Lines of source, counted in differented ways:
  - [oil-osh-cloc](metrics.wwz/line-counts/oil-osh-cloc.txt).  The core of Oil,
    as measured by the [cloc][] tool.
  - [src](metrics.wwz/line-counts/src.txt).  The whole Oil repo organized by
    type of source file.
  - [parser](metrics.wwz/line-counts/parser.txt).  How big is the parser?
  - [runtime](metrics.wwz/line-counts/runtime.txt).  How big is the runtime?
- Lines of dependencies:
  - [pydeps](metrics.wwz/line-counts/pydeps.txt).  Oil code plus the Python
    standard library.
  - [nativedeps](metrics.wwz/line-counts/nativedeps.txt).  Oil code plus A
    slice of CPython.
- Bytecode Metrics
  - [overview](metrics.wwz/bytecode/overview.txt) - Compare OPy vs. CPython.
  - [oil-with-opy](metrics.wwz/bytecode/oil-with-opy.txt) - Oil compiled with
    OPy.
  - [oil-with-cpython](metrics.wwz/bytecode/oil-with-cpython.txt) - Oil
    compiled with CPython (for comparison).
  - [src-bin-ratio-with-opy](metrics.wwz/bytecode/src-bin-ratio-with-opy.txt) -
    How big is the compiled output?
- Native Code Metrics
  - [overview](metrics.wwz/native-code/overview.txt) - An analysis of GCC's
    compilation of [OVM][] (a subset of CPython).  [Bloaty][] provides the
    underlying data.
  - [cpython-defs/overview](metrics.wwz/cpython-defs/overview.txt) - We try to
    ship as little of CPython as possible, and this is what's left.

[cloc]: https://github.com/AlDanial/cloc
[Bloaty]: https://github.com/google/bloaty
[OVM]: //www.oilshell.org/cross-ref.html?tag=OVM#OVM


### Oil Tests

- [Spec Tests](test/spec.wwz/).  Test OSH behavior against that of existing
  shells.
- [Wild Tests](test/wild.wwz/).  Parsing and translating thousands of shell
  scripts with OSH.
- [Unit Tests](test/unit.wwz/).  Python unit test results.

More tests:

- [Gold Tests](test/other.wwz/gold.txt).  Comparisons against bash (using
  implicit assertions, no golden output.)
- [osh2oil Tests](test/other.wwz/osh2oil.txt).  Test the conversion of OSH to
  Oil.
- [parse-errors](test/other.wwz/parse-errors.txt).  A list of all parse errors.
- [runtime-errors](test/other.wwz/runtime-errors.txt).  A list of all runtime
  errors.
- [osh-usage](test/other.wwz/osh-usage.txt).  Misc tests of the `osh` binary.
- [oshc-deps](test/other.wwz/oshc-deps.txt).  Tests for a subcommand in
  progress.
- [arena](test/other.wwz/arena.txt).  Testing an invariant for the parser.

### OPy Tests

The OPy compiler is used to compile Oil to bytecode, but isn't itself part of
the release.

- [build-oil-repo](test/opy.wwz/build-oil-repo.txt)
- [test-gold](test/opy.wwz/test-gold.txt)
- [test-oil-unit-byterun](test/opy.wwz/test-oil-unit-byterun.txt)
- [regtest-compile](test/opy.wwz/regtest-compile.txt)
- [regtest-verify-golden](test/opy.wwz/regtest-verify-golden.txt)

Tree-shaking:

- [Symbols in Oil](test/opy.wwz/oil-symbols.txt)
- [Symbols in OPy](test/opy.wwz/opy-symbols.txt)

### Manual Tests

- [ ] Test build and install on OS X

### Benchmarks

- [OSH Parser Performance](benchmarks.wwz/osh-parser/).  How fast does OSH
  parse compared to other shells?
- [OSH Runtime](benchmarks.wwz/osh-runtime/).  How fast does OSH
  run compared to other shells?
- [Virtual Memory Baseline](benchmarks.wwz/vm-baseline/).  How much memory do
  shells use at startup?
- [OVM Build](benchmarks.wwz/ovm-build/).  How long does it take for end users
  to build Oil?  How big is the resulting binary?

<!-- - [OHeap](benchmarks.wwz/oheap/).  Metrics for a possible AST encoding format. -->

<!-- TODO: 
/src/                       annotated/cross-referenced source code
coverage/                  code coverage in Python and C
-->
