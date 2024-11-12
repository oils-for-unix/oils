---
in_progress: yes
default_highlighter: oils-sh
---

Streams, Tables and Processes - awk, R, xargs
=============================================

*(July 2024)*

This is a long, "unified/orthogonal" design  for:

- Streams: [awk]($xref) delimited lines, regexes
- Tables: like data frames with R's dplyr or Pandas, but with the "exterior"
  TSV8 format
- Processes: xargs -P in parallel

There's also a relation to:

- Trees: `jq`, which will be covered elsewhere.

It's a layered design.  That means we need some underlying mechanisms:

- `eval` and positional args `$1 $2 $3`
- `ctx` builtin
- Data langauges: TSV8
- Process pool / event loop primitive

It will link to:

- Oils blog posts (old)
- Zulip threads (recent)
- Other related projects (many of them)

<div id="toc">
</div> 

## Intro With Code Snippets

Let's introduce this with a text file

    $ seq 4 | xargs -n 2 | tee test.txt
    1 2
    3 4 

xargs does splitting:

    $ echo 'alice bob' | xargs -n 1 -- echo hi | tee test2.txt
    hi alice
    hi bob

Oils:

    # should we use $_ for _word _line _row?  $[_.age] instead of $[_row.age]
    $ echo 'alice bob' | each-word { echo "hi $_" } | tee test2.txt
    hi alice
    hi bob

Normally this should be balanced

### Streams - awk

Now let's use awk:

    $ cat test.txt | awk '{ print $2 " " $1 }'
    2 1
    4 3

In YSH:

    $ cat test.txt | chop '$2 $1'
    2 1
    4 3

It's shorter!  `chop` is an alias for `split-by (space=true, template='$2 $1')`

With a template, for static parsing:

    $ cat test.txt | chop (^"$2 $1")
    2 1
    4 3

It's shorter!  With a block:

    $ cat test.txt | chop { mkdir -v -p $2/$1 }
    mkdir: created directory '2/1'
    mkdir: created directory '4/3'

With no argument, it prints a table:

    $ cat test.txt | chop
    #.tsv8 $1 $2
           2  1
           4  3

    $ cat test.txt | chop (names = :|a b|)
    #.tsv8 a  b
           2  1
           4  3

Longer examples with split-by:

    $ cat test.txt | split-by (space=true, template='$2 $1')
    $ cat test.txt | split-by (space=true, template=^"$2 $1")
    $ cat test.txt | split-by (space=true) { mkdir -v -p $2/$1 }
    $ cat test.txt | split-by (space=true)
    $ cat test.txt | split-by (space=true, names= :|a b|)
    $ cat test.txt | split-by (space=true, names= :|a b|) {
        mkdir -v -p $a/$b
      }

With must-match:

    $ var p = /<capture d+> s+ </capture d+>/
    $ cat test.txt | must-match (p, template='$2 $1')
    $ cat test.txt | must-match (p, template=^"$2 $1")
    $ cat test.txt | must-match (p) { mkdir -v -p $2/$1 }
    $ cat test.txt | must-match (p)

With names:

    $ var p = /<capture d+ as a> s+ </capture d+ as b>/
    $ cat test.txt | must-match (p, template='$b $a')
    $ cat test.txt | must-match (p)
    #.tsv8 a b
           2 1
           4 3

    $ cat test.txt | must-match (p) {
        mkdir -v -p $a/$b
      }

Doing it in parallel:

    $ cat test.txt | must-match --max-jobs 4 (p) {
        mkdir -v -p $a/$b
      }

### Tables - Data frames with dplyr (R)

   $ cat table.txt
   size path
   3    foo.txt
   20   bar.jpg

   $ R
   > t=read.table('table.txt', header=T)
   > t
     size    path
   1    3 foo.txt
   2   20 bar.jpg

### Processes - xargs

We already saw this!  Because we "compressed" awk and xargs together

What's not in the streams / awk example above:

- `BEGIN END` - that can be separate
- `when [$1 ~ /d+/] { }`

## Background / References

- Shell, Awk, and Make Should be Combined (2016)
  - this is the Awk part!

- What is a Data Frame?  (2018)

- Sketches of YSH Features (June 2023) - can we express things in YSH?
  - Zulip: Oils Layering / Self-hosting

- Language Compositionality Test: J8 Lines
  - This whole thing is a compositionality test

- read --split
  - more feedback from Aidan and Samuel

- What is a Data Frame?

- jq in jq thread

Old wiki pages:

- <https://github.com/oilshell/oil/wiki/Structured-Data-in-Oil>
  - uxy - closest I think - <https://github.com/sustrik/uxy>
    - relies on to-json and jq for querying
  - miller - I don't like their language - https://github.com/johnkerl/miller -
  - jc - <https://github.com/kellyjonbrazil/jc>
- nushell
- extremely old thing -

We're doing **all of these**.

## Concrete Use Cases

- benchmarks/* with dplyr
- wedge report
- oilshell.org analytics job uses dplyr and ggplot2

## Intro

### How much code is it?

- I think this is ~1000 lines of Python and ~1000 lines of YSH (not including tests)
  - It should be small

### Thanks

- Samuel - two big hints 
  - do it in YSH
  - `table` with the `ctx` builtin
- Aidan
  - `read --split` feedback


## Tools

- awk 
  - streams of records - row-wise
- R
  - column-wise operations on tables
- `find . -printf '%s %P\n'`  - size and path
  - generate text that looks like a table
- xargs
  - operate on tabular text -- it has a bespoke splitting algorithm
  - Opinionated guide to xargs
  - table in, table out
- jq - "awk for JSON"


## Concepts

- TSV8
  - aligned format SSV8
  - columns have types, and attributes
- Lines 
  - raw lines like shell
  - J8 lines (which can represent any filename, any unicode or byte string)
- Tables - can be thought of as:
  - Streams of Rows - shape `[{bytes: 123, path: "foo"}, {}, ...]`
    - this is actually <https://jsonlines.org> , and it fits well with `jq` 
  - Columns - shape `{bytes: [], path: []}

## Underlying Mechanisms in Oils / Primitives

- blocks `value.Block` - `^()` and `{ }` 
- expressions `value.Expr` - `^[]` and 'compute [] where []'

- eval (b, vars={}, positional=[])

- Buffered for loop
  - YSH is now roughly as fast as Awk!
  - `for x in (io.stdin)`

- "magic awk loop"

    with chop {
      for <README.md *.py> {
        echo _line_num _line _filename $1 $2
      }
    }

- positional args $1 $2 $3
  - currently mean "argv stack"
  - or "the captures"
  - this can probably be generalized

- `ctx` builtin
- `value.Place`

TODO:

- split() like Python, not like shell IFS algorithm

- string formatting ${bytes %.2f}
  - ${bytes %.2f M} Megabytes
  - ${bytes %.2f Mi} Mebibytes

  - ${timestamp +'%Y-m-%d'}  and strfitime

  - this is for

  - floating point %e %f %g and printf and strftime

### Process Pool or Event Loop Primitive?

- if you want to display progress, then you might need an event loop
- test framework might display progress

## Matrices - Orthogonal design in these dimensions

- input: lines vs. rows
- output: string (Str, Template) vs. row vs. block execution (also a row)
- execution: serial vs. parallel
- representation: interior vs. exterior !!!
  - Dicts and Lists are interior, but TSV8 is exterior
  - and we have row-wise format, and column-wise format -- this always bugged me
- exterior: human vs. machine readable
  - TSV8 is both human and machine-readable
  - "aligned" #.ssv8 format is also
  - they are one format named TSV8, with different file extensions.  This is
    because it doesn't make too much sense to implement SSV8 without TSV8.  The
    latter becomes trivial.  So we call the whole thing TSV8.

This means we consider all these conversions

- Line -> Line
- Line -> Row
- Row -> Line
- Row -> Row

## Concrete Decisions - Matrix cut off

Design might seem very general, but we did make some hard choices.

- push vs. pull
  - everything is "push" style I think
- buffered vs. unbuffered, everything

- List vs iterators
  - everything is either iterable pipelines, or a List


[OSH]: $xref
[YSH]: $xref


## String World

**THESE ARE ALL THE SAME ALGORITHM**.  They just have different names.

- each-line
- each-row
- split-by (/d+/, cols=:|a b c|)
  - chop
- if-match
- must-match
  - todo

should we also have: if-split-by ?  In case there aren't enough  columns?

They all take:

- string arg ' '
- template arg (^"") - `value.Expr`
- block arg

for the block arg, this applies:

    -j 4
    --max-jobs 4

    --max-jobs $(cached-nproc)
    --max-jobs $[_nproc - 1]

### Awk Issues

So we have this

    echo begin
    var d = {}
    cat -- @files | split-by (ifs=IFS) {
      echo $2 $1
      call d->accum($1, $2)
    }
    echo end

But then how do we have conditionals:

    Filter foo {  # does this define a proc?  Or a data structure

      split-by (ifs=IFS)  # is this possible?  We register the proc itself?

      config split-by (ifs=IFS)  # register it

      BEGIN {
        var d = {}
      }
      END {
        echo d.sum
      }

      when [$1 ~ /d+/] {
        setvar d.sum += $1
      }

    }

## Table World

### `table` to construct

Actions:

    table cat
    table align / table tabify
    table header (cols)
    table slice (1, -1)   or (-1, -2) etc.

Subcommands

    cols
    types
    attr units

Partial Parsing  / Lazy Parsing - TSV8 is designed for this

    # we only decode the columns that are necessary
    cat myfile.tsv8 | table --by-col (&out, cols = :|bytes path|)

## Will writing it in YSH be slow?

- We concentrate on semantics first
- We can rewrite in Python
- Better: users can use **exterior** tools with the same interface
  - in some cases
  - they can write an efficient `sort-tsv8` or `join-tsv8` with novel algorithms
- Most data will be small at first


## Applications

- Shell is shared nothing
- Scaling to infinity on the biggest clouds


## Extra: Tree World?

This is sort of "expanding the scope" of the project, when we want to reduce scope.

But YSH has both tree-shaped JSON, and table-shaped TSV8, and jq is a nice **bridge** between them.

Streams of Trees (jq)

    empty
    this
    this[]
    =>
    select()
    a & b  # more than one


## Pie in the Sky

Four types of Data Languages:

- flat strings
- JSON8 - tree
- TSV8 - table
- NIL8 - Lisp Tree
- HTML/XML - doc tree -- attributed text (similar to Emacs data model)
  - 8ml

Four types of query languaegs:

- regex
- jq / jshape
- tsv8


## Appendix

### Notes on Naming

Considering columns and then rows:

- SQL is "select ... where"
- dplyr is "select ... filter"
- YSH is "pick ... where"
  - select is a legacy shell keyword, and pick is shorter
  - or it could be elect in OSH, elect/select in YSH
    - OSH wouldn't support mutate [average = bytes/total] anyway

dplyr:

- summarise vs. summarize vs. summary





