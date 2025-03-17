---
title: Global Shell Options (Oils Reference)
all_docs_url: ..
body_css_class: width40
default_highlighter: oils-sh
preserve_anchor_case: yes
---

<div class="doc-ref-header">

[Oils Reference](index.html) &mdash;
Chapter **Global Shell Options**

</div>

This chapter describes global shell options in Oils.  Some options are from
POSIX shell, and some are from [bash]($xref).  We also use options to turn
[OSH]($xref) into [YSH]($xref).

<span class="in-progress">(in progress)</span>

<div id="dense-toc">
</div>

## Errors

These options are from POSIX shell:

    nounset -u  
    errexit -e

These are from bash:

    inherit_errexit:
    pipefail

## Globbing

These options are from POSIX shell:

    noglob -f

From bash:

    nullglob   failglob   dotglob

From Oils:

    dashglob

Some details:

### nullglob

When `nullglob` is on, a glob matching no files expands to no arguments:

    shopt -s nullglob
    $ echo L *.py R
    L R

Without this option, the glob string itself is returned:

    $ echo L *.py R  # no Python files in this dir
    L *.py R

(This option is from GNU bash.)

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

## Other Option

    noclobber -C  # Redirects can't overwrite files

## Debugging

<h3 id="errtrace">errtrace (-E)</h3>

Enable the ERR [trap][] in both shell functions and subshells.

The option is also `set -E`.  It's designed to be compatible with bash.

[trap]: chap-builtin-cmd.html#trap

### extdebug

Show more info in when printing functions with `declare -f`.  Used by
`task-five.sh`.

<h3 id="xtrace">xtrace (-x)</h3>

Show execution traces.

- In OSH, the [PS4][] variables control the display.
- In YSH, the `SHX_*` variables control the display.

[PS4]: chap-plugin.html#PS4

This option is also `set -x`.  It's required by POSIX shell.

### verbose

Not implemented.

This option is from POSIX shell.

## Interactive

These options are from bash.

    emacs   vi


## Compat

### eval_unsafe_arith

Allow dynamically parsed `a[$(echo 42)]`  For bash compatibility.

### ignore_flags_not_impl

Suppress failures from unimplemented flags.  Example:

    shopt --set ignore_flags_not_impl

    declare -i foo=2+3  # not evaluated to 5, but doesn't fail either

This option can be useful for "getting past" errors while testing.

### ignore_shopt_not_impl

Suppress failures from unimplemented shell options.  Example:

    shopt --set ignore_shopt_not_impl

    shopt --set xpg_echo  # exit with status 0, not 1
                          # this is a bash option that OSH doesn't implement

This option can be useful for "getting past" errors while testing.

## Groups

To turn OSH into YSH, we use three option groups.  Some of them allow new
features, and some disallow old features.

<!-- note: explicit anchor necessary because of mangling -->
<h3 id="strict:all">strict:all</h3>

Option in this group disallow problematic or confusing shell constructs.  The
resulting script will still run in another shell.

    shopt --set strict:all    # turn on all options
    shopt -p strict:all       # print their current state

Parsing options:

      strict_parse_slice      # No implicit length for ${a[@]::}
    X strict_parse_utf8       # Source code must be valid UTF-8

Runtime options:

      strict_argv             # No empty argv
      strict_arith            # Fatal parse errors (on by default)
      strict_array            # Arrays and strings aren't confused
      strict_control_flow     # Disallow misplaced keyword, empty arg
      strict_errexit          # Disallow code that ignores failure
      strict_nameref          # Trap invalid variable names
      strict_word_eval        # Expose unicode and slicing errors
      strict_tilde            # Tilde subst can result in error
    X strict_glob             # Parse the sublanguage more strictly

<h3 id="ysh:upgrade">ysh:upgrade</h3>

Options in this group enable new YSH features.  It doesn't break existing shell
scripts when it's avoidable.

For example, `parse_at` means that `@myarray` is now the operation to splice
an array.  This will break scripts that expect `@` to be literal, but you can
simply quote it like `'@literal'` to fix the problem.

    shopt --set ysh:upgrade   # turn on all options
    shopt -p ysh:upgrade      # print their current state

Details on each option:

      parse_at                echo @array @[arrayfunc(x, y)]
      parse_brace             if true { ... }; cd ~/src { ... }
      parse_equals            x = 'val' in Caps { } config blocks
      parse_paren             if (x > 0) ...
      parse_proc              proc p { ... }
      parse_triple_quote      """$x"""  '''x''' (command mode)
      parse_ysh_string        echo r'\' u'\\' b'\\' (command mode)
      command_sub_errexit     Synchronous errexit check
      process_sub_fail        Analogous to pipefail for process subs
      sigpipe_status_ok       status 141 -> 0 in pipelines
      simple_word_eval        No splitting, static globbing
      xtrace_rich             Hierarchical and process tracing
      xtrace_details (-u)     Disable most tracing with +
      dashglob (-u)           Disabled to avoid files like -rf
      env_obj                 Init ENV Obj at startup; use it when starting
                              child processes
      for_loop_frames         YSH can create closures from loop vars

<h3 id="ysh:all">ysh:all</h3>

Enable the full YSH language.  This includes everything in the `ysh:upgrade`
group and the `strict:all` group.

    shopt --set ysh:all       # turn on all options
    shopt -p ysh:all          # print their current state

Details on options that are not in `ysh:upgrade` and `strict:all`:

      parse_at_all            @ starting any word is an operator
      parse_backslash (-u)    Allow bad backslashes in "" and $''
      parse_backticks (-u)    Allow legacy syntax `echo hi`
      parse_bare_word (-u)    'case unquoted' and 'for x in unquoted'
      parse_dollar (-u)       Allow bare $ to mean \$  (maybe $/d+/)
      parse_dbracket (-u)     Is legacy [[ allowed?
      parse_dparen (-u)       Is (( legacy arithmetic allowed?
      parse_ignored (-u)      Parse, but ignore, certain redirects
      parse_sh_arith (-u)     Allow legacy shell arithmetic
      expand_aliases (-u)     Whether aliases are expanded
    X old_builtins (-u)       local/declare/etc.  pushd/popd/dirs
                              ... source  unset  printf  [un]alias
                              ... getopts
    X old_syntax (-u)         ( )   ${x%prefix}  ${a[@]}   $$
      no_exported             Environ doesn't correspond to exported (-x) vars
      no_init_globals         At startup, don't set vars like PWD, SHELLOPTS
      simple_echo             echo doesn't accept flags -e -n
      simple_eval_builtin     eval takes exactly 1 argument
      simple_test_builtin     3 args or fewer; use test not [
    X simple_trap             Function name only
      verbose_errexit         Whether to print detailed errors

## YSH Details

### opts-redefine

In the interactive shell, you can redefine procs and funcs.

      redefine_source          'source-guard' builtin always returns 0
    X redefine_const            Can consts be redefined?

### opts-internal

These options are used by the interpreter.  You generally shouldn't set them
yourself.

    _allow_command_sub  To implement strict_errexit, eval_unsafe_arith
    _allow_process_sub  To implement strict_errexit
    dynamic_scope       To implement proc and func
    _no_debug_trap      Used in pipelines in job control shell
    _running_trap       To disable strict_errexit
    _running_hay        Hay evaluation

## Unlinked Descriptions

Here are some descriptions of individual options.

### strict_control_flow

Disallow `break` and `continue` at the top level, and disallow empty args like
`return $empty`.

### strict_tilde

Failed tilde expansions cause hard errors (like zsh) rather than silently
evaluating to `~` or `~bad`.


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

### parse_triple_quote

Parse the shell-style multi-line strings, which strip leading whitespace:

    echo '''    
      one
      two
      '''

    echo """
      hello
      $name
      """

(This option affects only command mode.  Such strings are always parsed in
expression mode.)

### parse_ysh_string

Allow `r'\'` and `u'\\'` and `b'\\'` strings, as well as their multi-line
versions.

Since shell strings are already raw, this means that YSH just ignores the r
prefix:

    echo r'\'  # a single backslash

J8 unicode strings:

    echo u'mu \u{3bc}'  # mu char

J8 byte strings:

    echo b'byte \yff'

(This option affects only command mode.  Such strings are always parsed in
expression mode.)

### sigpipe_status_ok

If a process that's part of a pipeline exits with status 141 when this is
option is on, it's turned into status 0, which avoids failure.

SIGPIPE errors occur in cases like 'yes | head', and generally aren't useful.

