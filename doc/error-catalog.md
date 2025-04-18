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
     `doc/error-catalog.sh`, or
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

- Did you forget to declare the name with the [var](ref/chap-ysh-cmd.html#var)
  keyword?
- Did you mean to use the [setglobal](ref/chap-ysh-cmd.html#setglobal)
  keyword?

Related help topics:

- [setvar](ref/chap-ysh-cmd.html#setvar)

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

```
      if (a || b && c) {
            ^~
[ -c flag ]:2: Use 'or' in expression mode (OILS-ERR-15)
```

Expression mode uses `not or and`, rather than `! || &&`.  See [Command vs.
Expression Mode](command-vs-expression-mode.html) for details.


No:

    if (!a || b && c) {
      echo no
    }

Yes:

    if (not a or b and c) {
      echo yes
    }


Command mode is the opposite; it uses `! || &&`, rather than `not or and`:

No:

    # Command mode
    if not test --dir a or test --dir b and test --dir c {
      echo no
    }

Yes:

    # Command mode
    if ! test --dir a || test --dir b && test --dir c {
      echo yes
    }

### OILS-ERR-16

```
  for x in (1 .. 5) {
              ^~
[ -c flag ]:1: Use ..< for half-open range, or ..= for closed range (OILS-ERR-16)
```

<!-- 
Similar to
test/ysh-parse-errors.sh test-expr-range
-->

There are two ways to construct a [Range](ref/chap-expr-lang#range). The `..<`
operator is for half-open ranges and the `..=` operator is for closed ranges:

    for i in (0 ..< 3) {
      echo $i
    }
    => 0
    => 1
    => 2

    for i in (0 ..= 3) {
      echo $i
    }
    => 0
    => 1
    => 2
    => 3

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
[ -c flag ]:1: Command 'findz' not found (OILS-ERR-100)
```

The shell tried to execute an external command, but couldn't.

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


### OILS-ERR-102

```
  var cmd = ^(seq 3)
              ^~~
[ stdin ]:1: Command 'seq' not found in pure mode (OILS-ERR-102)
```

The shell tried to execute a command in pure mode, but couldn't.

In pure mode, only user-defined procs and a few builtin commands can be the "first word".

- Did you misspell a proc name?
- Are you trying to run an external command?  Such commands aren't allowed in
  pure mode.

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

### OILS-ERR-204

<!--
Generated with:
test/ysh-runtime-errors.sh test-purity
-->

```
  x=$(date)
    ^~
impure.sh:1: fatal: Command subs aren't allowed in pure mode (OILS-ERR-204)
```

In **pure mode**, the shell can't do I/O.  It's intended for config file
evaluation and pure functions.

- Did you mean to use `--eval` instead of `--eval-pure`?
- Did you mean to use a `proc`, rather than a `func`?


<!-- TODO -->

## Runtime Errors: `strict:all`

### OILS-ERR-300

```
  if ! ls | wc -l; then echo failed; fi
          ^
[ -c flag ]:1: fatal: Command conditionals should only have one status, not Pipeline (strict_errexit, OILS-ERR-300)
```

Compound commands can't be used as conditionals because it's ambiguous.

It confuses true/false with pass/fail.  What if part of the pipeline fails?
What if `ls` doesn't exist?

This YSH idiom is more explicit:

    try {
      ls | wc -l
    }
    if failed {
      echo failed
    }

### OILS-ERR-301

<!--
Generated with demo/home-page.sh strict-mode
-->

```
    if shell-func; then
       ^~~~~~~~~~
foo.sh:9: fatal: Can't run functions or procs while errexit is disabled (OILS-ERR-301)
```

This error prevents you from hitting a **pitfall** with `set -e` aka `errexit`,
as it's defined in POSIX shell.

Here are some shell-compatible solutions:

- Rewrite your code to avoid the function call within `if`, `||`, etc.
- Wrap the function in another process, like `if $0 shell-func`
  - This is what we call the [$0 Dispatch Pattern](https://www.oilshell.org/blog/2021/08/xargs.html)

In YSH, use the [try][] builtin instead of `if`.

[try]: ref/chap-builtin-cmd.html#try

- [Guide to YSH Error Handling](ysh-error.html)
- Technical details: [YSH Fixes Shell's Error Handling (`errexit`)](error-handling.html)


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

