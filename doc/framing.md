---
in_progress: yes
---

Solutions to the Framing Problem
================================

How do you write multiple **records** to a pipe, and how do you read them?

You need a way of delimiting them.  Let's call this the "framing problem"
&mdash; a term borrowed from network engineering.

This doc categorizes different formats, and shows how you handle them in YSH.

YSH is meant for writing correct shell programs.

<div id="toc">
</div>

## A Length Prefix

[Netstrings][netstring] are a simple format defined by Daniel J Bernstein.

    3:foo,  # ASCII length, colon, byte string, comma

[netstring]: https://en.wikipedia.org/wiki/Netstring

This format is easy to implement, and efficient to read and write.

But the encoded output may contain binary data, which isn't readable by a human
using a terminal (or GUI).  This is significant!

---

TODO: Implement `read --netstr` and `write --netstr`

<!--
Like [J8 Notation][], this format is "8-bit clean", but:

- A netstring encoder is easier to write than a QSN encoder.  This may be
  useful if you don't have a library handy.
- It's more efficient to decode, in theory.
-->

## Solutions Using a Delimiter

Now let's look at traditional Unix solutions, and their **problems**.

### Fixed Delimiter: Newline or `NUL` byte

In traditional Unix, newlines delimit "records".  Here's how you read them in
shell:

    while IFS='' read -r; do  # confusing idiom!
      echo line=$REPLY
      break                   # remaining bytes are still in the pipe
    done

YSH has a simpler idiom:

    while read --raw-line {   # unbuffered
      echo line=$_reply
      break                   # remaining bytes are still in the pipe
    }

Or you can read all lines:

    for line in (stdin) {     # buffered
      echo line=$line
      break                   # remaining bytes may be lost in a buffer
    }

**However**, in Unix, all of these strings may have newlines:

- filenames
- items in `argv`
- values in `environ`

---

But these C-style strings can't contain the `NUL` byte, aka `\0`.  So GNU tools
have evolved support for another format:

    find . -print0  # write data
    xargs -0        # read data; also --null
    grep -z         # read data; also --null-data
    sort -z         # read data; also --zero-terminated
                    # (Why are all the names different?)

In Oils, we added a `-0` flag to `read` to understands this:

    $ find . -print0 | { read -0 x; echo $x; read -0 x; echo $x; }
    foo  # could contain newlines!
    bar

### Chosen Delimiter: Here docs and multipart MIME

Shell has has here docs that look like this:

    cat <<EOF
    the string EOF
    can't start a line
    EOF

So you **choose** the delimiter, with the "word" you write after `<<`.

---

Similarly, when your browser POSTs a form, it uses [MIME multipart message
format](https://en.wikipedia.org/wiki/MIME#Multipart_messages):

    MIME-Version: 1.0
    Content-Type: multipart/mixed; boundary=frontier
    
    This is a message with multiple parts in MIME format.
    --frontier
    Content-Type: text/plain
    
    This is the body of the message.
    --frontier

So again, you **choose** a delimiter with `boundary=frontier`, and then you
must recognize it later in the message.

## C-Style `\` escaping allows arbitrary bytes

[JSON][] can express strings with newlines:

    "line 1 \n line 2"

It can also express the zero code point, which isn't the same as NUL byte:

    "zero code point \u0000"

[J8 Notation][] is an extension of JSON that fixes this:

    "NUL byte \y00"

(We use `\y00` rather than `\x00`, because Python and JavaScript both confuse
`\x00` with `U+0000`.  The zero code point may be encoded as 2 or 4 `NUL`
bytes.)

[J8 Strings]: j8-notation.html
[JSON]: $xref

### Escaping-Based Records

TSV files are based on delimiters, but they aren't very readable in a terminal.

TODO

So TSV8 offers and "aligned" format:

    #.ssv8 flag      desc                 type
    type   Str       Str                  Str
           --verbose "do it \t verbosely" bool
           --count   "count only"         int

So this format combines two strategies:

- Delimiter-based for the **rows** / lines
- Escaping-based for the **cells**

## Conclusion

Traditional shells mostly support newline-based records.  YSH supports:

1. Length-prefixed records
1. Delimiter-based records
  - fixed delimiter: newline or `NUL`
  - chosen delimiter: TODO?  with regex capture?
1. Escaping-based records with [JSON][] and the [J8 Notation][] extension.
  - But we avoid formats that are purely based on escaping.
