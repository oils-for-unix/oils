---
title: Front End (Oils Reference)
all_docs_url: ..
body_css_class: width40
default_highlighter: oils-sh
preserve_anchor_case: yes
---

<div class="doc-ref-header">

[Oils Reference](index.html) &mdash;
Chapter **Front End**

</div>

This chapter describes command line usage and lexing.

<span class="in-progress">(in progress)</span>

<div id="dense-toc">
</div>

<h2 id="usage">Command Line Usage</h2>

<h3 id="oils-usage" class="osh-ysh-topic" oils-embed="1">
  oils-usage
</h3>

<!-- pre-formatted for help builtin -->

```
bin/oils-for-unix is an executable that contains OSH, YSH, and more.

Usage: oils-for-unix MAIN_NAME ARG*
       MAIN_NAME ARG*

It behaves like busybox.  The command name can be passed as the first argument:

    oils-for-unix ysh -c 'echo hi'

More commonly, it's invoked through a symlink like 'ysh', which causes it to
behave like that command:

    ysh -c 'echo hi'

```

<h3 id="osh-usage" class="osh-topic" oils-embed="1">
  osh-usage
</h3>

<!-- pre-formatted for help builtin -->

```
bin/osh is compatible with POSIX shell, bash, and other shells.

Usage: osh FLAG* SCRIPT ARG*
       osh FLAG* -c COMMAND ARG*
       osh FLAG*

The command line accepted by `bin/osh` is compatible with /bin/sh and bash.

    osh -c 'echo hi'
    osh myscript.sh
    echo 'echo hi' | osh

It also has a few enhancements:

    osh -n -c 'hello'                    # pretty-print the AST
    osh --ast-format text -n -c 'hello'  # print it full

osh accepts POSIX sh flags, with these additions:

    -n             parse the program but don't execute it.  Print the AST.
    --ast-format   what format the AST should be in
```

<h3 id="ysh-usage" class="ysh-topic" oils-embed="1">
  ysh-usage
</h3>

<!-- pre-formatted for help builtin -->

```
bin/ysh is the shell with data tYpes, influenced by pYthon, JavaScript, ...

Usage: ysh FLAG* SCRIPT ARG*
       ysh FLAG* -c COMMAND ARG*
       ysh FLAG*

Examples:

    ysh -c 'echo hi'
    ysh myscript.ysh
    echo 'echo hi' | ysh

bin/ysh is the same as bin/osh with a the ysh:all option group set.  So bin/ysh
also accepts shell flags.  Examples:

    bin/ysh -n myfile.ysh
    bin/ysh +o errexit -c 'false; echo ok'
```


<h3 id="config" class="osh-ysh-topic">config</h3>

If the --rcfile flag is specified, that file will be executed on startup.
Otherwise:

- `bin/osh` runs `~/.config/oils/oshrc`
- `bin/ysh` runs `~/.config/oils/yshrc`

Pass --rcfile /dev/null or --norc to disable the startup file.

If the --rcdir flag is specified, files in that folder will be executed on
startup.
Otherwise:

- `bin/osh` runs everything in `~/.config/oils/oshrc.d/`
- `bin/ysh` runs everything in `~/.config/oils/yshrc.d/`

Pass --norc to disable the startup directory.

<h3 id="startup" class="osh-ysh-topic">startup</h3>

History is read?

<h3 id="line-editing" class="osh-ysh-topic">line-editing</h3>

Oils is often built with GNU readline, which recognizes many terminal commands
for editing input.

A useful option is `set -o vi`, which tells GNU readline to accept vi keys.

<h3 id="exit-codes" class="osh-ysh-topic">exit-codes</h3>

The meaning of exit codes is a convention, and generally follows one of two
paradigms.

#### The Success / Failure Paradigm 

- `0` for **success**.
- `1` for **runtime error**
  - Example: `echo foo > out.txt` and `out.txt` can't be opened.
  - Example: `fg` and there's not job to put in the foreground.
- `2` for **parse error**.  This means that we didn't *attempt* to do
  anything, rather than doing something, then it fails.
  - Example: A language parse error, like `echo $(`.
  - Example: Builtin usage error, like `read -z`.
- `3` for runtime **expression errors**.  The expression language is new to
  Oils, so its errors have a new exit code.
  - Example: divide by zero `42 / 0` 
  - Example: index out of range `a[1000]`

POSIX exit codes:

- `126` for permission denied when running a command (`errno EACCES`)
- `127` for command not found

Hint: Error checking often looks like this:

    try {
      ls /bad
    }
    if (_error.code !== 0) {
      echo 'failed'
    }

#### The Boolean Paradigm

- `0` for **true**
- `1` for **false**.
  - Example: `test -f foo` and `foo` isn't a file.
- `2` for **error** (usage error, parse error, etc.)
  - Example: `test -q`: the flag isn't accepted.

Hint: The `boolstatus` builtin ensures that false and error aren't confused:

    if boolstatus test -f foo {
      echo 'foo exists'
    }

See [YSH Fixes Shell's Error Handling](../error-handling.html) for more detail.

## Lexing

<h3 id="comment" class="osh-ysh-topic">comment</h3>

A comment starts with `#` and goes until the end of the line.

    echo hi  # print a greeting

<h3 id="line-continuation" class="osh-ysh-topic">line-continuation</h3>

A backslash `\` at the end of a line continues the line without executing it:

    ls /usr/bin \
       /usr/lib \
       ~/src        # A single command split over three lines

<h3 id="ascii-whitespace" class="osh-ysh-topic">ascii-whitespace</h3>

In most places, Oils uses the same definition of ASCII whitespace as JSON.
That is, any of these 4 bytes are considered whitespace:

    [ \t\r\n]  # space, tab, carriage return, newline

Sometimes newlines are significant, e.g. after shell commands.  Then the set of
whitespace characters is:

    [ \t\r]

(We don't handle the Windows `\r\n` sequence in a special way.  Instead, `\r`
is often treated like space and tab.)

Examples:

- Inside shell arithmetic `$(( 1 + 2 ))`, ASCII whitespace is ignored.
- Inside YSH expressions `42 + a[i] * f(x)`, ASCII whitespace is ignored.

Exceptions:

- Carriage return `\r` may not always be whitespace.
  - It can appear in an unquoted shell words, a rule that all POSIX shells
    follow.
  - The default `$IFS` doesn't include `\r`.
- YSH `trim()` functions also respect Unicode space.

<h3 id="ascii-control-chars" class="osh-ysh-topic">ascii-control-chars</h3>

The ASCII control chars have byte values `0x00` to `0x1F`.  This set includes 3
whitespace chars:

- tab - `\t` aka `0x09`
- newline - `\n` aka `0x0a`
- carriage return - `\r` aka `0x0d`

(It doesn't include the space - `0x20`.)

General rules:

- In J8 **data** languages, control chars other than whitespace are illegal.
  This is consistent with the JSON spec.
- In **source code**, control chars are allowed (but discouraged).
  - For example, in OSH, we don't check for control chars unquoted words
    words or string literals.  They are treated like printable chars.
  - TODO: YSH should only allow printable characters, which implies valid
    UTF-8.

Note about `NUL` aka `0x00`:

- The NUL byte is often used to terminate buffers, i.e. as a sentinel for
  [re2c](https://re2c.org) lexing.  This means that data after the NUL will be
  ignored.
   - J8 **data** input is read all at once, i.e. **not** split into lines.  So
     everything after the first NUL may be ignored.
   - Shell **source code** is split into lines.

<h3 id="doc-comment" class="ysh-topic">doc-comment</h3>

Doc comments look like this:

    proc deploy {   
      ### Deploy the app
      echo hi
    }

<h3 id="multiline-command" class="ysh-topic">multiline-command</h3>

The ... prefix starts a single command over multiple lines.  It allows writing
long commands without \ continuation lines, and the resulting limitations on
where you can put comments.

Single command example:

    ... chromium-browser
        # comment on its own line
        --no-proxy-server
        --incognito  # comment to the right
        ;

Long pipelines and and-or chains:

    ... find .
        # exclude tests
      | grep -v '_test.py'
      | xargs wc -l
      | sort -n
      ;

    ... ls /
     && ls /bin
     && ls /lib
     || error "oops"
     ;

## Tools

### cat-em

Print files embedded in the `oils-for-unix` binary to stdout.  Example:

    osh --tool cat-em stdlib/math.ysh stdlib/other.ysh


## Help Chapters

<h3 id="osh-chapters" class="osh-topic" oils-embed="1">
  osh-chapters
</h3>

<!-- shown at the bottom of 'help' -->

```
The reference is divided in to "chapters", each of which has its own table of
contents.  Type:

    help osh-$CHAPTER

Where $CHAPTER is one of:

    front-end
    command-lang
    osh-assign
    word-lang
    mini-lang
    builtin-cmd
    option
    special-var
    plugin

Example:

    help osh-word-lang
```


<h3 id="ysh-chapters" class="ysh-topic" oils-embed="1">
  ysh-chapters
</h3>

<!-- shown at the bottom of 'help' -->

```
The reference is divided in to "chapters", each of which has its own table of
contents.  Type:

    help ysh-$CHAPTER

Where $CHAPTER is one of:

    front-end
    command-lang
    expr-lang
    word-lang
    builtin-cmd
    option
    special-var
    type-method
    builtin-func

Example:

    help ysh-expr-lang
```

<!-- h4 needed to end last card: ysh-chapters -->
<h4></h4>
