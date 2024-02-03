Pretty Printing
===============

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


## TODO

- Fix ADSL cycle bug
  - Fix it in C++

- distinguish ... vs ---

- Somehow do ASDL ref counts, because the thing is long
  - to fix bin/osh -n


- Write separate parser for TYG8
  - no commas, no JSON8, just () and []
    - (unquotedyaks unquotedjs:value) and [value value]
    - unquotedyaks 
      - module.Type
      - `obj->method`
      - well to be honest this is probably SUGAR
      - so Yaks is different than ASDL
        - ASDL does have module.Type, but it doesn't need to be parsed
          differently
      - reader macro
        - (. module 'Type')
        - (-> obj 'method')

  - but is it for ASDL?  or is it for Yaks?
  - is it worth unifying these things?

- In both JSON8 and TYG8
  - allow comments
  - allow unquoted identifiers
    - lexer could be different here, not sure

- maybe change = operator and pp line (x) to use new pretty printer?

- come up with new hnode.asdl
  - with better line-wrapping algorithm?


