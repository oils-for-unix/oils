---
in_progress: yes
body_css_class: width40 help-body
default_highlighter: oils-sh
preserve_anchor_case: yes
---

YSH Types and Methods
===

This chapter in the [Oils Reference](index.html) describes YSH types and methods.

<div id="toc">
</div>

## Null

## Bool

## Int

## Float

## Str

### find()

### replace()

### startsWith()   

### endsWith()

### trim()   

Respects unicode space.

### trimLeft()   

Respects unicode space.

### trimRight()

Respects unicode space.

### trimPrefix()   

### trimSuffix()

### upper()   

Respects unicode.

### lower()

Respects unicode.

## List

### append()

### pop()

### extend()

### find()

### insert()

### remove()

### reverse()


## Dict

### keys()

### values()

### get()

### erase()

### inc()

### accum()

## Place

### setValue()

A Place is used as an "out param" by calling setValue():

    proc p (out) {
      call out->setValue('hi')
    }

    var x
    p (&x)
    echo x=$x  # => x=hi


## IO

### eval()

Like the `eval` builtin, but useful in pure functions.

### captureStdout()

Like `$()`, but useful in pure functions.

### promptVal()

An API the wraps the `$PS1` language.  For example, to simulate `PS1='\w\$ '`:

    func renderPrompt(io) {    
      var parts = []
      call parts->append(io->promptval('w'))  # pass 'w' for \w
      call parts->append(io->promptval('$'))  # pass '$' for \$
      call parts->append(' ')
      return (join(parts))
    }


### time()

TODO: Depends on system clock.

### strftime()

TODO: Like the awk function, this takes an timestamp directly.

In other words, it calls C localtime() (which depends on the time zone
database), and then C strftime().

### glob()

TODO: The free function glob() actually does I/O.  Although maybe it doesn't
fail?

