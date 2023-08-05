---
in_progress: yes
css_files: ../web/base.css ../web/manual.css ../web/help.css ../web/toc.css
body_css_class: width40 help-body
---

YSH Help
========

This doc describes every aspect of YSH briefly.  It underlies the `help`
builtin, and is indexed by keywords.

Navigate it with the [index of YSH help topics](oil-help-topics.html).

<!--
IMPORTANT: This doc is processed in TWO WAYS.  Be careful when editing.

It generates both HTML and text for the 'help' builtin.
-->

<div id="toc">
</div>


<h2 id="option">Shell Options</h2>

### Option Groups

<!-- note: explicit anchor necessary because of mangling -->
<h4 id="strict:all">strict:all</h4>

Option in this group disallow problematic or confusing shell constructs.  The
resulting script will still run in another shell.

    shopt --set strict:all  # turn on all options
    shopt -p strict:all     # print their current state

<h4 id="ysh:upgrade">ysh:upgrade</h4>

Options in this group enable Oil features that are less likely to break
existing shell scripts.

For example, `parse_at` means that `@myarray` is now the operation to splice
an array.  This will break scripts that expect `@` to be literal, but you can
simply quote it like `'@literal'` to fix the problem.

    shopt --set ysh:upgrade   # turn on all options
    shopt -p ysh:upgrade      # print their current state

<h4 id="ysh:all">ysh:all</h4>

Enable the full Oil language.  This includes everything in the `ysh:upgrade`
group.

    shopt --set ysh:all     # turn on all options
    shopt -p ysh:all        # print their current state

### Strictness

#### strict_control_flow

Disallow `break` and `continue` at the top level, and disallow empty args like
`return $empty`.

#### strict_tilde

Failed tilde expansions cause hard errors (like zsh) rather than silently
evaluating to `~` or `~bad`.

#### strict_word_eval

TODO

#### strict_nameref

When `strict_nameref` is set, undefined references produce fatal errors:

    declare -n ref
    echo $ref  # fatal error, not empty string
    ref=x      # fatal error instead of decaying to non-reference

References that don't contain variables also produce hard errors:

    declare -n ref='not a var'
    echo $ref  # fatal
    ref=x      # fatal

#### parse_ignored

For compatibility, Oil will parse some constructs it doesn't execute, like:

    return 0 2>&1  # redirect on control flow

When this option is disabled, that statement is a syntax error.

### Oil Basic

#### parse_at

TODO

#### parse_brace

TODO

#### parse_paren

TODO

#### parse_raw_string

Allow the r prefix for raw strings in command mode:

    echo r'\'  # a single backslash

Since shell strings are already raw, this means that Oil just ignores the r
prefix.

#### command_sub_errexit

TODO

#### process_sub_fail

TODO

#### sigpipe_status_ok

If a process that's part of a pipeline exits with status 141 when this is
option is on, it's turned into status 0, which avoids failure.

SIGPIPE errors occur in cases like 'yes | head', and generally aren't useful.

#### simple_word_eval

TODO:

<!-- See doc/simple-word-eval.html -->

### Oil Breaking

#### copy_env

#### parse_equals

<h2 id="special">Special Variables</h2>

### Shell Vars

#### `ARGV`

Replacement for `"$@"`

#### `_DIALECT`

Name of a dialect being evaluated.

#### `_this_dir`

The directory the current script resides in.  This knows about 3 situations:

- The location of `oshrc` in an interactive shell
- The location of the main script, e.g. in `osh myscript.sh`
- The location of script loaded with the `source` builtin

It's useful for "relative imports".

### Platform

#### OIL_VERSION

The version of Oil that is being run, e.g. `0.9.0`.

<!-- TODO: specify comparison algorithm. -->

### Exit Status


#### `_status`

Set by the `try` builtin.

    try ls /bad
    if (_status !== 0) {
      echo 'failed'
    }

#### `_pipeline_status`

Alias for [PIPESTATUS]($osh-help).

#### `_process_sub_status`

The exit status of all the process subs in the last command.

### Tracing

#### SHX_indent

#### SHX_punct

#### SHX_pid_str

<h2 id="lib">Oil Libraries</h2>

### Pattern

#### `_match()`

#### `_start()`

#### `_end()`

### Collections

#### len()

- `len(mystr)` is its length in bytes
- `len(myarray)` is the number of elements
- `len(assocarray)` is the number of pairs

### String

#### find 

#### sub 

#### join 

Given an array of strings, returns a string.

    var x = ['a', 'b', 'c']

    $ echo $[join(x)]
    abc

    $ echo $[join(x, ' ')]  # optional delimiter
    a b c

#### split

<!--
Note: This is currently SplitForWordEval.  Could expose Python-type splitting?
-->

### Word

<!--
Note: glob() function conflicts with 'glob' language help topic
-->

#### maybe

### Arrays

- `index(A, item)` is like the awk function
- `append()` is a more general version of the `append` builtin
- `extend()`

### Assoc Arrays

- `keys()`
- `values()`

### Introspection

#### `shvar_get()`

TODO

### Config Gen

### Better Syntax

These functions give better syntax to existing shell constructs.

- `shquote()` for `printf %q` and `${x@Q}`
- `lstrip()` for `${x#prefix}` and  `${x##prefix}`
- `rstrip()` for `${x%suffix}` and  `${x%%suffix}` 
- `lstripglob()` and `rstripglob()` for slow, legacy glob
- `upper()` for `${x^^}`
- `lower()` for `${x,,}`
- `strftime()`: hidden in `printf`


### Codecs

TODO

### Hashing

TODO

