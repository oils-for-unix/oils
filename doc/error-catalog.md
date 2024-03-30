---
default_highlighter: oils-sh
---

Oils Error Catalog, With Hints
==================

This doc lists errors from Oils (both [OSH]($xref) and [YSH]($xref)), with
hints to help you fix them.

Each error is associated with a code like `OILS-ERR-42`, a string that search
engines should find.

<!-- 
Later, we could have a URL shortener, like https://oils.err/42 
-->

<div id="toc">
</div>

## How to Contribute

If you see an error that you don't understand:

1. Ask a question on `#oil-help` on [Zulip]($xref:zulip).  What's the problem,
   and what's the solution?
1. Then `grep` the source code for the confusing error message.  Tag it with a
   string like `OILS-ERR-43`, picking a new number according to the conventions
   below.
1. Add a tagged section below, with hints and explanations.
   - Quote the error message.  You may want copy and paste from the output of
     `test/{parse,runtime,ysh-parse,ysh-runtime}-errors.sh`.  Add an HTML
     comment `<!-- -->` about that.
   - Link to relevant sections in the [**Oils Reference**](ref/index.html).
1. Optionally, add your name to the acknowledgements list at the end of this
   doc.

Note that error messages are **hard** to write, because a single error could
result from many different user **intentions**!

### To Preview this Doc

Right now I use this command:

    build/doc.sh split-and-render doc/error-catalog.md

Then paste this into your browser:

    file:///home/andy/git/oilshell/oil/_release/VERSION/doc/error-catalog.html

(Replace with your home dir)

## Parse Errors - Rejected Input

Roughly speaking, a parse error means that text input was **rejected**, so the
shell didn't try to do anything.

Examples:

    echo )   # Shell syntax error

    type -z  # -z flag not accepted

These error codes start at `10`.

### OILS-ERR-10

<!--
Generated with:
test/ysh-parse-errors.sh test-func-var-checker
-->

```
      setvar x = true
             ^
[ -c flag ]:3: setvar couldn't find matching 'var x' (OILS-ERR-10)
```

- Did you forget to declare the name with the [var](ref/chap-cmd-lang.html#var)
  keyword?
- Did you mean to use the [setglobal](ref/chap-cmd-lang.html#setglobal)
  keyword?

Related help topics:

- [setvar](ref/chap-cmd-lang.html#setvar)

### OILS-ERR-11

<!--
Generated with:
test/ysh-parse-errors.sh ysh_c_strings (this may move)
-->

```
  echo $'\z'
         ^
[ -c flag ]:1: Invalid char escape in C-style string literal (OILS-ERR-11)
```

- Did you mean `$'\\z'`?  Backslashes must be escaped in `$''` and `u''` and
  `b''` strings.
- Did you mean something like `$'\n'`?  Only valid escapes are accepted in YSH.

Related help topics:

- [osh-string](ref/chap-word-lang.html#osh-string) (word language)
- [ysh-string](ref/chap-expr-lang.html#ysh-string) (expression language)

### OILS-ERR-12

<!--
Generated with:
test/ysh-parse-errors.sh ysh_dq_strings (this may move)
-->

```
  echo "\z"
        ^
[ -c flag ]:1: Invalid char escape in double quoted string (OILS-ERR-12)
```

- Did you mean `"\\z"`?  Backslashes must be escaped in double-quoted strings.
- Did you mean something like `"\$"`?  Only valid escapes are accepted in YSH.

Related help topics:

- [osh-string](ref/chap-word-lang.html#osh-string) (word language)
- [ysh-string](ref/chap-expr-lang.html#ysh-string) (expression language)

### OILS-ERR-13

<!--
Generated with:
test/ysh-parse-errors.sh ysh_bare_words (this may move)
-->

```
  echo \z
       ^~
[ -c flag ]:1: Invalid char escape in unquoted word (OILS-ERR-13)
```

- Did you mean `\\z`?  Backslashes must be escaped in unquoted words.
- Did you mean something like `\$`?  Only valid escapes are accepted in YSH.

## Runtime Errors - Traditional Shell

These errors may occur in shells like [bash]($xref) and [zsh]($xref).

They're numbered starting from `100`.  (If we have more than 90 parse errors,
we can start a new section, like `300`.)

### OILS-ERR-100

Example TODO: Command not found.

- Is the file in your `$PATH`?  That variable controls where the shell shell
  looks for executable files.
- Did you misspell a shell function or YSH `proc`?

## Runtime Errors - Oils and YSH

These errors don't occur in shells like [bash]($xref) and [zsh]($xref).

They may involve Python-like **expressions** and **typed data**.

They're numbered starting from `200`.

### OILS-ERR-200

<!--
Generated with:
test/runtime-errors.sh test-external_cmd_typed_args
-->

```
  cat ("myfile")
      ^
[ -c flag ]:1: fatal: 'cat' appears to be external. External commands don't accept typed args (OILS-ERR-200)
```

- Builtin commands and user-defined procs may accept [typed
  args](ref/chap-cmd-lang.html#typed-arg), but external commands never do.
- Did you misspell a [YSH proc](ref/chap-cmd-lang.html#proc-def)? If a name is
  not found, YSH assumes it's an external command.
- Did you forget to source a file that contains the proc or shell function you
  wanted to run?

### OILS-ERR-201

<!--
Generated with:
test/runtime-errors.sh test-arith_ops_str
-->

```
  = "100" + "10a"
          ^
[ -c flag ]:1: fatal: Binary operator expected numbers, got Str and Str (OILS-ERR-201)
```

- Use `++` if you intended to _concatenate_ strings or lists.
- The arithmetic operators (`+`, `-`, `*`, `/`) may be used on strings,
  provided that they are formatted as numbers. For example, `= '10' + '1'` will
  result in `(Int) 11`.
- You can explicitly parse a string into a number with the
  [`int()`](ref/chap-builtin-func.html#int) and
  [`float()`](ref/chap-builtin-func.html#float) functions.

## Appendix

### Kinds of Errors from Oils

- Runtime errors (status 1) - the shell tried to do something, but failed.
  - Example: `echo hi > /does/not/exist`
- Parse errors and builtin usage errors (status 2) - input rejected, so the
  shell didn't try to do anything.
- Uncaught I/O errors (status 2)
- Expression errors (status 3)
- User errors from the `error` builtin (status 10 is default)

### Contributors

(If you updated this doc, feel free to add your name to the end of this list.)

