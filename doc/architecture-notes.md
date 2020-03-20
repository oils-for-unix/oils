---
in_progress: true
---

Notes on Oil's Architecture
===========================

<style>
/* override language.css */
.sh-command {
  font-weight: unset;
}
</style>

This doc is for contributors or users who want to understand the Oil codebase.
These internal details are subject to change.

<div id="toc">
</div>

## Links

- [Contributing][] (wiki) helps you change the code for the first time.
- [README](README.html) describes how the code is organized.
- [Interpreter State](interpreter-state.html) describes the interpreter's user-facing data
  structures.
- [Parser Architecture](parser-architecture.html)
- [OSH Word Evaluation Algorithm][word-eval] (wiki) describes shell's complex
  word evaluation.  Oil uses [Simple Word Evaluation](simple-word-eval.html)
  instead.

[Contributing]: https://github.com/oilshell/oil/wiki/Contributing
[word-eval]: https://github.com/oilshell/oil/wiki/OSH-Word-Evaluation-Algorithm

## Source Code

### Build Dependencies

- Essential: [libc]($xref)
- Optional: GNU [readline]($xref) (TODO: other line editing libraries).
- Only in the OVM build (as of March 2020): [yajl]($xref)

### Borrowed Code

- [ASDL]($oil-src:asdl/) front end from [CPython]($xref:cpython) (heavily
  refactored)
- [frontend/tdop.py]($oil-src): Adapted from tinypy, but almost no original code
  remains
- [pgen2]($oil-src:pgen2/)
- All of OPy (will be obsolete)
  - compiler2 from stdlib
  - byterun
- Build Dependency: [MyPy]($xref:mypy)

### Metaprogramming / Generated Code

- Try `ls */*_def.py */*_gen.py`
  - The `def.py` files are abstract definitions.  They're not translated by
    [mycpp]($xref).
  - The `gen.py` files generate source code in Python and C++ from these
    definitions.
  - For example, we define the core `Id` type and the lexing rules abstractly.
  - *TODO: Details on each `def` / `gen` pair*.
- See [build/dev.sh]($oil-src) and [build/codegen.sh]($oil-src)


## Other Cross-Cutting Observations

### Where $IFS is Used

- Splitting of unquoted substitutions
- The [read]($help) builtin
- To split words in `compgen -W` (bash only)

### Shell Function Callbacks

- Completion hooks registered by `complete -F ls_complete_func ls`
- bash has a `command_not_found` hook; OSH doesn't yet

### Where Unicode is Respected

See the doc on [Unicode](unicode.html).

### Parse-time and Runtime Pairs

In OSH:

- `echo -e '\x00\n'` and `echo $'\x00\n'` (OSH shares lexer rules between them)
- `test` / `[` and `[[` (OSH shares the parser and evaluator)
- Static vs. Dynamic Assignment.  `local x=$y` vs. `s='x=$y'; local $s`.
  - All shells have both notions!

Other Pairs:

- `expr` and `$(( ))` (`expr` not in shell)
- Later:
  - [printf]($help) can have a static variant like `${myfloat %.3f}`
  - `find` and our own language (although this may be done with blocks)

## State Machines

- `$IFS` splitting in `osh/split.py`
- [compadjust]($help) needs to split partial `argv` by user-defined delimiters,
  e.g.  `:=`

The point of a state machine is to make sure all cases are handled!

<!-- 
Idea:
- Model the prompt state and completion as a state machine (?)
- vtparse is another good example
-->

## Other Topics

- [Dependency Injection]($xref:dependency-injection)

