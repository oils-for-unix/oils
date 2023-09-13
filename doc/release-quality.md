---
css_files: web/base.css web/toc.css web/release-index.css 
all_docs_url: -
version_url: -
---

Oils 0.18.0 Quality
===================

<!-- NOTE: This file is published to /release/$VERSION/quality.html -->

<span class="date">
<!-- REPLACE_WITH_DATE -->
</span>

This is a supplement to the [main release page](index.html).

<div id="toc">
</div>

## Test Results

### Spec Tests

- [OSH Survey](test/spec.wwz/osh-py/index.html).  Test OSH with existing shells,
  and compare their behavior.
  - [OSH in C++](test/spec.wwz/osh-cpp/compare.html).  The progress of the C++
    translation.
- [YSH](test/spec.wwz/ysh-py/index.html).  The legacy-free language.
  - [YSH in C++](test/spec.wwz/ysh-cpp/compare.html).  The progress of the C++
    translation.
- [Stateful Tests](test/spec.wwz/stateful/index.html).  Tests that use
  [pexpect]($xref).

### Primary Test Suites

- [Gold Tests](more-tests.wwz/suite-logs/gold.txt).  Compare OSH with bash
  (using implicit assertions, not golden output.)
- [Wild Tests](test/wild.wwz/).  Parse and translate thousands of shell scripts
  with OSH.
- [Python Unit Tests](more-tests.wwz/unit/).
- [C++ Test Coverage](test/coverage.wwz/unified/html/index.html) measured by
  Clang.
  - [Log Files](test/coverage.wwz/log-files.html)
- [Process Table](more-tests.wwz/process-table/).  Are child processes in the
  right state for job control?

### More Tests

- [Smoosh][] test suite (from [mgree/smoosh][]):
  - [smoosh](test/spec.wwz/smoosh/smoosh.html)
    | [smoosh-hang](test/spec.wwz/smoosh/smoosh-hang.html)
- [parse-errors](more-tests.wwz/suite-logs/parse-errors.txt).  A list of all parse errors.
  - [parse-errors-osh-cpp](more-tests.wwz/suite-logs/parse-errors-osh-cpp.txt).
    With the native binary.
- [runtime-errors](more-tests.wwz/suite-logs/runtime-errors.txt).  A list of shell runtime
  errors.
- [ysh-runtime-errors](more-tests.wwz/suite-logs/ysh-runtime-errors.txt).  YSH
  runtime errors.
- [ysh-parse-errors](more-tests.wwz/suite-logs/ysh-parse-errors.txt).  YSH
  parse errors.
- [ysh-large](more-tests.wwz/suite-logs/ysh-large.txt)
- [tea-large](more-tests.wwz/suite-logs/tea-large.txt)
- [arena](more-tests.wwz/suite-logs/arena.txt).  Test an invariant of the parser.
- [osh-usage](more-tests.wwz/suite-logs/osh-usage.txt).  Misc tests of the `osh` binary.
- [tools-deps](more-tests.wwz/suite-logs/tools-deps.txt).  Tests for a subcommand in
  progress.
- How many processes does Oils start compared to other shells?
  - [syscall/by-code](more-tests.wwz/syscall/by-code.txt)
    | [syscall/by-input](more-tests.wwz/syscall/by-input.txt)
- [ysh-ify Tests](more-tests.wwz/suite-logs/ysh-ify.txt).  Test OSH to YSH
  translation.

[Smoosh]: http://shell.cs.pomona.edu/

[mgree/smoosh]: https://github.com/mgree/smoosh/tree/master/tests/shell

## Benchmarks

- [Parser](benchmarks.wwz/osh-parser/).  How fast does OSH
  parse compared to other shells?
- [Runtime](benchmarks.wwz/osh-runtime/).  How fast does OSH run shell
  scripts?
- [Compute](benchmarks.wwz/compute/).  How fast does OSH run small programs
  without I/O?
- [Build](benchmarks.wwz/ovm-build/).  How long does it take for end users to
  build Oils?  How big is the resulting binary?
- [Virtual Memory Baseline](benchmarks.wwz/vm-baseline/).  How much memory do
  shells use at startup?
- [mycpp](benchmarks.wwz/mycpp-examples/).  Compares Python and generated C++
  on small examples.
- Memory Management Overhead.  How much time do we spend managing memory,
compared with the shell interpreter?
  - [benchmarks/gc](benchmarks.wwz/gc/).  Stats from the OS and our GC runtime.
  - [benchmarks/gc-cachegrind](benchmarks.wwz/gc-cachegrind/).  Stable
    measurements.
- [uftrace](benchmarks.wwz/uftrace/).  Stable measurements for parsing and
  runtime.

## Metrics

- Lines of source, counted in different ways:
  - [overview](pub/metrics.wwz/line-counts/overview.html).  The whole Oils
    repo, organized by type of source file.
  - [for-translation](pub/metrics.wwz/line-counts/for-translation.html).  An
    overview of the "compiler engineer" project.
  - [osh-cloc](pub/metrics.wwz/line-counts/osh-cloc.txt).  OSH and common
    libraries, as measured by the [cloc][] tool.
- Generated C++ code
  - [oil-cpp](pub/metrics.wwz/line-counts/oil-cpp.txt).  The C++ code in the
    `oils-for-unix` tarball.
  - [preprocessed](pub/metrics.wwz/preprocessed/index.html).  How much code is
    passed to the compiler?
    - [cxx-dbg](pub/metrics.wwz/preprocessed/cxx-dbg.txt),
      [cxx-opt](pub/metrics.wwz/preprocessed/cxx-opt.txt)
  - [Binary code size](pub/metrics.wwz/oils-for-unix/index.html) reported by
    [Bloaty][].  How much code is output by the compiler?
    - [overview](pub/metrics.wwz/oils-for-unix/overview.txt),
      [symbols](pub/metrics.wwz/oils-for-unix/symbols.txt)


[cloc]: https://github.com/AlDanial/cloc
[Bloaty]: https://github.com/google/bloaty
[OVM]: //www.oilshell.org/cross-ref.html?tag=OVM#OVM

## Source Code

These files may help you understand how Oils is implemented, i.e. with
domain-specific languages and code generation.

- [_gen/frontend/id_kind.asdl_c.h](pub/src-tree.wwz/_gen/frontend/id_kind.asdl_c.h.html).
  A list of language elements, used in the lexer and in multiple parsers and
  evaluators.
- The regex-based lexer uses two stages of code generation:
  - [frontend/lexer_def.py](pub/src-tree.wwz/frontend/lexer_def.py.html)
    | [_build/tmp/frontend/match.re2c.txt](pub/src-tree.wwz/_build/tmp/frontend/match.re2c.txt.html)
    | [_gen/frontend/match.re2c.h](pub/src-tree.wwz/_gen/frontend/match.re2c.h)
- [frontend/syntax.asdl](pub/src-tree.wwz/frontend/syntax.asdl.html). The syntax tree
  for OSH and YSH.
- [ysh/grammar.pgen2](pub/src-tree.wwz/ysh/grammar.pgen2.html). The
  expression grammar for YSH.  In contrast, the OSH parsers are hand-written.

Also see the [oilshell/oil](https://github.com/oilshell/oil) repository.

## Old

These links describe the CPython / "[OVM]($xref)" build, which should become
the "experimental" version of Oils.

#### OPy / OVM Metrics

- Lines of dependencies:
  - [pydeps](pub/metrics.wwz/line-counts/pydeps.txt).  Oils code plus the Python
    standard library.
  - [nativedeps](pub/metrics.wwz/line-counts/nativedeps.txt).  Oils code plus a
    slice of CPython.
- Bytecode Metrics
  - [overview](pub/metrics.wwz/bytecode/overview.txt) - Compare OPy vs. CPython.
  - [oil-with-opy](pub/metrics.wwz/bytecode/oil-with-opy.txt) - Oils compiled with
    OPy.
  - [oil-with-cpython](pub/metrics.wwz/bytecode/oil-with-cpython.txt) - Oils
    compiled with CPython (for comparison).
  - [src-bin-ratio-with-opy](pub/metrics.wwz/bytecode/src-bin-ratio-with-opy.txt) -
    How big is the compiled output?
- OVM / CPython
  - [overview](pub/metrics.wwz/ovm/overview.txt) - An analysis of GCC's
    compilation of [OVM][] (a subset of CPython).  [Bloaty][] provides the
    underlying data.
  - [cpython-defs/overview](pub/metrics.wwz/cpython-defs/overview.txt) - We try to
    ship as little of CPython as possible, and this is what's left.
