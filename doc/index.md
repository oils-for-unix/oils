---
in_progress: yes
all_docs_url: -
---

All Docs
========

Oils is **our upgrade path from bash** to a better language and runtime.  This
page links to all the documentation.

<div id="toc">
</div>

&dagger; means a doc is not ready to read yet.

## Preliminaries

- [INSTALL](INSTALL.html). How do I install Oils?  This text file is also in the
  tarball.  <!-- TODO: C++ tarball -->
- [Getting Started](getting-started.html).  How do I use the shell?
- [FAQ on Documentation](faq-doc.html).  **Look here if you can't find
  something**.

## Reference

Like many other docs, the reference is still in progress:

- [Oils Reference](ref/index.html) &dagger; - These docs underlie `help` builtin, and
  are also published online.
- Links to topics within each chapter:
  - [OSH Table of Contents](ref/toc-osh.html) &dagger;
  - [YSH Table of Contents](ref/toc-ysh.html) &dagger;
  - [Data Notation Table of Contents](ref/toc-data.html) &dagger;
- [Style Guide](style-guide.html) gives coding recommendations.

## Interactive Shell

- [Headless Mode](headless.html).  For alternative UIs on top of YSH.
- [Completion](completion.html) &dagger;.  We emulate bash completion.

## OSH is a Compatible Shell

These docs are for advanced users:

- [Known Differences Between OSH and Other Shells](known-differences.html)
- [OSH Quirks](quirks.html) for compatibility.
- [Shell Language Idioms](shell-idioms.html) has some advice for using any
  shell, not just Oils.

## YSH is a Shell with Structured Data

- [A Tour of YSH](ysh-tour.html).  Explains YSH from scratch, without referring
  to shell's legacy.
- [What Breaks When You Upgrade to YSH](upgrade-breakage.html).  When you turn
  on YSH, there are some shell constructs you can no longer use.  We try to
  minimize the length of this list.
- [YSH Language FAQ](ysh-faq.html).  Common questions about the
  language.

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

Crosscutting design issues:

- [Guide to Procs and Funcs](proc-func.html)
  - [Block Literals](block-literals.html) &dagger;
- [Variable Declaration, Mutation, and Scope](variables.html)
- [Strings: Quotes, Interpolation, Escaping, and Buffers](strings.html) &dagger;
  - [Unicode](unicode.html) &dagger;.  Oils supports and prefers UTF-8.
- [YSH I/O Builtins](io-builtins.html) &dagger;

<!-- TODO: proc-func.html -- Informal guide to procs and funcs -->

## Data Languages Avoid Ad-Hoc Parsing

YSH programs "talk about" these data languages, also called interchange formats
or protocols.  In-memory data structures are *in service* of data languages on
the wire, **not** the other way around.

- [J8 Notation](j8-notation.html).  An upgrade of JSON to bytes, strings,
  lines, and structured data.
  - [JSON](json.html).  Some usage details.
  - [Framing](framing.html)

TODO:

- Packle &dagger;

## The Shared Oils Runtime

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

- [README.md](README.html).  If you want to modify Oils, start here.  We
  welcome contributions!
- [Doc Toolchain](doc-toolchain.html) and [Doc Plugins](doc-plugins.html).
- [Github Wiki for oilshell/oil](https://github.com/oilshell/oil/wiki)
- [Old Docs](old/index.html).  Drafts that may be deleted.

Internal Architecture:

- [Notes on Oils Architecture](architecture-notes.html)
  - [Parser Architecture](parser-architecture.html)

## More

- [Github Wiki for oilshell/oil](https://github.com/oilshell/oil/wiki).
- [The blog](https://www.oilshell.org/blog/) has useful background information,
  although older posts are more likely to have incorrect information.
- [The home page](https://www.oilshell.org/) has links to docs for new users.

<!-- vim: set sw=2: -->
