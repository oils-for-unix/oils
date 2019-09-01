<!-- NOTE: This file is at /release/$VERSION/index.html -->

Oil 0.7.pre4
---------

<span class="date">
<!-- REPLACE_WITH_DATE -->
</span>

This is the home page for version 0.7.pre4 of Oil, a Unix shell.  To use it,

1. Download a source tarball.
2. Build and install it, as described in [INSTALL][].

These steps take 30 to 60 seconds on most machines.  After that, you can
assemble an `oshrc` file, which is described in [the
manual](doc/osh-manual.html).

Test results, metrics, and benchmarks are shown below.

[INSTALL]: doc/INSTALL.html

### Download

<!-- REPLACE_WITH_DOWNLOAD_LINKS -->

### What's New

- Details are in the [raw git change log](changelog.html).  Not all changes
  affect the release tarball.
- I sometimes write a [release announcement](announcement.html) with a
  high-level description of changes.

### Documentation

- [INSTALL][]: How do I install Oil?  This text file is also in the tarball.
- [OSH User Manual](doc/osh-manual.html): How do I use it?
  - [Known Differences](doc/known-differences.html) is trivia for advanced
    users.  It lists differences between Oil and other shells.
  - [OSH Quick Reference](doc/osh-quick-ref.html), with examples (incomplete).
    This document underlies the `help` builtin, and gives a rough overview of
    what features OSH implements.
- [Github Wiki for oilshell/oil](https://github.com/oilshell/oil/wiki)
  - The [Oil Deployments](https://github.com/oilshell/oil/wiki/Oil-Deployments)
    wiki page has other ways of getting Oil.  These versions may not be
    up-to-date.


### Metrics

- Lines of source, counted in differented ways:
  - [osh-cloc](metrics.wwz/line-counts/osh-cloc.txt).  OSH and common
    libraries, as measured by the [cloc][] tool.
  - [src](metrics.wwz/line-counts/src.txt).  The whole Oil repo organized by
    type of source file.
  - [OPy](metrics.wwz/line-counts/opy.txt).  How much code is in the OPy
    toolchain?
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
- [arena](test/other.wwz/arena.txt).  Testing an invariant for the parser.
- [osh-usage](test/other.wwz/osh-usage.txt).  Misc tests of the `osh` binary.
- [oshc-deps](test/other.wwz/oshc-deps.txt).  Tests for a subcommand in
  progress.
- [opyc](test/other.wwz/opyc.txt).  Tests for the opyc tool.
- [Smoosh][] test suite (from [mgree/smoosh][]):
  - [smoosh](test/spec.wwz/smoosh.html)
  - [smoosh-hang](test/spec.wwz/smoosh-hang.html)

[Smoosh]: http://shell.cs.pomona.edu/

[mgree/smoosh]: https://github.com/mgree/smoosh/tree/master/tests/shell

### OPy Tests

The OPy compiler is used to compile Oil to bytecode, but isn't itself part of
the release.

- [build-oil-repo](test/opy.wwz/build-oil-repo.txt)
- [test-gold](test/opy.wwz/test-gold.txt)
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
