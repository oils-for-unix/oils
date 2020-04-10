---
in_progress: true
---

QSN: A Familiar String Interchange Format
=========================================

Taglines:

- We already use it informally and sloppily, but let's name it and use it
  precisely.  QSN "discovered" and "tightened up", rather than invented.
- QSN Adapts Rust's String Literal Syntax to Express Byte Strings and Unicode
  Better than JSON.
  - Can represent any byte string
  - No Surrogate Pairs for characters like ... (3 in Chinese)

Rough Analogy:

Javacript Literals : JSON  ::  Rust String Literals : QSN

Examples:

    'my favorite song.mp3'
    'bob\t1.0\ncarol\t2.0\n'  # TODO syntax highlight this
    'byte: \xff character: \u{03bc}'

We want a single way to serialize and parse arbitrary byte strings (which may
be encoded in UTF-8 or another encoding.)

- It should be safe to print arbitrary strings to terminals.
- Strings should fit on a line.

TODO: copy content from this page:
<https://github.com/oilshell/oil/wiki/CSTR-Proposal>

<div id="toc">
</div>

## Who Should Use QSN?

- Any command line utility that needs to display filenames (which is most of
  them, e.g. for "file not found")

- A shell.


## Use Case: `set -x` format (`xtrace`)

Unquoted:

```
$ set -x
$ echo a b
+ echo a b
```

We need single quotes `'1 2'` to make arguments with spaces unambiguous:

```
$ set -x
$ x='a b'
$ echo "$x" c
+ echo 'a b' c
```

We need C-escaped strings `$'1\n2'` to make arguments with newlines fit on a
line:

```
$ set -x
$ x=$'a\nb'
$ echo "$x" c
+ echo $'a\nb' 3
```

And to show unprintable characters safely on a terminal:

```
$ set -x
$ x=$'\e\001'
$ echo "$x"
echo $'\x1b\x01'
```

## Design

- The `$''` emitter should be compatible with CSTR.  These all mean the same thing:

```
$'\x01\n'  # shell-compatible (but confusing)
c'\x01\n'  # explicit CSTR
'\x01\n'   # implicit CSTR, which is similar ro Python format
```

## Display Special Characters

### Three options For Displaying Unicode


1. Don't decode UTF-8.  Just show bytes like `'\xce\xbc'`.
2. Decode UTF-8.  This could be useful for showing at a glance if we have valid
   UTF-8 strings.
   a. Show code points like `'\u03bc'`.  ASCII friendly, so better for weird
   debugging situations.
   b. Show them literally.  Depends on the terminal.

### Special Chars Emitted

- `\r` `\n` `\t` `\0` (subset of C and shell; Rust has this)
- Everything else is either `\xFF` or `\u03bc`

## Extensions

- QTSV for tables.  This is a priority for Oil.
- JSON-like dicts and lists.  Someone else should run with this!
  - warning: "\\x00\\'" will confuse people.  Programmers don't understand
    backslashes, and language implementers often don't either.

## Links

- <https://doc.rust-lang.org/reference/tokens.html#string-literals> - Rust is
  precise about it:
  - `\x7F`
  - `\u{03bc}` or `\u{0003bc}`.  This is clearer than the bare format.  And
    there are bugs in octal in bash -- is it 3 or 4 chars, etc.?
    - But bash's `$''` doesn't accept this.
  - `\t` `\r` `\n`
  - `\\`
  - `\0`
