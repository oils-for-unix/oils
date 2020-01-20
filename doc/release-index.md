---
css_files: web/base.css web/release-index.css
all_docs_url: -
version_url: -
---

Oil 0.7.0
============

<!-- NOTE: This file is published to /release/$VERSION/index.html -->

<span class="date">
<!-- REPLACE_WITH_DATE -->
</span>

This is the home page for version 0.7.0 of Oil, a Unix shell.  To use it,

1. Download a source tarball.
2. Build and install it, as described in [INSTALL][].

These steps take 30 to 60 seconds on most machines.  After that, you can
assemble an `oshrc` file, which is described in [the
manual](doc/osh-manual.html).

Test results, metrics, and benchmarks are shown below.

[INSTALL]: doc/INSTALL.html

## Download

<!-- REPLACE_WITH_DOWNLOAD_LINKS -->

Note: `oil-native` is a **preview** release, not a working shell.

## What's New

- Details are in the [raw git change log](changelog.html).  Not all changes
  affect the release tarball.
- I sometimes write a [release announcement](announcement.html) with a
  high-level description of changes.

## Documentation

Oil has three major sources of docs:

- The [Doc Overview](doc/) links to all other docs, including the Manual and
  Oil Language Reference.  It's work in progress.  Up-to-date docs include:
  - [INSTALL][]
  - [OSH User Manual](doc/osh-manual.html)
  - [Known Differences Between OSH and Other
    Shells](doc/known-differences.html)
  - [Egg Expressions (Oil Regexes)](doc/eggex.html)
  - [JSON Support](doc/json.html)
- [Github Wiki for oilshell/oil](https://github.com/oilshell/oil/wiki)
  - The [Oil Deployments](https://github.com/oilshell/oil/wiki/Oil-Deployments)
    wiki page has other ways of getting Oil.  These versions may not be
    up-to-date.

## Metrics

- Lines of source, counted in different ways:
  - [osh-cloc](metrics.wwz/line-counts/osh-cloc.txt).  OSH and common
    libraries, as measured by the [cloc][] tool.
  - [src](metrics.wwz/line-counts/src.txt).  The whole Oil repo organized by
    type of source file.
  - [oil-cpp](metrics.wwz/line-counts/oil-cpp.txt).  The C++ code in the
    `oil-native` tarball.
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
- OVM / CPython
  - [overview](metrics.wwz/ovm/overview.txt) - An analysis of GCC's
    compilation of [OVM][] (a subset of CPython).  [Bloaty][] provides the
    underlying data.
  - [cpython-defs/overview](metrics.wwz/cpython-defs/overview.txt) - We try to
    ship as little of CPython as possible, and this is what's left.
- `oil-native`.  The future of Oil is pure native code.
  - [overview](metrics.wwz/oil-native/overview.txt) - Binary code size reported
    by [Bloaty][].

[cloc]: https://github.com/AlDanial/cloc
[Bloaty]: https://github.com/google/bloaty
[OVM]: //www.oilshell.org/cross-ref.html?tag=OVM#OVM

## Tests

### Main Test Suites

- [Oil Spec Tests](test/spec.wwz/oil.html).  Test new Oil language features.
- [OSH Spec Tests](test/spec.wwz/osh.html).  Test OSH with existing shells, and
  compare their behavior.
- [Wild Tests](test/wild.wwz/).  Parse and translate thousands of shell scripts
  with OSH.
- [Unit Tests](test/unit.wwz/).  Python unit test results.

### Other Suites

- [Gold Tests](test/other.wwz/gold.txt).  Compare OSH against bash (using
  implicit assertions, no golden output.)
- [osh2oil Tests](test/other.wwz/osh2oil.txt).  Test the conversion of OSH to
  Oil.
- [parse-errors](test/other.wwz/parse-errors.txt).  A list of all parse errors.
  - [parse-errors-oil-native](test/other.wwz/parse-errors-oil-native.txt).
    With the native binary.
- [runtime-errors](test/other.wwz/runtime-errors.txt).  A list of shell runtime
  errors.
- [oil-runtime-errors](test/other.wwz/oil-runtime-errors.txt).  Oil language
  runtime errors.
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

### For OPy

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

## Benchmarks

- [OSH Parser Performance](benchmarks.wwz/osh-parser/).  How fast does OSH
  parse compared to other shells?
- [OSH Runtime](benchmarks.wwz/osh-runtime/).  How fast does OSH
  run compared to other shells?
- [Virtual Memory Baseline](benchmarks.wwz/vm-baseline/).  How much memory do
  shells use at startup?
- [OVM Build](benchmarks.wwz/ovm-build/).  How long does it take for end users
  to build Oil?  How big is the resulting binary?

## Source Code

These files may help you understand how Oil is implemented, i.e. with
domain-specific languages and code generation.

- [_devbuild/gen/id.h](source-code.wwz/_devbuild/gen/id.h). A list of language
  elements, used in the lexer and in multiple parsers and evaluators.
- The regex-based lexer uses two stages of code generation:
  - [frontend/lex.py](source-code.wwz/frontend/lex.py)
  - [_devbuild/tmp/osh-lex.re2c.h](source-code.wwz/_devbuild/tmp/osh-lex.re2c.h)
  - [_devbuild/gen/osh-lex.h](source-code.wwz/_devbuild/gen/osh-lex.h)
- [frontend/syntax.asdl](source-code.wwz/frontend/syntax.asdl). The syntax tree
  for OSH and Oil.
- [oil_lang/grammar.pgen2](source-code.wwz/oil_lang/grammar.pgen2). The
  expression grammar for Oil.  In contrast, the OSH parsers are hand-written.

Also see the [oilshell/oil](https://github.com/oilshell/oil) repository.

<!-- - [OHeap](benchmarks.wwz/oheap/).  Metrics for a possible AST encoding format. -->

<!-- TODO: 
/src/                       annotated/cross-referenced source code
coverage/                  code coverage in Python and C
-->
