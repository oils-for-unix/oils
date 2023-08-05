---
in_progress: yes
css_files: ../../web/base.css ../../web/manual.css ../../web/help.css ../../web/toc.css
body_css_class: width40 help-body
default_highlighter: oil-sh
---

Special Variables
===

This chapter in the [Oils Reference](index.html) describes special variables
for OSH and YSH.

<div id="toc">
</div>

<h2 id="usage">Command Line Usage</h3>

<h3 id="oils-usage" class="osh-ysh-topic">oils-usage</h3>
<h2 id="special">Special Variables</h2>

## Shell Vars

### `ARGV`

Replacement for `"$@"`

### `_DIALECT`

Name of a dialect being evaluated.

### `_this_dir`

The directory the current script resides in.  This knows about 3 situations:

- The location of `oshrc` in an interactive shell
- The location of the main script, e.g. in `osh myscript.sh`
- The location of script loaded with the `source` builtin

It's useful for "relative imports".

## Platform

### OIL_VERSION

The version of Oil that is being run, e.g. `0.9.0`.

<!-- TODO: specify comparison algorithm. -->

## Exit Status


### `_status`

Set by the `try` builtin.

    try ls /bad
    if (_status !== 0) {
      echo 'failed'
    }

### `_pipeline_status`

Alias for [PIPESTATUS]($osh-help).

### `_process_sub_status`

The exit status of all the process subs in the last command.

## Tracing

### SHX_indent

### SHX_punct

### SHX_pid_str
