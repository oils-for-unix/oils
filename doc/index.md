---
in_progress: yes
all_docs_url: -
---

All Docs
========

This page links to all docs.  A dagger &dagger; means a doc isn't finished.

See [Published Docs](published.html) for those that are ready to read.


<!--
<div id="toc">
</div>
-->

## Good Places to Start

- [A Tour of YSH](ysh-tour.html)
- [YSH vs. Shell Idioms](idioms.html) 
- [**Oils Reference**](ref/index.html) - underlies the [help][] builtin
- [FAQ on Docs](faq-doc.html).  **Look here if you can't find
  something**.

[help]: ref/chap-builtin-cmd.html#help

## Preliminaries

- [INSTALL](INSTALL.html). How do I install Oils?  This text file is also in
  the `oils-for-unix` tarball.
  - [Oils Build `--help` Mirror](help-mirror.html)
  - [Portability](portability.html)
- [Getting Started](getting-started.html).  How do I use the shell?

## Interactive Shell

- [Headless Mode](headless.html).  For alternative UIs on top of YSH.
- [Completion](completion.html) &dagger;.  We emulate bash completion.

## OSH is a Compatible Shell

- [Shell Language Idioms](shell-idioms.html) has some advice for using any
  shell, not just Oils.
- [OSH Standard Library](lib-osh.html) &dagger;.  Small but useful enhancements.

For sophisticated users:

- [Known Differences Between OSH and Other Shells](known-differences.html)
- [OSH Quirks](quirks.html) for compatibility.

## YSH is a New, Powerful Shell

- [A Tour of YSH](ysh-tour.html).  Explains YSH from scratch, without referring
  to shell's legacy.
- [What Breaks When You Upgrade to YSH](upgrade-breakage.html).  When you turn
  on YSH, there are some shell constructs you can no longer use.  We try to
  minimize the length of this list.
- [YSH Language FAQ](ysh-faq.html)
- [YSH Style Guide](style-guide.html)

### Comparisons

- [YSH vs. Shell Idioms](idioms.html).  A list of code snippets.
- [YSH vs. Shell](ysh-vs-shell.html).  High-level descriptions: how does YSH
  differ from Bourne/POSIX shell?
- [YSH Expressions vs. Python](ysh-vs-python.html).  The expression language is
  borrowed from Python, with a few tweaks.
- [Novelties in OSH and YSH](novelties.html).  May be helpful for experienced
  programmers.

### Design Concepts

- [YSH Language Influences](language-influences.html) - Shell, Python,
  JavaScript, Lisp, ...
- Syntax
  - [A Feel For YSH Syntax](syntax-feelings.html)
  - [Syntactic Concepts](syntactic-concepts.html) may help you remember the
    language.
  - [Command vs. Expression Mode](command-vs-expression-mode.html).
- [Warts](warts.html).  Mostly for compatibility.

YSH has 3 main sublanguages:

- **Command** language, which now consistently uses `{ }` for blocks.
  - [Hay - Custom Languages for Unix Systems](hay.html).  Use Ruby-like
    blocks to declare data and interleaved code.
- **Word** language.
  - [Simple Word Evaluation](simple-word-eval.html).  Written for shell
    experts.
- **Expression** language on typed data.
  - [Egg Expressions](eggex.html).  A new regex syntax, abbreviated *eggex*.
  - [YSH Regex API](ysh-regex-api.html).  Convenient and powerful.

Features:

- [Guide to YSH Error Handling](ysh-error.html)
- [Guide to Procs and Funcs](proc-func.html)
  - [Block Literals](block-literals.html) &dagger;

Designs for "Maximalist YSH":

- [Streams, Tables, and Processes - awk, R, xargs](stream-table-process.html) &dagger;
- [Document Processing in YSH - Notation, Query, Templating](ysh-doc-processing.html) &dagger;


Crosscutting design issues:

- [Variable Declaration, Mutation, and Scope](variables.html)
- [Strings: Quotes, Interpolation, Escaping, and Buffers](strings.html) &dagger;
  - [Unicode](unicode.html) &dagger;.  Oils supports and prefers UTF-8.
- [YSH I/O Builtins](io-builtins.html) &dagger;

## Data Languages Avoid Ad-Hoc Parsing

YSH programs "talk about" these data languages, also called interchange formats
or protocols.  In-memory data structures are *in service* of data languages on
the wire, **not** the other way around.

- [J8 Notation](j8-notation.html).  An upgrade of JSON to bytes, strings,
  lines, and structured data.
  - [JSON](json.html).  Some usage details.
  - [Framing](framing.html) &dagger;
- [BYO Protocols](byo.html) - for testing and completion.

## The Shared Oils Runtime

- [Types in the Oils Runtime](types.html)
- [Pure Mode: For Config Files and Functions](pure-mode.html)
- [YSH Fixes Shell's Error Handling (`errexit`)](error-handling.html)
- [Oils Error Catalog, With Hints](error-catalog.html)
- [Tracing Execution](xtrace.html).  YSH enhances shell's `set -x`.
- [Options](options.html) &dagger;.  Parsing and runtime options turn OSH into YSH.

Internal details:

- [Interpreter State](interpreter-state.html) &dagger;.  What's inside a shell
  interpreter?
- [Process Model](process-model.html) &dagger;.  The shell language is a thin
  layer over the Unix kernel.

## For Contributors

- [README.md](oils-repo/README.html).  If you want to modify Oils, start here.
  We welcome contributions!
- [Oils Repo Overview](repo-overview.html)
- [Doc Toolchain](doc-toolchain.html) and [Doc Plugins](doc-plugins.html).
  - [ul-table: Markdown Tables Without New Syntax](ul-table.html)
- [Github Wiki for oilshell/oil](https://github.com/oilshell/oil/wiki)
- [Old Docs](old/index.html).  Drafts that may be deleted.

Internal Architecture:

- [Notes on Oils Architecture](architecture-notes.html)
  - [Parser Architecture](parser-architecture.html)
- [Pretty Printing](pretty-printing.html) - March 2024 design notes.
- [mycpp/README](oils-repo/mycpp/README.html) - How we translate typed Python to
  C++.

## More

- [Github Wiki for oilshell/oil](https://github.com/oilshell/oil/wiki).
- [The blog](https://www.oilshell.org/blog/) has useful background information,
  although older posts are more likely to have incorrect information.
- [The home page](https://www.oilshell.org/) has links to docs for new users.

Old:

- [INSTALL-old](INSTALL-old.html) for the slow `oil-$VERSION` tarball, based on
  CPython.

<!-- vim: set sw=2: -->
