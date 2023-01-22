---
css_files: web/base.css web/release-index.css
all_docs_url: -
version_url: -
---

Oil 0.14.0
============

<!-- NOTE: This file is published to /release/$VERSION/index.html -->

<span class="date">
<!-- REPLACE_WITH_DATE -->
</span>

This is the home page for version 0.14.0 of Oil, a Unix shell.  To use it,

1. Download a source tarball.
2. Build it and do a "smoke test", as described in [INSTALL][].

These steps take 30 to 60 seconds on most machines.  After installation, see
[Getting Started](doc/getting-started.html).

The associated **[quality page](quality.html)** shows test results, metrics,
and benchmarks.

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

The [Doc Overview](doc/) links to all docs.  Here is the subset of them that
are **ready to read**:

- [Getting Started](doc/getting-started.html)
- [FAQ on Documentation](doc/faq-doc.html).  **Look here if you can't find
  something.**
- OSH:
  - [Known Differences Between OSH and Other Shells](doc/known-differences.html)
  | [Quirks](doc/quirks.html)
  | [Tracing Execution](doc/xtrace.html)
  | [Headless Mode](doc/headless.html)
- The Oil language:
  - [A Tour of the Oil Language](doc/oil-language-tour.html)
  | [Oil vs. Shell Idioms](doc/idioms.html) and [Shell Idioms](doc/shell-idioms.html)
  | [What Breaks When You Upgrade to Oil](doc/upgrade-breakage.html)
  | [Oil Language FAQ](doc/oil-language-faq.html)  | [Egg Expressions (Oil Regexes)](doc/eggex.html)
  | [Oil Fixes Shell's Error Handling](doc/error-handling.html)
  | [Simple Word Evaluation](doc/simple-word-eval.html)
  | [Variable Declaration, Mutation, and Scope](doc/variables.html)
  | [Hay - Custom Languages for Unix Systems](doc/hay.html)
  | [Warts](doc/warts.html)
- Language Design:
  - [A Feel For Oil's Syntax](doc/syntax-feelings.html) 
  | [Syntactic Concepts](doc/syntactic-concepts.html) 
  | [Command vs. Expression Mode](doc/command-vs-expression-mode.html)
  | [Language Influences](doc/language-influences.html)
- Interchange Formats:
  - [QSN](doc/qsn.html)

More docs:

- [OSH Help Topics](doc/osh-help-topics.html) (in progress)
  | [Oil Help Topics](doc/oil-help-topics.html) (in progress).
- [Github Wiki for oilshell/oil](https://github.com/oilshell/oil/wiki).  The
  [Oil Deployments](https://github.com/oilshell/oil/wiki/Oil-Deployments) wiki
  page has other ways of getting Oil.  These versions may not be up-to-date.


