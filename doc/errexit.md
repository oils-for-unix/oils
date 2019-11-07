---
in_progress: yes
---

set -e / errexit in shell
=========================

<div id="toc">
</div>

<!-- TODO: copy section from OSH manual -->

## Problem

### Solution in Shell

    set +o errexit

    my-complex-func
    status=$?

    other-func
    status=$?

    set -o errexit


### Solution Oil

    shopt -u errexit {
      var status = 0 

      my-complex-func
      setvar status = $?

      other-func
      setvar status = $?
    }

## Style Guide

No:

    if myfunc ...             # internal exit codes would be thrown away

    if ls | wc -l ;           # first exit code would be thrown away


Yes:

    if external-command ...   # e.g. grep
    if builtin ...            # e.g. test
    if $0 myfunc ...          # $0 pattern


The `$0 myfunc` pattern wraps the function in an external command.

<!-- TODO: link to blog post explaining it -->
