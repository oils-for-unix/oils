---
in_progress: yes
css_files: ../web/base.css ../web/help-index.css ../web/toc.css
---

Tea Help Topics
===============

<!--
IMPORTANT: This doc is processed in TWO WAYS.  Be careful when editing.

Special rules:
- [] at start of line is a section
- X for deprecated
- three spaces separating words to be highlighted

TODO: There should be a character for "no links past here?"
- or <span></span>
- this should be turned GREEN?
-->

This is a sketch for a hypothetical language, used to implement OSH and Oil.

It's a cleaned-up version of mycpp and ASDL.  It shares Oil's expression
language and eggex (for lexers).

<div id="toc">
</div>

<h2 id="func-data">
  Functions and Data (<a class="group-link" href="tea-help.html#func-data">func-data</a>)
</h2>

```oil-help-topics
                  func      func inc(p, p2=0; n=0, ...named) { echo 'hi' }
                  data      data Point(x Int, y Int)
                  enum      enum Tree { Leaf(x Int), Node(left Tree, right Tree) }
  [Assignment]    var   set   X const   
  [Errors]        try   catch   throw
                  with      deterministic destruction in the face of errors
  [Conditional]   switch   case   default   X match
                  if   elif   else
  [Loops]         for   while
                  break   continue   return
```

<h2 id="types">
  Builtin Data Types (<a class="group-link" href="tea-help.html#types">types</a>)
</h2>

```oil-help-topics
  [Literals]      Str           r'\'   c'\n'   "$var"   X multiline r""" c'''
                  X Symbol      %foo
                  Bool          True   False   None
                  Int           1_000_000  0b0100  0xFF  0o377  \n  \\  \u0100
                  Float         3.14   6.022e+23
                  List[]        :| ls -l |
                  Tuple[]       ()  tup(42)  (42, "foo")
                  Dict[]        {name: 'oil'}  {['name']: 'oil'}  {name}
                  Regex         / d+ /
                  X Func        fn(x) x+1   func(x) { return x+1 }
                  X Buf         file-like, mutable string
                  Type          Bool  Map[Str, Int]  Func[Int => Int]
  [Operators]     ternary       a if cond else b
                  subscript     a[b, c]   a[start:end]
                  X chain       _ a => f(y, z) => var new
                  getattr       d->key is like d['key'] or d.key
                  scope-attr    module::name
                  genexp   listcomp   X dictcomp
```

<h2 id="mod">
  Mods / Objects (<a class="group-link" href="tea-help.html#mod">mod</a>)
</h2>

```oil-help-topics
  [Objects]       class         bundle state and behavior (aka module)
                  extends       inheritance
                  self          pseudo-keyword
                  virtual   override   abstract
  [Names]         namespace
                  import        contrast with 'use' in Oil
                  export        for both files and classes
```

Not needed for minimal Oil port:

- const integers
- const methods (nice C++ feature)
- non-nullable types (that compile to C++ references)
- namespace or import (just use implicit naming)
