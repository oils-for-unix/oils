---
default_highlighter: oils-sh
---

YSH Style Guide
===============

Here are some recommendations on coding style.

<div id="toc">
</div>

## Your Names

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

For consistency, this style is also OK:

    var MY_CONST = 42

Env vars use `CAP_WORDS`:

    var maxProcs = ENV.MAX_PROCS

### Filenames

    my-script.sh    # runs with /bin/sh and OSH

    my-script.bash  # runs with bash and OSH

    my-script.osh   # runs with OSH

    my-script.ysh   # runs with YSH

## YSH Names

Capital Letters are used for types:

    Null   Bool   Int   Float   Str
    List   Dict
    Proc   Func

Special shell variables:

    PATH   IFS

Global variables that are **silently mutated** by the interpreter start with
`_`:

    _status   _pipeline_status   _reply

As do functions to access such mutable vars:

    _match()  _start()   _end()

Example:

    try false
    if (_status !== 0) {
      echo 'failed'
    }

## Related 

- [Shell Language Idioms](shell-idioms.html)
- [A Feel For YSH Syntax](syntax-feelings.html)


<!--
`kebab-case` is for procs and filenames:

    gc-test   opt-stats   gen-mypy-asdl

    test/spec-runner.ysh

`snake_case` is for local variables:

    proc foo {
      var deploy_dest = 'bar@example.com'
      echo $deploy_dest
    }

`CAPS` are used for global variables built into the shell:

    PATH  IFS  UID  HOSTNAME

External programs also accept environment variables in `CAPS`:

    PYTHONPATH  LD_LIBRARY_PATH

-->
