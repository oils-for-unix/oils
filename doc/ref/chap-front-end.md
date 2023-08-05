---
in_progress: yes
css_files: ../../web/base.css ../../web/manual.css ../../web/help.css ../../web/toc.css
body_css_class: width40 help-body
default_highlighter: oil-sh
---

Oils Reference: Front End
===

<div id="toc">
</div>

## Usage

<h3 id="bundle-usage" class="osh-ysh-topic">App Bundle Usage</h3>

<!-- pre-formatted for help builtin -->

```
oils-for-unix is an executable that contains OSH, YSH, and more.

Usage: oils-for-unix MAIN_NAME ARG*
       MAIN_NAME ARG*

It behaves like busybox.  If it's invoked through a symlink like 'osh', then it
behaves like that command.

    ysh -c 'echo hi'

Otherwise, the command name can be passed as the first argument, e.g.:

    oils-for-unix ysh -c 'echo hi'
```

<h3 id="osh-usage" class="osh-topic"><code>bin/osh</code> Usage</h3>

<!-- pre-formatted for help builtin -->

```
osh is compatible with POSIX shell, bash, and more.

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

<h3 id="ysh-usage" class="ysh-topic"><code>bin/ysh</code> Usage</h3>

<!-- pre-formatted for help builtin -->

```
ysh is the shell with data tYpes, influenced by pYthon, JavaScript, Lisp, ...

Usage: ysh FLAG* SCRIPT ARG*
       ysh FLAG* -c COMMAND ARG*
       ysh FLAG*

`bin/ysh` is the same as `bin/osh` with a the `ysh:all` option group set.  So
`bin/ysh` also accepts shell flags.

    ysh -c 'echo hi'
    ysh myscript.ysh
    echo 'echo hi' | ysh
```


<h3 id="config" class="osh-ysh-topic">Configuring the Shell</h3>

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

<h3 id="startup" class="osh-ysh-topic">Startup Files</h3>

History is read?

## Lexing

<h3 id="comment" class="osh-ysh-topic">Comments</h3>

A comment starts with `#` and goes until the end of the line.

    echo hi  # print a greeting

<h3 id="line-continuation" class="osh-ysh-topic">Line Continuation</h3>

A backslash `\` at the end of a line continues the line without executing it:

    ls /usr/bin \
       /usr/lib \
       ~/src        # A single command split over three lines

<h3 id="doc-comment" class="ysh-topic">Doc Comments</h3>

Doc comments look like this:

    proc deploy {   
      ### Deploy the app
      echo hi
    }

<h3 id="multiline-command" class="ysh-topic">Multi-Line Command</h3>

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

