---
in_progress: yes
body_css_class: width40 help-body
default_highlighter: oils-sh
preserve_anchor_case: yes
---

Global Shell Options
===

This chapter in the [Oils Reference](index.html) describes global shell options
for OSH and YSH.

<div id="toc">
</div>

## Option Groups

<!-- note: explicit anchor necessary because of mangling -->
<h3 id="strict:all">strict:all</h3>

Option in this group disallow problematic or confusing shell constructs.  The
resulting script will still run in another shell.

    shopt --set strict:all  # turn on all options
    shopt -p strict:all     # print their current state

<h3 id="ysh:upgrade">ysh:upgrade</h3>

Options in this group enable YSH features that are less likely to break
existing shell scripts.

For example, `parse_at` means that `@myarray` is now the operation to splice
an array.  This will break scripts that expect `@` to be literal, but you can
simply quote it like `'@literal'` to fix the problem.

    shopt --set ysh:upgrade   # turn on all options
    shopt -p ysh:upgrade      # print their current state

<h3 id="ysh:all">ysh:all</h3>

Enable the full YSH language.  This includes everything in the `ysh:upgrade`
group.

    shopt --set ysh:all     # turn on all options
    shopt -p ysh:all        # print their current state

## Strictness

### strict_control_flow

Disallow `break` and `continue` at the top level, and disallow empty args like
`return $empty`.

### strict_tilde

Failed tilde expansions cause hard errors (like zsh) rather than silently
evaluating to `~` or `~bad`.

### strict_word_eval

TODO

### strict_nameref

When `strict_nameref` is set, undefined references produce fatal errors:

    declare -n ref
    echo $ref  # fatal error, not empty string
    ref=x      # fatal error instead of decaying to non-reference

References that don't contain variables also produce hard errors:

    declare -n ref='not a var'
    echo $ref  # fatal
    ref=x      # fatal

### parse_ignored

For compatibility, YSH will parse some constructs it doesn't execute, like:

    return 0 2>&1  # redirect on control flow

When this option is disabled, that statement is a syntax error.

## ysh:upgrade

### parse_at

TODO

### parse_brace

TODO

### parse_paren

TODO

### parse_raw_string

Allow the r prefix for raw strings in command mode:

    echo r'\'  # a single backslash

Since shell strings are already raw, this means that YSH just ignores the r
prefix.

### command_sub_errexit

TODO

### process_sub_fail

TODO

### sigpipe_status_ok

If a process that's part of a pipeline exits with status 141 when this is
option is on, it's turned into status 0, which avoids failure.

SIGPIPE errors occur in cases like 'yes | head', and generally aren't useful.

### simple_word_eval

TODO:

<!-- See doc/simple-word-eval.html -->

## YSH Breaking

### copy_env

### parse_equals

## Errors

## Globbing

### nullglob

Normally, when no files match  a glob, the glob itself is returned:

    $ echo L *.py R  # no Python files in this dir
    L *.py R

With nullglob on, the glob expands to no arguments:

    shopt -s nullglob
    $ echo L *.py R
    L R

(This option is in GNU bash as well.)

### dashglob

Do globs return results that start with `-`?  It's on by default in `bin/osh`,
but off when YSH is enabled.

Turning it off prevents a command like `rm *` from being confused by a file
called `-rf`.

    $ touch -- myfile -rf

    $ echo *
    -rf myfile

    $ shopt -u dashglob
    $ echo *
    myfile

## Debugging

## Interactive

## Other Option

