---
default_highlighter: oils-sh
---

Up to 4 Pretty Printers?
========================

*(March 2024)*

Oils **parses** a lot of text, and it's becoming apparent than we need a
**print** a lot too!  The text should be nicely formatted because a shell is a
user interface.

This doc describes 4 possible pretty printers in Oils.  Traditional shells
don't have appear to have any pretty printing.

[OSH]: $xref
[YSH]: $xref

<div id="toc">
</div> 

## Screenshots

Let's be concrete first, because there's a lot of brainstorming below.

[YSH]($xref) prints its JSON-like data structures with the `=` keyword, which
takes a Python-like expression on the right:

![ysh issues.json](https://app.oilshell.org/picdir/resize?name=14qke97__ysh-issues.png&max-width=600)

Right now, it looks bad on big data structures.  It should look something like
`nodejs` or `jq`:

![node.js issues.json](https://app.oilshell.org/picdir/resize?name=13b35jj__nodejs-issues.png&max-width=600)

![jq issues.json](https://app.oilshell.org/picdir/resize?name=11wsgpm__jq-issues.png&max-width=600)

We may want to omit the quotes, like `nodejs`.  (This syntax isn't meant to be
parsed.  [JSON8]($xref) may have unquoted dict keys, although it's not
essential).

## Background - `go fmt` style versus PPL style

To back up a bit, I'm writing this doc organize my thoughts, and to explain
problems and requirements to contributors.

There are at least two schools of thought on pretty printers, which 
this lobste.rs thread has a good discussion of:

- *Why is Prettier Rock Solid?* <https://lobste.rs/s/aevptj/why_is_prettier_rock_solid>
  - HN comments: <https://news.ycombinator.com/item?id=39437424>.  Aside: a top
    comment shows why we don't want to take responsibility for *all* formatting
    decisions in our OSH-YSH printer!   Users are opinionated.  The JavaScript
    formatter Prettier is criticized for a bug, and for being **slow**.

More comments on a blog post by Justin Pombrio (which I circulated):

- *A Twist on Wadler's Printer*
  <https://lobste.rs/s/1r0aak/twist_on_wadler_s_printer>

Let's call the two styles the "`go fmt` style" and the "PPL style" (functional
pretty printing language).

I was probably "biased" toward `go fmt`, because the two formatters we actually
**use** in Oils are influenced by it:

1. `clang-format` for our C++ code.
   - This is the best formatter I've used.  It's fast, and e.g. does a good job
     on C macros.
1. `yapf` for our Python code.
   - It's intentionally a "clone" for `clang-format`.  (It's slow, mostly due
     to being written in Python, and creating lots of tiny objects!)

(Details: they have line wrapping algorithms, while `go fmt` doesn't.  I'm not
calling them "graph search" printers, because I think of line wrapping as a
**subproblem** of pretty printing.)

<!--

Related: a bunch of Zulip threads where I was learning about pretty printing:

- TODO: Link to threads

(I've written many parsers before, but only one ad hoc pretty printer, which I
want to get rid of.  Discussed below.)

-->

### Why PPL style?

However, Justin's post helped me understand Wadler's printer, a popular example
of the PPL style.  This style might have some advantages for Oils:

- There's no user-provided layout for data structures &mdash; either
  [YSH]($xref) data or [Zephyr ASDL][ASDL] data.  So we need to synthesize a
  layout from scratch.
- We have multiple languages to format, and the PPL style separates **policy**
  (language rules) and **mechanism** (line wrapping).  So we should try a more
  principled architecture, hopefully without sacrificing quality.
- The two styles may not be as distinct as they seem at first.  They may be
  complementary.
  - We can probably use a PPL for the **expression subproblem** of the OSH-YSH
    shell formatter.  The rest of the formatter will have rules that **don't**
    have to do with line wrapping (aligning EOL comments like `go fmt` does,
    etc.)
  - I think a **non-wrapping** pretty printer &mdash; an "indenter" &mdash; can
    use something similar to the PPL IRs.  Notes below.
- PPLs *could be* slower (asymptotically and in practice) than the custom
  algorithms, but I think that can be solved with a simple rule in practice:
  1. Compute the total size of the data structure/doc up front.
  1. If it's small, spend extra time to make it look pretty, by using an
     **expressive and slow** PPL.  We can be quadratic or worse, perhaps.  We
     might want `node.js`-like columnar layout.
  1. If it's big, use a **simple and fast** PPL subset.

(Does that last idea work?)

[ASDL]: $xref:zephyr-asdl


### Warning

Sometimes I pile on too many requirements, which I mentioned in the latest
release announcement:

- [Oils 0.20.0 > Why I'm Working on JSON](https://www.oilshell.org/blog/2024/02/release-0.20.0.html#zulip-why-am-i-working-on-json)

We should do the simplest things first, and I think the PPL approach will allow
that.

BTW there are many threads on `#data-languages` on [Zulip]($xref) where I'm
brainstorming and learning about pretty printing.

## Four Printers - What and Why?

Here's a sketch of what I think we need.  It goes from **concrete** &rarr;
**experimental** and research-y.

### Print YSH data types in a JSON-like format

**What is it?**  This is the `=` keyword shown in the screenshots above.  (BTW,
Lua uses the same syntax `=` to evaluate expressions.)

**Motivation**: We should look as good as `node.js` or `jq`.

---

Currently we use our JSON printer with the options `SHOW_NON_DATA |
SHOW_CYCLES`.

- `SHOW_NOW_DATA` prints non-data objects, like `<Func 0x123>`.  This syntax
  can't be parsed.
- `SHOW_CYCLES` prints cycles with `-->`, instead of raising an error, like
  JSON does.

Example:

    ysh$ var d = {}
    ysh$ setvar d.eggex = /dot+/  # Eggex object

    ysh$ = d
    (Dict 0x7feb87cb4050)   {"eggex":<Eggex 0x7feb87dbfd00>}

    ysh$ setvar d.cycle = d

    ysh$ = d
    (Dict 0x7feb87cb4050)   {"eggex":<Eggex 0x7feb87dbfd00>,"cycle":{ --> 0x7feb87cb4050 }}

We should **replace** this with a new pretty printer that wraps lines, and has
<span style="color: darkcyan; font-weight: bold">COLOR</span>.

### Replace our ad hoc Zephyr ASDL pretty printer

**What is it?**  [Zephyr ASDL][ASDL] is the statically typed schema language we
use to implement Oils.  It's "one level down" from the shell.

We used it to define the syntax of shell with **algebraic data types**.  We
create a [lossless syntax tree]($xref:LST), which is also an **IR** for shell.

**Motivation**: We already wrote an ad hoc pretty printer, and it should be
replaced!  It tries to fit records on a single line, and if that fails, it uses
multiple lines.  I think it's slow.

If we already have a YSH data printer, this printer should "obviously" be
unified with it.  We should have a nice separation of policy and mechanism.

---

Use `osh -n myscript.sh` to see what it does:

![osh -n](https://app.oilshell.org/picdir/resize?name=1lwb0bf__osh-n.png&max-width=600)

Notes:

- The algorithm is in [asdl/format.py]($oils-src), and the "homogeneous IR" is
  in [asdl/hnode.asdl]($oils-src).
  - Each generated class definition has a `PrettyTree()` method, which converts
    the **typed** `self` or `this` to the homogeneous `hnode` tree.
  - `AbbreviatedTree()` is a bit like the **modular** printers discussed in the
    `lobste.rs` thread.  It makes certain common data structures more
    readable, with type-specific logic.  It's in Python only &mdash; can that
    logic also be in C++?
  - The syntax tree is actually a **graph**, and I recently added logic to
    **omit duplicate** nodes.  This is unlike the JSON printer, which prints
    duplicate nodes, as Python and node.js do.
- The slowness hasn't really mattered, because this format isn't exposed to
  users.  It's only for **debugging** Oils itself.  But it's useful, and we may
  want to expose it.
- Also used in `pp asdl (obj)`, another debugging feature.
- TODO: Add a simple benchmark?  The new printer will probably be faster than
  the old one.
  - `osh -n benchmarks/testdata/configure-coreutils` tests a huge shell file

<!--
- current state of `osh -n`
  - timing of it -- I think this may take awhile.  It was never optimized.  It
    produces MANY allocations.
  - to be honest -- allocations and GC will probably **dominate** in Oils.
-->

### OSH-YSH Code Formatter

**What is it?** A formatter for shell code.  I think it's more essential to
have a [YSH]($xref) formatter, but an [OSH]($xref) formatter is also possible.
They both use the same [lossless syntax tree]($xref:LST).

**Motivation** - Formatters make a new language easier to use, and there are
many users who don't know shell well. 

For example, I don't know TypeScript well, and I had a good experience with
`deno fmt`.  It reduced the **mental load** of adopting a new tool.

---

Justin had a nice idea on on `lobste.rs` - we should create **coarse tree**
with these elements:

- `{ }` affect indentation in [YSH]($xref)
  - In [OSH]($xref), we should also understand `then elif else fi`, `do done`,
    etc.
- `( )` in [YSH]($xref) changes the lexer from [command mode to expression
  mode](command-vs-expression-mode.html)
- **Newlines** can't appear in atomic `text()` / chunks
- Comments need to be preserved at the end of lines
  - They may also be aligned on consecutive lines (with heuristics)
- Keywords like `while for if` begin blocks of code

Why?  We don't don't want to take responsibility for every formatting decision!

I actually think the command mode / statement formatter should be
**non-wrapping**, while expressions can wrap.  Commands will likely be more
common than expressions in most YSH code.

---

The formatter will be invoked with `ysh --tool format myfile.ysh`.

It can also be used with the output of `osh --tool ysh-ify`, which roughly
translates [OSH]($xref) to [YSH]($xref) (doesn't preserve semantics).  This may
help generate **test data**, since there's plenty of shell code in the wild,
but not much [YSH][] code.

### Experimental: Export the Oils "Syntax Graph" to Users with "NIL8"

**What is it?** A more human AND machine-readable format for the syntax tree,
which is actually a **graph**.

**Motivation**: The pretty-printed AST could be a **parseable** format.  Allow
users to reuse all the hard work we did [parsing
shell]($blog-tag:parsing-shell)!

---

Printing raw [ASDL][] data is useful, but it could be more readable with custom
logic to print the natural **layers** of the graph.  There are 4 logical layers
in [frontend/syntax.asdl]($oils-src):

1. `source_t` describes whether shell code comes from `foo.sh` or `ysh -c 'echo
   mycode'`
2. `SourceLine` represents physical lines of code
3. `Token` refers to portions of lines
4. The syntax tree of `command_t word_t word_part_t expr_t`.  The leaves are
   tokens.

And instead of a pretty format meant for humans, we may want to print an
s-expression-like format I'm calling **"NIL8"**.

NIL8 can be parsed.  You may want to write tree-shaking code to deploy
[YSH][] into containers.

More on NIL8 below.  Again, it's experimental.

## Implementation Notes

### Do the printers depend on each other?

- The [YSH][] printer (1) naturally comes before the [ASDL][] printer (2).
- The code formatter (3) is concrete and useful to end users.
- The NIL8 printer (4) comes after the [ASDL][] printer (2), but it's experimental.
  - It depends on a bunch of other work in Oils/YSH.

Risks:

- No real risks for (1) and (2)
  - They're "engineering" &mdash; Justin's blog post is very close!  It could
    be ported almost literally to typed Python.  It will translate
    automatically to C++.  (And it would be interesting to compare our
    garbage-collected C++ with Rust's `Rc<T>`)
  - [ASDL][] involves code generation in both Python and C++.  We have a custom
    build system for this (using Ninja for C++).
- The OSH/YSH formatter has non-trivial decisions
  - End-of-line comments.  (Shell doesn't have block comments, which simplifies
    things.)
  - Multi-line strings in YSH have a special rule -- the indentation of the
    closing `'''` is significant
  - Shell here docs may be tricky
  - This formatter probably requires the most "elbow grease".  This is why I
    said that the statement formatter should initially be **non-wrapping** &mdash;
    it reduces the scope of the problem.

### Code Skeleton

I added some stubs in the code:

- [data_lang/pretty.asdl]($oils-src) - How we would express the IR
- [data_lang/pretty.py]($oils-src) - YSH conversion.
- [data_lang/pretty-benchmark.sh]($oils-src) - Our naive ASDL pretty printer is
  slow.  It can take more than 3 seconds on a big file, vs. ~100ms to parse it.
  (It does print over 100 MB of text though.)

To generate Python code from the ASDL schema, run `build/py.sh all`.
Otherwise, Oils is a plain Python 2 program, with a few C extensions.

C++ translation is a separate step, and it's now pretty polished.

For new contributors:

- [Contributing]($wiki) on the wiki
- [Where Contributors Have Problems]($wiki)

There is also a stub for the formatter:

- [tools/fmt.py]($oils-src) - Stub file for the formatter.
  - Code copied from [tools/ysh_ify.py]($oils-src).

## Design Questions

This section has some less concrete thoughts.

### Non-Wrapping Printers aka "Indenters" - same PPL IR?

I think the PPL IRs are also useful if you're not line wrapping?  You can just
fix indentation.

### Columnar Layouts (spending more time)

`nodejs` does this in its `console.log()`.

![python node.js](https://app.oilshell.org/picdir/resize?name=uscdu6__python-nodejs.png&max-width=600)

Future work?  We should get the basic pretty printer working first.

### Two Levels of Coarse Parsing for YSH?  (not at first)

Making the coarse tree has some similarity to syntax highlighting.  I wrote a 
simple syntax highlighter for 5+ languages called `micro-syntax`, and it should
support [YSH]($xref) too.

Sketch:

1. First make the **really coarse tree**, something like: `Comment | Code |
   StringLiteral`
2. Then make a **less coarse** tree for pretty printing:
   - Lex code into `{} ()`
   - Categorize comments into `EndLineComment` | `BeginLineComment`

Then do a trivial linear pass to fix up indentation.  The `{ }` or `do done`
tokens determine indentation.

---

Though honestly it's probably better to just **reuse** our elaborate parser at
first.  I like to "compress" different algorithms together, but it may not be
worth it here.

### NIL8 - Uses cases for both Code and Data

What is "NIL8"?  We don't know if it's a good idea yet, but it may be part of
[J8 Notation](j8-notation.html).

Think:

- A mash-up of [JSON][] and S-expressions
  - *NIL8 Isn't Lisp*
  - *Narrow Intermediate Language*
- WebAssembly text format
  - An IR for an **imperative** language, with a Lisp-y syntax.
- An **exterior** S-expression format
  - Blog: [Oils is Exterior-First](https://www.oilshell.org/blog/2023/06/ysh-design.html)
  - I posted POSE (portable s-expressions) on lobste.rs for this reason:
    <https://lobste.rs/s/lwf4jv/pose_portable_s_expressions_pose_spec> (no
    comments)

[JSON]: $xref

If NIL8 can represent both the [lossless syntax tree]($xref:LST) and a new IR
for a [mycpp]($xref) rewrite ("yaks"), that's a good test of the design.

Note that the AST is a **statically typed** data structure, which means we may
also want to export the [ASDL][] **schema** as NIL8!

Links:

- [#data-languages > NIL8 Infix Rule](https://oilshell.zulipchat.com/#narrow/stream/403584-data-languages/topic/NIL8.20Infix.20Rule)
- [Commit describing infix rule](https://github.com/oilshell/oil/commit/b9cecf88838d4c89ce1dbd8f4bcdd8e92e10d442)

At a high level, we're trying to nudge users toward a **small** set of syntaxes
for shell-like programming, rather than inventing ad hoc syntax every time.
String literals are a pain point: people often implement them badly, or not at
all.

## Conclusion 

I think we should have shared infrastructure for 3 printers:

1. [YSH]($xref) data structures
1. [ASDL][] data structures
1. [OSH]($xref) and [YSH]($xref) code

And then there's this idea of "replacing" or rationalizing the [ASDL][] syntax
tree with "NIL8":

- It can be parsed, not just printed.
  - To parse, you can reuse an existing [JSON]($xref) string lexer.  IMO, this
    is the fiddliest part of parsing.
- It can export a graph shape, in natural "layers".

## Related 

### Docs

- [Parser Architecture](parser-architecture.html) - describes issues like the
  **"lossless invariant"**, which is affected by *re-parsing*.
  - I recently updated it, and tested the invariant with
    [test/lossless.sh]($oils-src).
- The repo [README]($oils-doc:README.html) has an overview of the code.

### Fun Computer Science Problems in Oils

Pretty printing is adjacent to other fun problems in Oils, like GC performance,
"boxless" optimization, etc.

- [#help-wanted > Fun Computer Science Problems](https://oilshell.zulipchat.com/#narrow/stream/417617-help-wanted/topic/Fun.20Computer.20Science.20Problems)

Things to think about:

(1) Unified Code Representation for Oils

We want to pack all these tools into Oils:

- The interpreter, for **execution**
  - prints precise errors, ignores comment tokens
- `ysh-ify` - a VERY rough **translation** of [OSH]($xref) to [YSH]($xref)
  - doesn't respect semantics, because you really need static types for that
  - uses "span ID"
- **Pretty Printing** (this doc)
  - will also use "span ID" to detect comment positions, I think
- Syntax **highlighting**
  - Interactive highlighting will help users learn the language
  - It's **recursive**, because sublanguages are mutually recursive: string
    literals, commands, expressions

Related: Retrospective on the Go `ast` package.

(2) Yaks - *mycpp from the bottom up*

NIL8 leads into **"Yaks"**, which is an IR for garbage collected C++.  

- Yaks is of course a big yak shave, but it's **concrete** because we recently
  **completed** the translation with [mycpp]($xref).  (mycpp is a crappy
  program which produces good results!)

(3) Pretty printing will cause many small **allocations**.

I think that naive implementations should be fast enough.  If not, any slowness
may be due to allocation, not necessarily the pretty printing algorithm itself.

Some solutions:

- We want to move towards a **tagged pointer** runtime, an ambitious
  transformation of the entire interpreter.
  - But we'll do it in steps.  First step: Small String Optimization.
  - Yaks goes along with a tagged pointer runtime.  Yaks also has a principled
    IR, which may be represented with many small objects.
- GC rooting optimization should give a speed boost

## Appendix: Older Notes

This is about ref counting for printing **graph-shaped** data.

I no longer think this is as important.  I think we should **manually**
construct 4 layers of the graph, as described in the section on formatter (4).

### Dynamically Typed YSH Data (`value_t`)

Similar to JSON / JSON8 printing, except we 

1. count references, and then print `...` instead of repeating
1. line wrap
1. assign colors
   - for atoms, and possibly for balanced parens, to make it more readable

#### Step 1: Count References

This is a global pass that computes a Dict[int, int]

    object ID -> number of times referenced in the graph

The graph is specified by single root node, e.g. the argument to

    pp line (obj)

Pass this dict into the second step.

#### Step 2: Convert To Homogeneous Representation

    value.List   -> hnode.Compound with []
    value.Dict   -> hnode.Compound with {}

    null, true, false -> Atom
    Cycle detected -> Atom, with { --> 4beef2 }
                                 [ --> 4beef2 ]

Repetition:

    { key: { ... 4beef2 }, key2: { ... 4beef2 }

Or maybe omit the type, since strings don't have that:

    { key: ... 4beef2, key2: ... 4beef2 }

#### hnode Schema

The schema looks like this now?

    hnode = 
      Atom(str s, color color) - # External objects can use this?
    | Compound(hnode* items)

The length of 'str s' is the input to line wrapping.

#### Step 3: Figure out what's on each line

TODO: what's the heuristic here?  Is it global?

Dynamic programming?

do we insert hnode.Newline() or something?

### Statically Typed ASDL Data

Reduce it to the case above.

#### Step 1 - Ref Counting / Cycle Detection?

We do this all at once?

Because to convert to value.Record, you have to do cycle detection anyway.

And that's similar to ref counting.

#### Step 2 - ASDL records -> value.Record

    value = 
        ...
      | Record(str type_name, Dict[str, value_t] fields)

The special "-" key can be used for JSON:

    {"-": "command.Simple, "name": "hi"}

Though this loses some information, and it doesn't solve the problem with
shared references.  We would need Packle for that.

#### Step 2a: Optional Abbreviation?

Is this separate?  Or part of step 2.

We need something between value.Record and hnode.Compound
to do ABBREVIATION:

- Abbreviate type name, or omit it
- Omit some field names (requires schema to record it)
- Change () to <>

Also need nodes for

- `...` means already printed
- `---` means CANNOT print, because it's a cycle
- `@1f23` - ID if already printed, or in a cycle

#### Steps 3 and 4 - Homogeneous Representation, Line Wrapping

Identical to the dynamically typed case above.

