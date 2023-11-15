---
default_highlighter: oils-sh
in_progress: yes
---

Interactive Shell Completion
============================

You can use interactive completion directly under `osh` or `ysh`, or clients of
a [headless shell](headless.html) can use it as an API.  

## Completion API

The completion API is modeled after the [bash completion
API](https://www.gnu.org/software/bash/manual/html_node/Command-Line-Editing.html#Command-Line-Editing)

However, an incompatibility is that it deals with `argv` entries and not
command strings.

OSH moves the **responsibility for quoting** into the shell.  Completion
plugins should not do it.

- TODO: describe the `compadjust` builtin.  Derived from a cleanup of the
  `bash-completion` project.

