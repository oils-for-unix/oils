Up to 4 Pretty Printers?
========================

*(February 2024)*

Oils **parses** a lot of text, and it's becoming apparent than we need a
**print** a lot too!

A shell is a user interface, so the text should be nicely formatted.

This doc describes **four** possible pretty printers in Oils.  (Traditional
shells don't have appear to have any pretty printing.)


<div id="toc">
</div> 

## Intro

I'm writing this doc organize my thoughts, and to explain problem requirements
to contributors.  Note: sometimes I pile on too many requirements, which I
mentioned in the latest release announcement:

- [Oils 0.20.0 > Why I'm Working on JSON](https://www.oilshell.org/blog/2024/02/release-0.20.0.html#zulip-why-am-i-working-on-json)

## Background - `go fmt` style versus PPL style

There are at least two schools of thought on pretty printers, which 
this lobste.rs thread has a nice discussion of:

- <https://lobste.rs/s/aevptj/why_is_prettier_rock_solid>
- HN comments on same story: <https://news.ycombinator.com/item?id=39437424>
  - Top comment reveals why pretty-printing is hard - users are opinionated,
    and it can be **slow**.  This is why we don't want to take responsibility
    for all formatting decisions in our OSH-YSH printer.

More comments on a blog post by Justin Pombrio:

- <https://lobste.rs/s/1r0aak/twist_on_wadler_s_printer> (including `scalafmt`
  thesis)

Let's call the two styles the "`go fmt` style" and the "PPL style" (functional
pretty printing language).

I'm probably "biased" toward `go fmt`, because the two formatters we actually
**use** in Oils are influenced by it:

- `clang-format` for our C++ code.  This is the best formatter I've used.
- `yapf` for our Python code.  It's intentionally a "clone" for `clang-format`.

(They have line wrapping algorithms, while `go fmt` doesn't.  I'm not calling
them graph search" printers, because that describes what they do for **line
wrapping**, which I think of as a **subset** of pretty printing.)

<!--

Related: a bunch of Zulip threads where I was learning about pretty printing:

- TODO: Link to threads

(I've written many parsers before, but only one ad hoc pretty printer, which I
want to get rid of.  Discussed below.)

-->

---

However, Justin's post helped me understand Wadler's printer, which is a
popular example of the PPL style.  This style might have some advantages for
Oils:

- There's no "user layout" for data structures like JSON and Zephyr ASDL.  So
  we need to synthesize a layout from scratch.
- We have multiple languages to format, and the PPL style separates policy
  (language rules) and mechanism (line wrapping).  So we should try a more
  principled architecture, hopefully without sacrificing quality.
- The two styles may not be as distinct as they seem at first.  They may be
  complementary.
  - We can probably use a PPL for the **expression subproblem** of a shell
    formatter (OSH, YSH, or ideally both).  The rest of the formatter will have
    rules that don't have to do with line wrapping (aligning EOL comments like
    `go fmt` does, etc.)
  - I think a **non-wrapping** pretty printer can use something similar to the
    PPL IRs.  Notes below.
- I think PPLs *could be* slower (asymptotically and in practice) than the custom
  algorithms, but I think that can be solved with a simple rule in practice:
  - Compute the total size of the data structure/doc up front.
  - If it's small, spend extra time to make it look pretty, by using an
    expressive PPL.  We can be quadratic or worse, perhaps.  We might want
    `node.js`-like columnar layout.
  - If it's big, use a simple and fast PPL subset.

## Summary of Four Printers

TODO: add screenshots of

- node.js and jq
- current state of `=` operator
- current state of `osh -n`
  - link to screencast
  - timing of it -- I think this may take awhile.  It was never optimized.  It
    produces MANY allocations.
  - to be honest -- allocations and GC will probably **dominate** in Oils.

### Print YSH data types in a JSON-like format

We have the `=` operator, which is like Lua.

**Motivation**: We should look as good as `node.js` or `jq`.  TODO: add
screenshots.

### Replace our ad hoc Zephyr ASDL pretty printer

The algorithm is in `asdl/format.py`, and the code is in `asdl/hnode.asdl`.
This is an ad hoc line wrapper which I wrote several years ago.  TODO: I
believe it can be very slow, measure it.

The slowness didn't really matter because it's not user facing -- this format
is only debugging Oils itself.  But it's very useful, and we may want to expose
it to users.

**Motivation**: We already wrote an ad hoc pretty printer!  It seems like this
should "obviously" be unified

### Export the Oils Syntax Tree to Users with "NIL8"

Elaboration on the above.

**Motivations**:

- Expose a stable format for users.  They should be able to reuse all the hard
  work we did on parsing shell.
- Is NIL8 a good idea?
  - NIL8 Isn't Lisp
  - Narrow Intermediate Language
- We also plan to use NIL8 as a WebAssembly-text-format-like IR for

Note: the graph has layers like this:

1. `source_t` describes whether shell code comes from `foo.sh` or `ysh -c 'echo mycode'`
2. `SourceLine` represents physical lines
3. `Token` represents portions of lines
4. Then we have the Lossless Syntax Tree of `command_t word_t word_part_t
   expr_t`

### OSH-YSH Code Formatter

**Motivation** - Formatters are nice for users who don't know OSH/YSH well.  I
don't know TypeScript well, and I had a good experience with `deno fmt`.  It
reduces some mental load.

- Requirement: Don't take responsibility for every formatting decision!

### Order of implementation

It makes sense to do (1) and then (2).

(3) and (4) can be done in any order, or not at all.

Note: The first two printers are "engineering", but (3) and (4) are more
**experimental**.  Especially (3).

## Implementation Notes / Sketches

Notes on unifying pretty printing for 

- dynamically typed YSH values 
- statically typed ASDL values (mycpp, yaks)

## Dynamically Typed YSH Values

Similar to JSON / JSON8 printing, except we 

1. count references, and then print `...` instead of repeating
1. line wrap
1. assign colors
   - for atoms, and possibly for balanced parens, to make it more readable

### Step 1: Count References

This is a global pass that computes a Dict[int, int]

    object ID -> number of times referenced in the graph

The graph is specified by single root node, e.g. the argument to

    pp line (obj)

Pass this dict into the second step.

### Step 2: Convert To Homogeneous Representation

    value.List   -> hnode.Compound with []
    value.Dict   -> hnode.Compound with {}

    null, true, false -> Atom
    Cycle detected -> Atom, with { --- 4beef2 }
                                 [ --- 4beef2 ]

Repetition:

    { key: { ... 4beef2 }, key2: { ... 4beef2 }

Or maybe omit the type, since strings don't have that

    { key: ... 4beef2, key2: ... 4beef2 }

I guess you can do sharing

### hnode Schema

The schema looks like this now?

    hnode = 
      Atom(str s, color color) - # External objects can use this?
    | Compound(hnode* items)

The length of 'str s' is the input to line wrapping.

### Step 3: Figure out what's on each line

TODO: what's the heuristic here?  Is it global?

Dynamic programming?

do we insert hnode.Newline() or something?

## Statically Typed ASDL Data

Reduce it to the case above.

### Step 1 - Ref Counting / Cycle Detection?

We do this all at once?

Because to convert to value.Record, you have to do cycle detection anyway.

And that's similar to ref counting.

### Step 2 - ASDL records -> value.Record

    value = 
        ...
      | Record(str type_name, Dict[str, value_t] fields)

The special "-" key can be used for JSON:

    {"-": "command.Simple, "name": "hi"}

Though this loses some information, and it doesn't solve the problem with
shared references.  We would need Packle for that.

### Step 2a: Optional Abbreviation?

Is this separate?  Or part of step 2.

We need something between value.Record and hnode.Compound
to do ABBREVIATION:

- Abbreviate type name, or omit it
- Omit some field names (requires schema to record it)
- Change () to <>

Also need nodes for

- ... means already printed
- --- means CANNOT print, because it's a cycle
- @1f23 - ID if already printed, or in a cycle

### Step 3 and 4 - Homogeneous Representation, Line Wrapping

Identical to the dynamically typed case above.

## NIL8 - Two Use Cases - Code and Data

- NIL8 Isn't Lisp
- Narrow Intermediate Language

Use Cases:

- Exporitng the Oils lossless syntax tree
- Potential "Yaks" replacement for mycpp
  - Think: WebAssembly Text IR - it's a Lispy-format for an **imperative**
    language.
  - "an IR for garbage-collected C++"
  - "mycpp from the bottom up"
  - Reddit: Small statically typed language implemented in itself


Note: this is **experimental**.  Maybe these things **don't** belong together.

(We are trying to nudge users toward a **small** set of syntaxes for shell-like
programming, rather than inventing ad hoc syntax every time.  String literals
are a pain point: something people often implement badly, or don't implement at
all.)

## Non-Wrapping Printers - "Indenters"

### Can be trivial, but use similar PPL IR?

  Something like
  - First, do "Coarse Parsing" into `Comment | Code | StringLiteral` (this
    problem is related to syntax highlighting, which we also want  for YSH)
  - Lex code into `{} ()`,  and comments into `EolComment` | `Comment`
  - Do a trivial linear pass to fix up indnetation.  `{}` determines
    indentation.

## TODO

- Components
  - separate parser for NIL8
  - j8.PrettyPrinter -> new hnode representation
  - ASDL PrettyTree() -> new hnode representation
  - ASDL AbbreviatedTree() -> new hnode representation
    - need to figure out if we want abbreviations in C++
    - it's more readable

- Show NIL8 commit with "infix rule"

## Related Cool Stuff / Fun Computer Science Problems

Zulip: "Fun Computer Science Problems"

- Pretty printing is going to cause many allocations.
  - We want to move towards a "tagged pointer" runtime, which is an ambitiuos
    transformation of the entire interpreter.
  - But it can be done in steps
  - First step: Small string optimization
- GC rooting optimization
- NIL8 design might be interesting for someone who likes it
- Yaks might be interesting 
  - it's a little "meta", hence the name
  - But I believe it's **concrete** because we have **completed** the
    translation with mycpp, which is a crappy program
  - Yaks goes along with the tagged pointer runtime.  We want to make a
    principled IR rather than just printing text.
