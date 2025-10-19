Parser Architecture
===================

This doc has rough notes on the architecture of the parser.

[How to Parse Shell Like a Programming Language][parse-shell] (2019 blog post)
covers some of the same material.  (As of 2024, it's still pretty accurate,
although there have been minor changes.)

<div id="toc">
</div>

## The Lossless Invariant

The test suite [test/lossless.sh]($oils-src) invokes `osh --tool lossless-cat
$file`.

The `lossless-cat` tool does this:

1. Parse the file
1. Collect **all** tokens, from 0 to N
1. Print the text of each token.

Now, do the tokens "add up" to the original file?  That's what we call the
*lossless invariant*.

It will be the foundation for tools that statically understand shell:

- `--tool ysh-ify` - change style of `do done` &rarr; `{ }`, etc.
- `--tool fmt` - fix indentation, maybe some line wrapping

The sections on **re-parsing** explain some obstacles which we had to overcome.

## Lexing

[parse-shell]: https://www.oilshell.org/blog/2019/02/07.html

### List of Regex-Based Lexers

Oils uses regex-based lexers, which are turned into efficient C code with
[re2c]($xref).  We intentionally avoid hand-written code that manipulates
strings char-by-char, since that strategy is error prone; it's inevitable that
rare cases will be mishandled.

The list of lexers can be found by looking at [pyext/fastlex.c]($oils-src).

- The large, modal OSH/YSH lexer in [frontend/lexer_def.py]($oils-src).
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

These constructs aren't recognized by the Oils front end.  Instead, they're
punted to [libc]($xref):

- Glob patterns, e.g. `*.py` (in most cases)
- Extended glob patterns, e.g. `@(*.py|*.sh)`
- `strftime` format strings, e.g. `printf '%(%Y-%m-%d)T' $timestamp`

### Lexer Unread

[osh/word_parse.py]($oils-src) calls `lexer.MaybeUnreadOne()` to handle right
parens in this case:

```
(case x in x) ;; esac )
```

This is sort of like the `ungetc()` I've seen in other shell lexers.

## Parsing Issues

This section is about extra passes / "irregularities" at **parse time**.  In
the "Runtime Issues" section below, we discuss cases that involve parsing after
variable expansion, etc.

### Re-parsing - reading text more than once

We try to avoid re-parsing, but it happens in 4 places.

It complicates error messages with source location info.  It also implications
for `--tool ysh-ify` and `--tool fmt`, because it affects the **"lossless invariant"**.

This command is perhaps a quicker explanation than the text below:

    $ grep do_lossless */*.py
    ...
    osh/cmd.py: ...
    osh/word_parse.py: ...

Where re-parse:

1. [Here documents]($xref:here-doc):  We first read lines, and then parse them.
   - `VirtualLineReader` in [osh/cmd_parse.py]($oils-src)
   - This is re-parsing from **lines**

2. **Array L-values** like `a[x+1]=foo`.  bash allows splitting arithmetic
   expressions across word boundaries: `a[x + 1]=foo`.  But I don't see this
   used, and it would significantly complicate the OSH parser.
   - `_MakeAssignPair` in [osh/cmd_parse.py]($oils-src) has `do_lossless` condition
   - This is re-parsing from **tokens**

3. **Backticks**, the legacy form of `$(command sub)`.  There's an extra level
   of backslash quoting that may happen compared with `$(command sub)`.
   - `_ReadCommandSubPart` in [osh/word_parse.py]($oils-src) has `do_lossless`
     condition
   - This is re-parsing from **tokens**

### Re-parsing that doesn't affect the `ysh-ify` or `fmt` tools

4. `alias` expansion
    - `SnipCodeString` in [osh/cmd_parse.py]($oils-src)
   - This is re-parsing from **tokens**, but it only happens **after running**
     something like `alias ls=foo`.  So it doesn't affect the lossless
     invariant that `--tool ysh-ify` and `--tool fmt` use.

### Revisiting Tokens, Not Text

These language constructs are handled statically, but not in a single pass of
parsing:

- Assignment vs. Env binding detection: `FOO=bar declare a[x]=1`.
  We make another pass with `_SplitSimpleCommandPrefix()`.
  - Related: `s=1` doesn't cause reparsing, but `a[x+1]=y` does.
- Brace Detection in a few places: `echo {a,b}`
- Tilde Detection: `echo ~bob`, `home=~bob`

This is less problematic, since it doesn't affect error messages
(`ctx_SourceCode`) or the lossless invariant.

### Lookahead in Recursive Descent Parsers

- `myfunc() { echo hi; }` vs.  `myfunc=()  # an array`
- `shopt -s parse_equals`: For `x = 1 + 2*3`

### Where Parsers are Instantiated

- See [frontend/parse_lib.py]($oils-src) and its callers.

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
