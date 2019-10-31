---
in_progress: yes
---

set -e / errexit in shell
=========================

<div id="toc">
</div>

Problem:

Solution in Shell


Solution Oil:


shopt -u errexit {
  my-big-func 
  other-func

  var status = $?
}


shopt -u errexit {
  var status = 0 

  my-big-func || setvar status = $?
  other-func || setvar status = $?

  var status = $?
}

## Style Guide

No:

  if myfunc ...

  if ls | wc -l ;   # pipelines, no


Yes:

  if external-command ...  (grep)
  if builtin  (test)
  if $0 myfunc


It behaves just like an external command.


