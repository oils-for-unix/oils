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
- Did you to use single quotes, like `u'\n'` rather than `u"\n"`?

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

### OILS-ERR-14

<!--
Generated with:
test/ysh-parse-errors.sh test-parse-dparen
-->

```
  if ((1 > 0 && 43 > 42)); then echo yes; fi
     ^~
[ -c flag ]:1: Bash (( not allowed in YSH (parse_dparen, see OILS-ERR-14 for wart)
```

Two likely causes:

- Do you need to rewrite bash arithmetic as YSH arithmetic (which is
  Python-like)?
- Do you need to work around an [unfortunate wart](warts.html#two-left-parens-should-be-separated-by-space) in YSH?

Examples:

    if (1 > 0 and 43 > 42) {  # YSH-style
      echo yes
    }
  
    if ( (x + 1) < n) {  # space between ( ( avoids ((
      echo yes
    }

### OILS-ERR-15

Incorrect:

    # Expression mode
    if (a || b) {
      echo yes
    }

    # Command mode
    if test --dir a or test --dir b { ... }

Correct:

    # Expression mode
    if (a or b) {
      echo yes
    }

    # Command mode
    if test --dir a || test --dir b { ... }

In general, code within parentheses `()` is parsed as Python-like expressions
-- referred to as [expression mode](command-vs-expression-mode.html). The
standard boolean operators are written as `a and b`, `a or b` and `not a`.

This differs from [command mode](command-vs-expression-mode.html) which uses
`||` for "OR", `&&` for "AND" and `!` for "NOT".

## Runtime Errors - Traditional Shell

These errors may occur in shells like [bash]($xref) and [zsh]($xref).

They're numbered starting from `100`.  (If we have more than 90 parse errors,
we can start a new section, like `300`.)

### OILS-ERR-100

<!--
Generated with:
test/runtime-errors.sh test-command-not-found
-->

```
  findz
  ^~~~~
[ -c flag ]:1: 'findz' not found (OILS-ERR-100)
```

- Did you misspell a command name?
- Did you misspell a shell function or a YSH `proc`?
- Is the file in your `$PATH`?  The `PATH` variable is a colon-separated list
  of directories, where executable files may live.
- Is `findz` file executable bit set?  (`chmod +x`)

### OILS-ERR-101

<!--
Generated with:
test/runtime-errors.sh test-assoc-array
-->

Let's look at **three** instances of this error.

```
  declare -A assoc; assoc[x]=1
                    ^~~~~~
[ -c flag ]:1: fatal: Assoc array keys must be strings: $x 'x' "$x" etc. (OILS-ERR-101)
```

- Is `x` a string?  Then add quotes: `assoc['x']=1`
- Is `x` a variable?  Then write: `assoc[$x]=1`

---

Same idea here:

```
  declare -A assoc; echo ${assoc[x]}
                                 ^
[ -c flag ]:1: fatal: Assoc array keys must be strings: $x 'x' "$x" etc. (OILS-ERR-101)
```

- Is `x` a string?  Then add quotes: `${assoc['x']}`
- Is `x` a variable?  Then write: `${assoc[$x]}`

---

The third example is **tricky** because `unset` takes a **string**.  There's an
extra level of parsing, which:

- Implies an extra level of quoting
- Causes OSH to display the following **nested** error message

```
  assoc[k]
       ^
[ dynamic LHS word at line 1 of [ -c flag ] ]:1

  declare -A assoc; key=k; unset "assoc[$key]"
                                 ^
[ -c flag ]:1: fatal: Assoc array keys must be strings: $x 'x' "$x" etc. (OILS-ERR-101)
```

To fix it, consider using **single quotes**:

    unset 'assoc[$key]'

---

- This is the error in [Parsing Bash is
  Undecidable](https://www.oilshell.org/blog/2016/10/20.html) (2016)
- Also mentioned in [Known Differences](known-differences.html)


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
  = "age: " + "100"
            ^
[ -c flag ]:1: fatal: Binary operator expected numbers, got Str and Str (OILS-ERR-201)

  = 100 + myvar
        ^
[ -c flag ]:2: fatal: Binary operator expected numbers, got Int and Str (OILS-ERR-201)
```

- Did you mean to use `++` to concatenate strings/lists?
- The arithmetic operators [can coerce string operands to
  numbers](ref/chap-expr-lang.html#ysh-arith). However, if you are operating on
  user provided input, it may be a better idea to first parse that input with
  [`int()`](ref/chap-builtin-func.html#int) or
  [`float()`](ref/chap-builtin-func.html#float).

### OILS-ERR-202

<!--
Generated with:
test/ysh-runtime-errors.sh test-float-equality
-->

```
  pp (42.0 === x)
                ^~~
[ -c flag ]:3: fatal: Equality isn't defined on Float values (OILS-ERR-202)
```

Floating point numbers shouldn't be tested for equality.  Alternatives:

    = abs(42.0 - x) < 0.1
    = floatEquals(42.0, x) 

### OILS-ERR-203

<!--
Generated with:
test/ysh-runtime-errors.sh test-cannot-stringify-list
-->

```
  var mylist = [1,2,3]; write $[mylist]
                              ^~
[ -c flag ]:1: fatal: Expr sub got a List, which can't be stringified (OILS-ERR-203)
```

- Did you mean to use `@mylist` instead of `$mylist`?
- Did you mean to use `@[myfunc()]` instead of `$[myfunc()]`?
- Did you mean `$[join(mylist)]`?

Or:

- Do you have an element that can't be stringified in a list, like `['good',
  {bad: true}]`?


<!-- TODO -->


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

