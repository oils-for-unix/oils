---
default_highlighter: oils-sh
---

YSH Style Guide
===============

Here are some recommendations on coding style.

<div id="toc">
</div>

## Naming

### Procs and Funcs Look Different

    proc kebab-case() {
      echo hi
    }

    func camelCase() {
      echo hi
    }

### Variables

Local variables:

    var snake_case = 42

Hungarian for global "constants":

    var kMyConst = 42   # immutable

    var gMyGlobal = {}  # mutable

Env vars use `CAP_WORDS`:

    var maxProcs = ENV.MAX_PROCS

Variables starting with `_`, like `_status`, are reserved by interpreter:

    try false
    if (_status !== 0) {
      echo 'failed'
    }

### Filenames

    my-script.sh    # runs with /bin/sh and OSH

    my-script.bash  # runs with bash and OSH

    my-script.osh   # runs with OSH

    my-script.ysh   # runs with YSH

## Related 

- [Shell Language Idioms](shell-idioms.html)


