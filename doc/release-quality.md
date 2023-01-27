---
css_files: web/base.css web/toc.css web/release-index.css 
all_docs_url: -
version_url: -
---

Oil 0.14.0 Quality
=================

<!-- NOTE: This file is published to /release/$VERSION/quality.html -->

<span class="date">
<!-- REPLACE_WITH_DATE -->
</span>

This is a supplement to the [main release page](index.html).

<div id="toc">
</div>

## Test Results

### Spec Tests

- [OSH Survey](test/spec.wwz/survey/osh.html).  Test OSH with existing shells,
  and compare their behavior.
- [Stateful Tests](test/spec.wwz/stateful/index.html).  Tests that use
  [pexpect]($xref).
- [OSH in C++](test/spec.wwz/cpp/osh-summary.html).  The progress of Oil's C++
  translation.
- [Oil Language](test/spec.wwz/oil-language/oil.html).  The legacy-free
  language.

### Other Primary Suites

- [Gold Tests](test/other.wwz/gold.txt).  Compare OSH against bash (using
  implicit assertions, no golden output.)
- [Wild Tests](test/wild.wwz/).  Parse and translate thousands of shell scripts
  with OSH.
- [Python Unit Tests](test/unit.wwz/).
- [C++ Test Coverage](test/coverage.wwz/unified/html/index.html) measured by
  Clang.
  - [Log Files](test/coverage.wwz/log-files.html)

### More

- [Smoosh][] test suite (from [mgree/smoosh][]):
  - [smoosh](test/spec.wwz/survey/smoosh.html)
    | [smoosh-hang](test/spec.wwz/survey/smoosh-hang.html)
- [parse-errors](test/other.wwz/parse-errors.txt).  A list of all parse errors.
  - [parse-errors-osh-cpp](test/other.wwz/parse-errors-osh-cpp.txt).
    With the native binary.
- [runtime-errors](test/other.wwz/runtime-errors.txt).  A list of shell runtime
  errors.
- [oil-runtime-errors](test/other.wwz/oil-runtime-errors.txt).  Oil language
  runtime errors.
- [oil-large](test/other.wwz/oil-large.txt)
- [tea-large](test/other.wwz/tea-large.txt)
- [arena](test/other.wwz/arena.txt).  Testing an invariant for the parser.
- [osh-usage](test/other.wwz/osh-usage.txt).  Misc tests of the `osh` binary.
- [oshc-deps](test/other.wwz/oshc-deps.txt).  Tests for a subcommand in
  progress.
- How many processes does Oil start compared to other shells?
  - [syscall/by-code](test/other.wwz/syscall/by-code.txt)
    | [syscall/by-input](test/other.wwz/syscall/by-input.txt)
- [ysh-prettify Tests](test/other.wwz/ysh-prettify.txt).  Test OSH to YSH
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
  build Oil?  How big is the resulting binary?
- [Virtual Memory Baseline](benchmarks.wwz/vm-baseline/).  How much memory do
  shells use at startup?
- [mycpp](benchmarks.wwz/mycpp-examples/).  Compares Python and generated C++
  on small examples.
- [Memory Management Overhead](benchmarks.wwz/gc/).  How much time do we spend
  managing memory, compared with the shell interpreter?

## Metrics

- Lines of source, counted in different ways:
  - [overview](pub/metrics.wwz/line-counts/overview.html).  The whole Oil repo organized by
    type of source file.
  - [for-translation](pub/metrics.wwz/line-counts/for-translation.html).
    An overview of the "compiler engineer" project.
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

These files may help you understand how Oil is implemented, i.e. with
domain-specific languages and code generation.

- [_gen/frontend/id_kind.asdl_c.h](source-code.wwz/_gen/frontend/id_kind.asdl_c.h).
  A list of language elements, used in the lexer and in multiple parsers and
  evaluators.
- The regex-based lexer uses two stages of code generation:
  - [frontend/lexer_def.py](source-code.wwz/frontend/lexer_def.py)
    | [_build/tmp/frontend/match.re2c.txt](source-code.wwz/_build/tmp/frontend/match.re2c.txt)
    | [_gen/frontend/match.re2c.h](source-code.wwz/_gen/frontend/match.re2c.h)
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

## Old

These links describe the CPython / "[OVM]($xref)" build, which should become
the "experimental" version of Oil.

#### OPy / OVM Metrics

- Lines of dependencies:
  - [pydeps](pub/metrics.wwz/line-counts/pydeps.txt).  Oil code plus the Python
    standard library.
  - [nativedeps](pub/metrics.wwz/line-counts/nativedeps.txt).  Oil code plus a
    slice of CPython.
- Bytecode Metrics
  - [overview](pub/metrics.wwz/bytecode/overview.txt) - Compare OPy vs. CPython.
  - [oil-with-opy](pub/metrics.wwz/bytecode/oil-with-opy.txt) - Oil compiled with
    OPy.
  - [oil-with-cpython](pub/metrics.wwz/bytecode/oil-with-cpython.txt) - Oil
    compiled with CPython (for comparison).
  - [src-bin-ratio-with-opy](pub/metrics.wwz/bytecode/src-bin-ratio-with-opy.txt) -
    How big is the compiled output?
- OVM / CPython
  - [overview](pub/metrics.wwz/ovm/overview.txt) - An analysis of GCC's
    compilation of [OVM][] (a subset of CPython).  [Bloaty][] provides the
    underlying data.
  - [cpython-defs/overview](pub/metrics.wwz/cpython-defs/overview.txt) - We try to
    ship as little of CPython as possible, and this is what's left.
