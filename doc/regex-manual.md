Egg Expressions (Oil Regexes)
=============================

## Intro

Oil has a new regex syntax, which appears between the `/ /` delimiters.

    if (mystr ~ /d+ '.' d+/) {   
      echo 'mystr looks like a number N.M'
    }

It's different than POSIX or Perl syntax, but it's intended to be familiar.

It's called an "Eggex" because it's a similar to the regexes you already know,
but different.

Why?

- Eggexes let you name **subpatterns** and compose them, which makes them more
  readable and testable.
- Their **syntax** is vastly simpler because literal characters are **quoted**,
  and operators are not.  For example, `^` no longer means three totally
  different things.  See the critique at the end of this doc.
- bash and awk use the limited and verbose POSIX ERE syntax, while eggexes are
  more expressive and (in some cases) Perl-like.
- They're designed to be **translated to any regex dialect**.  Right now, it
  translates to ERE so you can use them with common Unix tools:
  - `egrep` (`grep -E`)
  - `awk`
  - GNU `sed --regexp-extended`
  - PCRE syntax is the second most important target.
- They're **statically parsed** in Oil, so:
  - You can get **syntax errors** at parse time.  In contrast, if you embed a
    regex in a string, you don't get syntax errors until runtime.
  - The eggex is part of the "lossless syntax tree", which means you can do
    linting, formatting, and refactoring on eggexes, just like any other type
    of code.
- Eggexes are more fun than regexes!

### Example of Pattern Reuse

Here's a longer example:

    $ var D = / digit{1,3} /  # Reuse this subpattern; 'digit' is long for 'd'
    $ var ip_pat = / @D '.' @D '.' @D '.' @D /

    $ echo $ip_pat            # This Eggex compiles to an ERE
    [[:digit:]]{1,3}\.[[:digit:]]{1,3}\.[[:digit:]]{1,3}\.[[:digit:]]{1,3}

This means you can use it in a very simple way:

    $ egrep $ip_pat foo.txt

TODO: You should also be able to inline patterns like this:

    egrep $/d+/ foo.txt

### Philosophy

- Eggexes can express a superset of POSIX and Perl syntax.
- The language is designed for "dumb", one-to-one, **syntactic** translations.
  That is, translation doesn't rely on understanding the **semantics** of
  regexes.  This is because regex implementations have many corner cases and
  incompatibilities, with regard to Unicode, `NUL` bytes, etc.

## The Expression language

Eggexes have a consistent syntax:

- Single characters are unadorned: `dot`, `space`, or `s`
- A sequence of multiple characters looks like `'lit'`, `$var`, etc.
- Constructs that match **zero** characters look like `%start %end` 
- Entire subpatterns (which may contain alternation, repetition, etc.) look
  like `@var_name`.  Important: these are **spliced** as syntax trees, not
  strings, so you **don't** need to think about quoting.

For example, it's easy to see that these patterns all match **three** characters:

    / d d d /
    / digit digit digit /
    / dot dot dot /
    / word space word /
    / 'ab' space /
    / 'abc' /

And that these patterns match **two**:

    / %start w w /
    / %start 'if' /
    / d d %end /

And that you have to look up the definition of `D` to know how many characters
this matches:

    / %start @D %end /

Constructs like `. ^ $ \< \>` are deprecated because they break these rules.

### Primitives

#### . is now `dot`

But `.` is still accepted.  It usually matches any character except a newline,
although this changes based on flags (e.g. `dotall`, `unicode`).

#### Classes are unadorned: `word`, `w`, `alnum`

We accept both Perl and POSIX classes.

- Perl
- POSIX

#### Zero-width Assertions Look Like `%this`

- `%start` is `^`
- `%end` is `$`
- `%start_word` is GNU `\<`
- `%end_word` is GNU `\>`

#### Literals

- `'abc'`
- `"xyz $var"`
- `$mychars`
- `${otherchars}`

### Compound Structures

#### Sequence and Alternation Are Unchanged

- `x y` matches `x` and `y` in sequence
- `x | y` matches `x` or `y`

You can also write a more Pythonic alternative: `x or y`.

#### Repetition Is Unchanged In Common Cases, and Better in Rare Cases

Repetition is just like POSIX ERE or Perl:

- `x?`, `x+`, `x*` 
- `x{3}`, `x{1,3}`

We've reserved syntactic space for PCRE and Python variants:

- lazy/non-greedy: `x{L +}`, `x{L 3,4}`
- possessive: `x{P +}`, `x{P 3,4}`

#### Negation Consistently Uses ~

You can negated named char classes:

    / ~digit /

and char class literals:

    / ~[ a-z A-Z ] /

Sometimes you can do both:

    / ~[ ~digit ] /  # translates to /[^\D]/ in PCRE
                     # error in ERE because it can't be expressed


You can also negate "regex modifiers" / compilation flags:

    / word ; ignorecase /   # flag on
    / word ; ~ignorecase /  # flag off
    / word ; ~i /           # abbreviated

In contrast, regexes have many confusing syntaxes for negation:

    [^abc] vs. [abc]
    [[^:digit:]] vs. [[:digit:]]

    \D vs. \d

    /[x]/-i vs /[x]/i

#### Splicing

New in Eggex!  You can reuse patterns with `@pattern_name`.

See the example at the front of this document.

This is similar to how `lex` and `re2c` work.

#### Grouping, Capturing

Capture with `()`:

    ('foo' or 'bar')+   # Becomes M.group(1)

Named capture

    ('foo' or 'bar' as myvar)  # Becomes M.group('myvar')

Group with `:()`

    :('foo' or 'bar')

See note below: POSIX ERE has no non-capturing groups.

#### Character Class Literals

Example:

    [ a-f 'A'-'F' \xFF \u0100 \n \\ \' \" \0 ]

Terms:

- Ranges: `a-f` or `'A' - 'F'`
- Literals: `\n`, `\x01`, `\u0100`, etc.
- Sets specified as strings:
  - `'abc'`
  - `"xyz"`
  - `$mychars`
  - `${otherchars}`

Only letters, numbers, and the underscore may be unquoted:

    /['a'-'f' 'A'-'F' '0'-'9']/
    /[a-f A-F 0-9]/                # Equivalent to the above

    /['!' - ')']/  # Syntactically correct range
    /[!-)]/      # Syntax Error

Ranges must be separated by spaces:

NO:

    /[a-fA-F0-9]/

YES:

    /[a-f A-f 0-9]/



### Flags and Translation Preferences

Flags or "regex modifiers" appear after the first semicolon:

    / digit+ ; ignorecase /

A translation preference appears after the second semicolon.  It controls what
regex syntax the eggex is translated to by default.

    / digit+ ; ignorecase ; ERE /

This expression has a translation preference, but no flags:

    / digit+ ;; ERE /


### Backtracking Constructs (Discouraged)

All the "dangerous" concepts begin with `!`.

If you want to translate to PCRE, you can use these.


    !REF 1
    !REF name

    !AHEAD( d+ )
    !NOT_AHEAD( d+ )
    !BEHIND( d+ )
    !NOT_BEHIND( d+ )

    !ATOMIC( d+ )

### Multiline Syntax

You can spread regexes over multiple lines and add comments:

    var x = ///
      digit{4}   # year e.g. 2001
      '-'
      digit{2}   # month e.g. 06
      '-'
      digit{2}   # day e.g. 31
    ///


(Not yet implemented in Oil.)

### Language Reference

- See Oil Grammar
- See frontend/syntax.asdl

## The Oil API

TODO:

    if (x ~ pat) {
    }

    if (for pat in mystr) {
    }

Link to another doc?

## Style Notes

### Use Character Literals Rather than C-Escaped Strings

NO:

    / c'foo\tbar' /   # Match 7 characters including a tab, but it's hard to read
    / r'foo\tbar' /   # The string must contain 8 chars including '\' and 't'

YES:

    # Instead, Take advantage of char literals and implicit regex concatenation
    / 'foo' \t 'bar' /
    / 'foo' \\ 'tbar' /


## ERE Limitations

### Surround Repeated Strings with a Capturing Group ()

NO:

    'foo'+ 
    $string_with_many_chars+

YES:

    ('foo')+
    ($string_with_many_chars)+

### Unicode Character Literals Can't Be in Char Class Literals

NO:

    # ERE can't represent this, and 2 byte utf-8 encoding could be confused
    with 2 bytes.
    / [ \u0100 ] /

YES:

    # This is accepted -- it's clear it matches one of two bytes.
    / [ \x61 \xFF ] /

### ] is Confusing in Char Class Literals

ERE wants it like this:

    []abc]

These don't work:

    [abc\]]
    [abc]]

So in Oil you have to write it like this:

YES:

    / [ ']' 'abc'] /

NO:

    / [ 'abc' ']' ] /
    / [ 'abc]' ] /

Since we do a dumb syntactic translation, we can't detect whether it's on the
front or back.  You have to put it in the right place.


## Critiques

### Existing Regex Syntax

Regexes are hard to read because the **same symbol can mean many things**.

`^` could mean:

- Start of the string/line
- Negated character class like `[^abc]`
- Literal character `^` like `[abc^]`

`\` is used in:

- Character classes like `\w` or `\d`
- Zero-width assertions like `\b`
- Escaped characters like `\n`
- Quoted characters like `\+`

`?` could mean:

- optional: `a?`
- lazy match: `a+?`
- some other kind of grouping:
  - `(?P<named>\d+)`
  - `(?:noncapturing)`

In Oil, each construct has a distinct syntax.

### Oil is Shorter than Bash

Bash:

    if [[ $x =~ '[[:digit:]]+' ]]; then
      echo 'x looks like a number
    fi

Compare with Oil:

    if (x ~ /digit+/) {
      echo 'x looks like a number'
    }

### And Perl

It's also shorter than Perl because we can write

    x ~ /d+/

rather than:

    $x =~ /\d+/

The Perl expression has three more punctuation characters:

- We don't need sigils in expression mode
- The operator is `~` not `=~`
- Named character classes are unadorned like `d`.  If that's too short, you can
  also write `digit`.

## Notes

### Eggexes In Other Languages

The eggex syntax can be incorporated into other tools and shells.  It's
designed to be separate from Oil -- hence the separate name.

Notes:

- Single quoted string literals should **disallow** internal backslashes, and
  treat all other characters literally..  Instead, users can write `/ 'foo' \t
  'sq' \' bar \n /` &mdash; i.e. implicit concatenation of strings and
  characters, described above.
- To make eggexes portable between languages, Don't use the host language's
  syntax for string literals (at least for single-quoted strings).

### Pronunciation

If "eggex" sounds too much like "regex" to you, simply say "egg expression".
It won't be confused with "regular expression" or "regex".


### TODO

Multiline syntax:

    var x = ///
      abc   # TODO: comments
      a+
    ///

Regex flags:

    $/ d+ ; ignorecase ~multiline/
    $/ d+ ; i ~m/

Translation preference:

    $/ d+ ; i m ; PCRE/     %ERE, %PCRE, %Python

    echo $/ d+ ; ignorecase ; ERE/    # prints [[:digit:]]
    echo $/ d+ ; ignorecase ; perl/   # prints \d+
    echo $/ d+ ;; python/             # prints \d+

Inline syntax:

  grep -P $/d+ ;; perl/ f

Zero-width asertions:

- %start_word %end_word  for < and >

API:

- `while` or `for` loop, saving state (like "sticky" bit)
- `sub()` (and `=>` syntax)
- `findall()`
- `split()`

Other ideas: either/or syntax

