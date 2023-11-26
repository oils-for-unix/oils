---
css_files: web/base.css web/release-index.css
all_docs_url: -
version_url: -
---

Oils 0.18.0
===========

<!-- NOTE: This file is published to /release/$VERSION/index.html -->

<span class="date">
<!-- REPLACE_WITH_DATE -->
</span>

This is the home page for version 0.18.0 of Oils, a Unix shell.  To use it,

1. Download a source tarball.
2. Build it and do a "smoke test", as described in [INSTALL][].

These steps take 30 to 60 seconds on most machines.  After installation, see
[Getting Started](doc/getting-started.html).

The associated **[quality page](quality.html)** shows test results, metrics,
and benchmarks.

[INSTALL]: doc/INSTALL.html

## Download

<!-- REPLACE_WITH_DOWNLOAD_LINKS -->

Note: `oil-$VERSION` is the slow Python build, while `oils-for-unix-$VERSION`
is the new, fast C++ build.

## What's New

- Details are in the [raw git change log](changelog.html).  Not all changes
  affect the release tarball.
- I sometimes write a [release announcement](announcement.html) with a
  high-level description of changes.

## Documentation

These docs are **ready to read** (though there may be obsolete references to
"Oil" rather than "YSH"):

- [Getting Started](doc/getting-started.html)
- [FAQ on Documentation](doc/faq-doc.html).  **Look here if you can't find
  something.**
- OSH:
  - [Known Differences Between OSH and Other Shells](doc/known-differences.html)
  | [Quirks](doc/quirks.html)
  | [Tracing Execution](doc/xtrace.html)
  | [Headless Mode](doc/headless.html)
- YSH:
  - Intro: [A Tour of YSH](doc/ysh-tour.html)
  | [A Feel For YSH Syntax](doc/syntax-feelings.html) 
  | [YSH vs. Shell Idioms](doc/idioms.html) and [Shell Idioms](doc/shell-idioms.html)
  | [What Breaks When You Upgrade to YSH](doc/upgrade-breakage.html)
  | [YSH Language FAQ](doc/ysh-faq.html)
  - Comparisons: [YSH vs. Shell](doc/ysh-vs-shell.html) | [YSH Expressions vs.
    Python](doc/ysh-vs-python.html)
  - Features: [Egg Expressions (YSH Regexes)](doc/eggex.html)
  | [Guide to Procs and Funcs](doc/proc-func.html)
  | [YSH Fixes Shell's Error Handling](doc/error-handling.html)
  | [Simple Word Evaluation](doc/simple-word-eval.html)
  | [Variable Declaration, Mutation, and Scope](doc/variables.html)
  | [Hay - Custom Languages for Unix Systems](doc/hay.html)
- Language Design:
  - [Syntactic Concepts](doc/syntactic-concepts.html) 
  | [Command vs. Expression Mode](doc/command-vs-expression-mode.html)
  | [Language Influences](doc/language-influences.html)
  - Notes: [Novelties in OSH and YSH](doc/novelties.html) | [Warts](doc/warts.html)

More:

- [**All Docs**](doc/) about Oils (in progress).
- [Github Wiki for oilshell/oil](https://github.com/oilshell/oil/wiki).  The
  [Oil Deployments](https://github.com/oilshell/oil/wiki/Oil-Deployments) wiki
  page has other ways of getting Oils.  These versions may not be up-to-date.

