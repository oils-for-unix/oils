---
default_highlighter: oil-sh
---

Tracing Execution in Oil (xtrace)
==================================

Examples:


    shopt -s xtrace_rich   # stack and processes?  part of oil:basic

    PS4='${X_indent}${X_prefix} '


- X_indent is empty unless xtrace_pretty
- X_prefix contains PID when it's pretty
  - -+
  - or it can be: ${X_punct}${X_prefix} so you can add BASH_SOURCE, FUNCNAME,
    LINENO.
    - TODO: Add OIL_SOURCE  as alias?
      and OIL_PID?  or maybe OIL_CURRENT_PID.  or maybe getpid() is better
      - distinguish between functions and values
    - Also #$SECONDS for timing


## Parsing It

- I think you can specify a regular language


