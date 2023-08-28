---
default_highlighter: oil-sh
---

Func vs. Proc
==================

- Funcs are in expressions
  - Interior
- Procs are in commands
  - Exterior

See blog: Oils is Exterior-First for some conceptual background.

- Note: procs do everything shell functions can.


<div id="toc">
</div>

## Quick List of Differences

- syntax: commands vs. expr
- name: `proc-with-hyphens`  vs. `funcCamelCase`
- funcs interior, vs procs interior or exterior
- eager vs lazy evaluation of params
- return
- error () -- I guess this is the same?
  - it raises an exception

## Func 

### Signatures

    func f(pos; named) {
    }

### Param Binding

## Proc

### Open Procs

### Signatures

Closed with signature

    proc proc-with-hyphens (word; pos; named; block) {
      = word
      = pos
      = named
      = block
    }

### Param Binding

## Lazy Evaluation of Proc Args


## Shell Functions vs. PRocs

### ARGV

Shell functions:

    f() {
      write -- "$@"
    }


Procs

    proc p {
      write -- @ARGV
    }


# vim: sw=2
