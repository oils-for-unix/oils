---
in_progress: yes
body_css_class: width40 help-body
default_highlighter: oils-sh
preserve_anchor_case: yes
---

Types and Methods
===

This chapter in the [Oils Reference](index.html) describes YSH types and methods.

There are also two OSH types for bash compatibility.

<div id="toc">
</div>

## Null

## Bool

## Int

## Float

## Str

### find()

### replace()

Replace substrings with a given string.

    = mystr => replace("OSH", "YSH")

Or match with an Eggex.

    = mystr => replace(/ d+ /, "<redacted>")  # => "code is <redacted>"

Refer to Eggex captures with replacement expressions. Captured values can be
referenced with `$1`, `$2`, etc.

    var mystr = "1989-06-08"
    var pat = / <capture d{4}> '-' <capture d{2}> '-' <capture d{2}> /
    = mystr => replace(pat, ^"Year: $1, Month: $2, Day: $3")

Captures can also be named.

    = mystr2 => replace(/ <capture digit{4} as year : int> /, ^"$[year + 1]")

`$0` refers to the entire capture itself in a substitution string.

    var mystr = "replace with mystr => replace()"
    = mystr => replace(/ alpha+ '=>' alpha+ '()' /, ^"<code>$0</code>")
    # => "replace with <code>mystr => replace()</code>"

In addition to captures, other variables can be referenced within a replacement
expression.

    = mystr => replace(/ <capture alpha+> /, ^"$1 and $anotherVar")

To limit the number of replacements, pass in a named count argument. By default
the count is `-1`. For any count in [0, MAX_INT], there will be at most count
replacements. Any negative count means "replace all" (ie. `count=-2` behaves
exactly like `count=-1`).

    var mystr = "bob has a friend named bob"
    = mystr => replace("bob", "Bob", count=1)   # => "Bob has a friend named bob"
    = mystr => replace("bob", "Bob", count=-1)  # => "Bob has a friend named Bob"

The following matrix of signatures are supported by `replace()`:

    s => replace(string_val, subst_str)
    s => replace(string_val, subst_expr)
    s => replace(eggex_val, subst_str)
    s => replace(eggex_val, subst_expr)

### startsWith()

Checks if a string starts with a pattern, returning true if it does or false if
it does not.

    = b'YSH123' => startsWith(b'YSH')  # => true
    = b'123YSH' => startsWith(b'YSH')  # => false
    = b'123YSH' => startsWith(/ d+ /)  # => true
    = b'YSH123' => startsWith(/ d+ /)  # => false

Matching is done based on bytes, not runes.

    = b'\yce\ya3'                 # => (Str)   "Σ"
    = 'Σ' => startsWith(b'\yce')  # => true
    = 'Σ' => endsWith(b'\ya3')    # => true

### endsWith()

Like 'startsWith()` but returns true if the _end_ of the string matches.

    = b'123YSH' => endsWith("YSH")  # => true
    = b'YSH123' => endsWith(/ d+ /) # => true

### trim()

Removes characters matching a pattern from the start and end of a string.
With no arguments, whitespace is removed. When given a string or eggex pattern,
that pattern is removed if it matches the start or end.

    = b' YSH\n'    => trim()        # => "YSH"
    = b'xxxYSHxxx' => trim('xxx')   # => "YSH"
    = b'xxxYSH   ' => trim('xxx')   # => "YSH   "
    = b'   YSHxxx' => trim('xxx')   # => "   YSH"
    = b'   YSH   ' => trim('xxx')   # => "   YSH   "
    = b'123YSH456' => trim(/ d+ /)  # => "YSH"

#### A note on whitespace

When stripping whitespace, Oils decodes the bytes in string as utf-8
characters. Only the following Unicode codepoints are considered to be
whitespace.

 - U+0009 -- Horizontal tab (`\t`)
 - U+000A -- Newline (`\n`)
 - U+000B -- Vertical tab (`\v`)
 - U+000C -- Form feed (`\f`)
 - U+000D -- Carriage return (`\r`)
 - U+0020 -- Normal space
 - U+00A0 -- No-break space `<NBSP>`
 - U+FEFF -- Zero-width no-break space `<ZWNBSP>`

While the Unicode standard defines other codepoints as being spaces, Oils
limits itself to just these codepoints so that the specification is stable, and
doesn't depend on an external standard that has reclassify characters.

### trimStart()

Like `trim()` but only removes characters from the _start_ of the string.

    = b' YSH\n'    => trimStart()        # => "YSH\n"
    = b'xxxYSHxxx' => trimStart(b'xxx')  # => "YSHxxx"
    = b'123YSH456' => trimStart(/ d+ /)  # => "YSH456"

### trimEnd()

Like `trim()` but only removes characters from the _end_ of the string.

    = b' YSH\n'    => trimEnd()        # => " YSH"
    = b'xxxYSHxxx' => trimEnd(b'xxx')  # => "YxxxSH"
    = b'123YSH456' => trimEnd(/ d+ /)  # => "123YSH"

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

`leftMatch()` Can be used to implement lexers that consume every byte of input.

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

Add an element to a list.

    var fruits = :|apple banana pear|
    call fruits->append("orange")
    echo @fruits  # => apple banana pear orange

### pop()

remove an element from a list and return it.

    var fruits = :|apple banana pear orange|
    var last = fruits->pop()  # "orange" is removed AND returned
    echo $last                # => orange
    echo @fruits              # => apple banana pear

### extend()

Extend an existing list with the elements of another list.

    var foods = :|cheese chocolate|
    var fruits = :|apple banana|
    call foods->extend(fruits)
    echo @foods  # => cheese chocolate apple banana

### indexOf()

Returns the first index of the element in the list, or -1 if it's not present.

    var names = :| Jane Peter Joana Sam |
    echo $[names => indexOf("Sam")]    # => 3
    echo $[names => indexOf("Simon")]  # => -1

### insert()

### remove()

### reverse()

Reverses a list in place.

    var fruits = :|apple banana pear|
    call fruits->reverse()
    echo @fruits  # => pear banana apple

## Dict

### keys()

Returns all existing keys from a dict as a list of strings.

    var en2fr = {
      hello: "bonjour",
      friend: "ami",
      cat: "chat"
    }
    = en2fr => keys()
    # => (List 0x4689)   ["hello","friend","cat"]

### values()

Similar to `keys()`, but returns the values of the dictionary.

    var person = {
      name: "Foo",
      age: 25,
      hobbies: :|walking reading|
    }
    = en2fr => values()]
    # => (List 0x4689)   ["Foo",25,["walking","reading"]]

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


## OSH

### BashArray

TODO

### BashAssoc

TODO
