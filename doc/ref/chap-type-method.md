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

### search()

Search for the first occurrence of a regex in the string.

    var m = 'hi world' => search(/[aeiou]/)  # search for vowels
    # matches at position 1 for 'i'

Returns a `value.Match()` if it matches, otherwise `null`.

You can start searching in the middle of the string:

    var m = 'hi world' => search(/dot 'orld'/, pos=3)
    # also matches at position 4 for 'o'

The `%start` or `^` metacharacter will only match when `pos` is zero.

(Similar to Python's `re.search()`.)

### leftMatch()

`leftMatch()` is like `search()`, but it checks

    var m = 'hi world' => leftMatch(/[aeiou]/)  # search for vowels
    # doesn't match because h is not a vowel

    var m = 'aye' => leftMatch(/[aeiou]/)
    # matches 'a'

`leftMatch()` Can be used to implement lexers that consome every byte of input.

    var lexer = / <capture digit+> | <capture space+> /

(Similar to Python's `re.match()`.)

## Match

### group()

Returns the string that matched a regex capture group.  Group 0 is the entire
match.

    var m = '10:59' => search(/ ':' <capture d+> /)
    echo $[m => group(0)]  # => ':59'
    echo $[m => group(1)]  # => '59'

Matches can be named with `as NAME`:

    var m = '10:59' => search(/ ':' <capture d+ as minute> /)

And then accessed by the same name:

    echo $[m => group('minute')]  # => '59'

<!--
    var m = '10:59' => search(/ ':' <capture d+ as minutes: int> /)
-->

### start()

Like `group()`, but returns the **start** position of a regex capture group,
rather than its value.

    var m = '10:59' => search(/ ':' <capture d+ as minute> /)
    echo $[m => start(0)]         # => position 2 for ':59'
    echo $[m => start(1)]         # => position 3 for '59'

    echo $[m => start('minute')]  # => position 3 for '59'

### end()

Like `group()`, but returns the **end** position of a regex capture group,
rather than its value.

    var m = '10:59' => search(/ ':' <capture d+ as minute> /)
    echo $[m => end(0)]         # => position 5 for ':59'
    echo $[m => end(1)]         # => position 5 for '59'

    echo $[m => end('minute')]  # => 5 for '59'

## List

### append()

### pop()

### extend()

### indexOf()

Returns the first index of the element in the List, or -1 if it's not present.

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

