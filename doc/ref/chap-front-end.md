---
in_progress: yes
body_css_class: width40 help-body
default_highlighter: oil-sh
---

Front End
===

This chapter in the [Oils Reference](index.html) describes command line usage
and lexing.

<div id="toc">
</div>

<h2 id="usage">Command Line Usage</h3>

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

`bin/ysh` is the same as `bin/osh` with a the `ysh:all` option group set.  So
`bin/ysh` also accepts shell flags.

    ysh -c 'echo hi'
    ysh myscript.ysh
    echo 'echo hi' | ysh
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

    try ls /bad
    if (_status !== 0) {
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

See [Oil Fixes Shell's Error Handling](../error-handling.html) for more detail.

## Lexing

<h3 id="comment" class="osh-ysh-topic">comment</h3>

A comment starts with `#` and goes until the end of the line.

    echo hi  # print a greeting

<h3 id="line-continuation" class="osh-ysh-topic">line-continuation</h3>

A backslash `\` at the end of a line continues the line without executing it:

    ls /usr/bin \
       /usr/lib \
       ~/src        # A single command split over three lines

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
