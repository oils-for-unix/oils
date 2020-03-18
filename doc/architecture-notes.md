Notes on OSH Architecture
=========================

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

## Source Code

[README](README.html) describes how the code is organized.

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
- See [build/dev.sh]($oil-src) and [build/codegen.sh]($oil-src)


## Lexing

Note: This article is more polished and covers some of the material in the
next two sections: [How to Parse Shell Like a Programming
Language][parse-shell].

[parse-shell]: https://www.oilshell.org/blog/2019/02/07.html


### List of Regex-Based Lexers

Oil uses regex-based lexers, which are turned into efficient C code with
[re2c]($xref).  We intentionally avoid hand-written code that manipulates
strings char-by-char, since that strategy is error prone; it's inevitable that
rare cases will be mishandled.

The list of lexers can be found by looking at [native/fastlex.c]($oil-src).

- The large, modal OSH/Oil lexer in [frontend/lexer_def.py]($oil-src).
- Lexers for OSH sublanguages
  - For `echo -e`
  - For `PS1` backslash escapes.
  - For history expansion, e.g. `!$`.
  - For globs, to implement `${x/foo*/replace}` via conversion to ERE.  We need
    position information, and the `fnmatch()` API doesn't provide it, but
    `regexec()` does.
    - NOTE: We'll also need one for converting extended globs to EREs, for
      portability.

[re2c]: http://re2c.org/

### Sublanguages We Don't Lex or Parse

These constructs aren't recognized by Oil's front end.  Instead, they're punted
to [libc]($xref):

- Glob patterns, e.g. `*.py` (in most cases)
- Extended glob patterns, e.g. `@(*.py|*.sh)`
- `strftime` format strings, e.g. `printf '%(%Y-%m-%d)T' $timestamp`

### Lexer Unread

[osh/word_parse.py]($oil-src) calls `lexer.MaybeUnreadOne()` to handle right
parens in this case:

```
(case x in x) ;; esac )
```

This is sort of like the `ungetc()` I've seen in other shell lexers.

## Parsing Issues

This section is about extra passes ("irregularities") at **parse time**.  In
the "Runtime Issues" section below, we discuss cases that involve parsing after
variable expansion, etc.

### Where We Parse More Than Once (statically, and unfortunately)

This makes it harder to produce good error messages with source location info.
It also implications for translation, because we break the "arena invariant".

(1) **Array L-values** like `a[x+1]=foo`.  bash allows splitting arithmetic
expressions across word boundaries: `a[x + 1]=foo`.  But I don't see this used,
and it would significantly complicate the OSH parser.

(in `_MakeAssignPair` in `osh/cmd_parse.py`)

(2) **Backticks**.  There is an extra level of backslash quoting that may
happen compared with `$()`.

(in `_ReadCommandSubPart` in `osh/word_parse.py`)

### Where We Read More Than Once (`VirtualLineReader`)

- [Here documents]($xref:here-doc):  We first read lines, and then parse them.
- [alias]($help) expansion

### Extra Passes Over the LST

These are handled up front, but not in a single pass.

- Assignment vs. Env binding detection: `FOO=bar declare a[x]=1`.
  We make another pass with `_SplitSimpleCommandPrefix()`.
  - Related: `s=1` doesn't cause reparsing, but `a[x+1]=y` does.
- Brace Detection in a few places: `echo {a,b}`
- Tilde Detection: `echo ~bob`, `home=~bob`

### Lookahead in Recursive Descent Parsers

- `myfunc() { echo hi; }` vs.  `myfunc=()  # an array`
- `shopt -s parse_equals`: For `x = 1 + 2*3`

### Where the Arena Invariant is Broken

- Here docs with `<<-`.  The leading tab is lost, because we don't need it for
  translation.

### Where Parsers are Instantiated

- See [frontend/parse_lib.py]($oil-src) and its callers.

## Runtime Parsing

### Where OSH Dynamically Parses

1. **Alias expansion** like `alias foo='ls | wc -l'`.  Aliases are like
"lexical macros".
2. **Prompt strings**.  `$PS1` and family first undergo `\` substitution, and
then the resulting strings are parsed as words, with `$` escaped to `\$`.
3. **Builtins**.
   - `eval` 
   - `trap` builtin
     - exit
     - debug
     - err
     - signals
   - `source` — the filename is formed dynamically, but the code is generally
     static.

### Where Bash Dynamically Parses (perhaps unintentionally)

All of the cases above, plus:

(1) Recursive **Arithmetic Evaluation**:

```sh-prompt
$ a='1+2'
$ b='a+3'
$ echo $(( b ))
6
```

This also happens for the operands to `[[ x -eq x ]]`.

Note that `a='$(echo 3)'` results in a **syntax error**.  I believe this was
due to the ShellShock mitigation.

(2) The **`unset` builtin** takes an LValue.  (not yet implemented in OSH)

```sh-prompt
$ a=(1 2 3 4)
$ expr='a[1+1]'
$ unset "$expr"
$ argv "${a[@]}"
['1', '2', '4']
```

(3) **printf -v** takes an "LValue".

(4) **Var refs** with `${!x}` takes a "cell".  (not yet implemented OSH.
Relied on by `bash-completion`, as discovered by Greg Price)

```sh-prompt
$ a=(1 2 3 4)
$ expr='a[$(echo 2 | tee BAD)]'
$ echo ${!expr}
3
$ cat BAD
2
```

(5) **test -v** takes a "cell".

(6) ShellShock (removed from bash): `export -f`, all variables were checked for
a certain pattern.

### Parse Errors at Runtime (Need Line Numbers)

- `test` / `[`, e.g. `[ -a -a -a ]`
- Command line flag usage errors
- [alias]($help) parse errors

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
- compadjust needs to split partial `argv` by user-defined delimiters, e.g.
  `:=`
- TODO: Model the prompt and completion as a state machine (?)

<!-- Another good example: vtparse. -->

The point of a state machine is to make sure all cases are handled!

## Other Topics

- [Dependency Injection]($xref:dependency-injection)

## Links

- [README](README.html) describes how the code is organized.
- [Data Model](data-model.html) describes the interpreter's user-facing data
  structures.
- [OSH Word Evaluation Algorithm][word-eval] on the wiki

[word-eval]: https://github.com/oilshell/oil/wiki/OSH-Word-Evaluation-Algorithm
