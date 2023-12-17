---
default_highlighter: oils-sh
---

Egg Expressions (YSH Regexes)
=============================

YSH has a new syntax for patterns, which appears between the `/ /` delimiters:

    if (mystr ~ /d+ '.' d+/) {   
      echo 'mystr looks like a number N.M'
    }

These patterns are intended to be familiar, but they differ from POSIX or Perl
expressions in important ways.  So we call them *eggexes* rather than
*regexes*!

<!-- cmark.py expands this -->
<div id="toc">
</div>

## Why Invent a New Language?

- Eggexes let you name **subpatterns** and compose them, which makes them more
  readable and testable.
- Their **syntax** is vastly simpler because literal characters are **quoted**,
  and operators are not.  For example, `^` no longer means three totally
  different things.  See the critique at the end of this doc.
- bash and awk use the limited and verbose POSIX ERE syntax, while eggexes are
  more expressive and (in some cases) Perl-like.
- They're designed to be **translated to any regex dialect**.  Right now, the
  YSH shell translates them to ERE so you can use them with common Unix tools:
  - `egrep` (`grep -E`)
  - `awk`
  - GNU `sed --regexp-extended`
  - PCRE syntax is the second most important target.
- They're **statically parsed** in YSH, so:
  - You can get **syntax errors** at parse time.  In contrast, if you embed a
    regex in a string, you don't get syntax errors until runtime.
  - The eggex is part of the [lossless syntax tree][], which means you can do
    linting, formatting, and refactoring on eggexes, just like any other type
    of code.
- Eggexes support **regular languages** in the mathematical sense, whereas
  regexes are **confused** about the issue.  All nonregular eggex extensions
  are prefixed with `!!`, so you can visually audit them for [catastrophic
  backtracking][backtracking].  (Russ Cox, author of the RE2 engine, [has
  written extensively](https://swtch.com/~rsc/regexp/) on this issue.)
- Eggexes are more fun than regexes!

[backtracking]: https://blog.codinghorror.com/regex-performance/

[lossless syntax tree]: http://www.oilshell.org/blog/2017/02/11.html

### Example of Pattern Reuse

Here's a longer example:

    # Define a subpattern.  'digit' and 'd' are the same.
    $ var D = / digit{1,3} /

    # Use the subpattern
    $ var ip_pat = / D '.' D '.' D '.' D /

    # This eggex compiles to an ERE
    $ echo $ip_pat
    [[:digit:]]{1,3}\.[[:digit:]]{1,3}\.[[:digit:]]{1,3}\.[[:digit:]]{1,3}

This means you can use it in a very simple way:

    $ egrep $ip_pat foo.txt

TODO: You should also be able to inline patterns like this:

    egrep $/d+/ foo.txt

### Design Philosophy

- Eggexes can express a **superset** of POSIX and Perl syntax.
- The language is designed for "dumb", one-to-one, **syntactic** translations.
  That is, translation doesn't rely on understanding the **semantics** of
  regexes.  This is because regex implementations have many corner cases and
  incompatibilities, with regard to Unicode, `NUL` bytes, etc.

### The Expression Language Is Consistent

Eggexes have a consistent syntax:

- Single characters are unadorned, in lowercase: `dot`, `space`, or `s`
- A sequence of multiple characters looks like `'lit'`, `$var`, etc.
- Constructs that match **zero** characters look like `%start`, `%word_end`, etc. 
- Entire subpatterns (which may contain alternation, repetition, etc.) are in
  uppercase like `HexDigit`.  Important: these are **spliced** as syntax trees,
  not strings, so you **don't** need to think about quoting.

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

And that you have to look up the definition of `HexDigit` to know how many
characters this matches:

    / %start HexDigit %end /

Constructs like `. ^ $ \< \>` are deprecated because they break these rules.

## Expression Primitives

### `.` Is Now `dot`

But `.` is still accepted.  It usually matches any character except a newline,
although this changes based on flags (e.g. `dotall`, `unicode`).

### Classes Are Unadorned: `word`, `w`, `alnum`

We accept both Perl and POSIX classes.

- Perl:
  - `d` or `digit`
  - `s` or `space`
  - `w` or `word`
- POSIX
  - `alpha`, `alnum`, ...

### Zero-width Assertions Look Like `%this`

- POSIX
  - `%start` is `^`
  - `%end` is `$`
- PCRE:
  - `%input_start` is `\A`
  - `%input_end` is `\z`
  - `%last_line_end` is `\Z`
- GNU ERE extensions:
  - `%word_start` is `\<`
  - `%word_end` is `\>`

### Literals Are Quoted And Can Use String Variables

- `'abc'`
- `"xyz $var"`
- `$mychars`
- `${otherchars}`

## Compound Expressions

### Sequence and Alternation Are Unchanged

- `x y` matches `x` and `y` in sequence
- `x | y` matches `x` or `y`

You can also write a more Pythonic alternative: `x or y`.

### Repetition Is Unchanged In Common Cases, and Better in Rare Cases

Repetition is just like POSIX ERE or Perl:

- `x?`, `x+`, `x*` 
- `x{3}`, `x{1,3}`

We've reserved syntactic space for PCRE and Python variants:

- lazy/non-greedy: `x{L +}`, `x{L 3,4}`
- possessive: `x{P +}`, `x{P 3,4}`

### Negation Consistently Uses !

You can negate named char classes:

    / !digit /

and char class literals:

    / ![ a-z A-Z ] /

Sometimes you can do both:

    / ![ !digit ] /  # translates to /[^\D]/ in PCRE
                     # error in ERE because it can't be expressed


You can also negate "regex modifiers" / compilation flags:

    / word ; ignorecase /   # flag on
    / word ; !ignorecase /  # flag off
    / word ; !i /           # abbreviated

In contrast, regexes have many confusing syntaxes for negation:

    [^abc] vs. [abc]
    [[^:digit:]] vs. [[:digit:]]

    \D vs. \d

    /\w/-i vs /\w/i

### Splice Other Patterns `@var_name` or `UpperCaseVarName`

This allows you to reuse patterns.  Using uppercase variables:

    var D = / digit{3} /

    var ip_addr = / D '.' D '.' D '.' D /

Using normal variables:

    var part = / digit{3} /

    var ip_addr = / @part '.' @part '.' @part '.' @part /

This is similar to how `lex` and `re2c` work.

### Group and Capture With `()` and `<>`

Group with `(pat)`

    ('foo' | 'bar')+

See note below: When translating to POSIX ERE, grouping becomes a capturing
group.  POSIX ERE has no non-capturing groups.

Capture with `<capture pat>`:

    <capture d+>           # Becomes _group(1)

Add a variable after `as` for named capture:

    <capture d+ as myvar>  # Becomes _group('myvar')

### Character Class Literals Use `[]`

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
    /[a-f A-F 0-9]/              # Equivalent to the above

    /['!' - ')']/                # Correct range
    /[!-)]/                      # Syntax Error

Ranges must be separated by spaces:

No:

    /[a-fA-F0-9]/

Yes:

    /[a-f A-f 0-9]/

### Backtracking Constructs Use `!!` (Discouraged)

If you want to translate to PCRE, you can use these.

    !!REF 1
    !!REF name

    !!AHEAD( d+ )
    !!NOT_AHEAD( d+ )
    !!BEHIND( d+ )
    !!NOT_BEHIND( d+ )

    !!ATOMIC( d+ )

Since they all begin with `!!`, You can visually audit your code for potential
performance problems.

## Outside the Expression language

### Flags and Translation Preferences (`;`)

Flags or "regex modifiers" appear after a semicolon:

    / digit+ ; ignorecase /

A translation preference is specified with a symbol like `%pref`.  It controls
what regex syntax the eggex is translated to by default.

    / digit+ ; %ERE /                # translates to [[:digit:]]+
    / digit+ ; %python /             # translates to \d+

Flags and translation preferences together:

    / digit+ ; ignorecase %python /  # translates to (?i)\d+

### Multiline Syntax

You can spread regexes over multiple lines and add comments:

    var x = ///
      digit{4}   # year e.g. 2001
      '-'
      digit{2}   # month e.g. 06
      '-'
      digit{2}   # day e.g. 31
    ///


(Not yet implemented in YSH.)

### The YSH API

See [YSH regex API](ysh-regex-api.html) for details.

In summary, YSH has Perl-like conveniences with an `~` operator:

    var s = 'on 04-01, 10-31'
    var pat = /<capture d+ as month> '-' <capture d+ as day>/

    if (s ~ pat) {       # search for the pattern
      echo $[_group(1)]  # => 04
    }

It also has an explicit and powerful Python-like API with the `search()` and
leftMatch()` methods on strings.

    var m = s => search(pat, pos=8)  # start searching at a position
    if (m) {
      echo $[m => group(1)]  # => 10
    }

### Language Reference

- See bottom of the [YSH Expression Grammar]($oils-src:ysh/grammar.pgen2) for
  the concrete syntax.
- See the bottom of [frontend/syntax.asdl]($oils-src:frontend/syntax.asdl) for
  the abstract syntax.

## Usage Notes

### Use character literals rather than C-Escaped strings

No:

    / $'foo\tbar' /   # Match 7 characters including a tab, but it's hard to read
    / r'foo\tbar' /   # The string must contain 8 chars including '\' and 't'

Yes:

    # Instead, Take advantage of char literals and implicit regex concatenation
    / 'foo' \t 'bar' /
    / 'foo' \\ 'tbar' /


## POSIX ERE Limitations

### Repetition of Strings Requires Grouping

Repetitions like `* + ?` apply only to the last character, so literal strings
need extra grouping:


No:

    'foo'+ 

Yes:

    <capture 'foo'>+

Also OK:

    ('foo')+  # this is a CAPTURING group in ERE

This is necessary because ERE doesn't have non-capturing groups like Perl's
`(?:...)`, and Eggex only does "dumb" translations.  It doesn't silently insert
constructs that change the meaning of the pattern.

### Unicode char literals are limited in range

ERE can't represent this set of 1 character reliably:

    / [ \u{0100} ] /      # This char is 2 bytes encoded in UTF-8

These sets are accepted:

    / [ \u{1} \u{2} ] /   # set of 2 chars
    / [ \x01 \x02 ] ] /   # set of 2 bytes

They happen to be identical when translated to ERE, but may not be when
translated to PCRE.

### Don't put non-ASCII bytes in string sets in char classes

This is a sequence of characters:

    / $'\xfe\xff' /

This is a **set** of characters that is illegal:

    / [ $'\xfe\xff' ] /  # set or sequence?  It's confusing

This is a better way to write it:

    / [ \xfe \xff ] /  # set of 2 chars

### Char class literals: `^ - ] \`

The literal characters `^ - ] \` are problematic because they can be confused
with operators.

- `^` means negation
- `-` means range
- `]` closes the character class
- `\` is usually literal, but GNU gawk has an extension to make it an escaping
  operator

The Eggex-to-ERE translator is smart enough to handle cases like this:

    var pat = / ['^' 'x'] / 
    # translated to [x^], not [^x] for correctness

However, cases like this are a fatal runtime error:

    var pat1 = / ['a'-'^'] /
    var pat2 = / ['a'-'-'] /

## Critiques

### Regexes Are Hard To Read

... because the **same symbol can mean many things**.

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

With egg expressions, each construct has a **distinct syntax**.

### YSH is Shorter Than Bash

Bash:

    if [[ $x =~ '[[:digit:]]+' ]]; then
      echo 'x looks like a number
    fi

Compare with YSH:

    if (x ~ /digit+/) {
      echo 'x looks like a number'
    }

### ... and Perl

Perl:

    $x =~ /\d+/

YSH:

    x ~ /d+/


The Perl expression has three more punctuation characters:

- YSH doesn't require sigils in expression mode
- The match operator is `~`, not `=~`
- Named character classes are unadorned like `d`.  If that's too short, you can
  also write `digit`.

## Design Notes

### Eggexes In Other Languages

The eggex syntax can be incorporated into other tools and shells.  It's
designed to be separate from YSH -- hence the separate name.

Notes:

- Single quoted string literals should **disallow** internal backslashes, and
  treat all other characters literally..  Instead, users can write `/ 'foo' \t
  'sq' \' bar \n /` &mdash; i.e. implicit concatenation of strings and
  characters, described above.
- To make eggexes portable between languages, Don't use the host language's
  syntax for string literals (at least for single-quoted strings).

### Backward Compatibility

Eggexes aren't backward compatible in general, but they retain some legacy
operators like `^ . $` to ease the transition.  These expressions are valid
eggexes **and** valid POSIX EREs:

    .*
    ^[0-9]+$
    ^.{1,3}|[0-9][0-9]?$

## FAQ

### The Name Sounds Funny.

If "eggex" sounds too much like "regex" to you, simply say "egg expression".
It won't be confused with "regular expression" or "regex".

### How Do Eggexes Compare with [Perl 6 Regexes][perl6-regex] and the [Rosie Pattern Language][rosie]?

All three languages support pattern composition and have quoted literals.  And
they have the goal of improving upon Perl 5 regex syntax, which has made its
way into every major programming language (Python, Java, C++, etc.)

The main difference is that Eggexes are meant to be used with **existing**
regex engines.  For example, you translate them to a POSIX ERE, which is
executed by `egrep` or `awk`.  Or you translate them to a Perl-like syntax and
use them in Python, JavaScript, Java, or C++ programs.

Perl 6 and Rosie have their **own engines** that are more powerful than PCRE,
Python, etc.  That means they **cannot** be used this way.

[rosie]: https://rosie-lang.org/

[perl6-regex]: https://docs.perl6.org/language/regexes

### What About Eggex versus Parsing Expression Grammars?  (PEGs)

The short answer is that they can be complementary: PEGs are closer to
**parsing**, while eggex and [regular languages]($xref:regular-language) are
closer to **lexing**.  Related:

- [When Are Lexer Modes Useful?](https://www.oilshell.org/blog/2017/12/17.html)
- [Why Lexing and Parsing Should Be
  Separate](https://github.com/oilshell/oil/wiki/Why-Lexing-and-Parsing-Should-Be-Separate) (wiki)

The PEG model is more resource intensive, but it can recognize more languages,
and it can recognize recursive structure (trees).

### Why Don't `dot`, `%start`, and `%end` Have More Precise Names?

Because the meanings of `.` `^` and `$` are usually affected by regex engine
flags, like `dotall`, `multiline`, and `unicode`.

As a result, the names mean nothing more than "however your regex engine
interprets `.` `^` and `$`".

As mentioned in the "Philosophy" section above, eggex only does a superficial,
one-to-one translation.  It doesn't understand the details of which characters
will be matched under which engine.

### Where Do I Send Feedback?

Eggexes are implemented in YSH, but not yet set in stone.

Please try them, as described in [this
post](http://www.oilshell.org/blog/2019/08/22.html) and the
[README]($oils-src:README.md), and send us feedback!

You can create a new post on [/r/oilshell](https://www.reddit.com/r/oilshell/)
or a new message on `#oil-discuss` on <https://oilshell.zulipchat.com/> (log in
with Github, etc.)
