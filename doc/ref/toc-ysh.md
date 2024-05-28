---
in_progress: yes
css_files: ../../web/base.css ../../web/ref-index.css ../../web/toc.css
preserve_anchor_case: yes
---

YSH Table of Contents
=====================

[YSH]($xref) is shell with a familiar syntax, JSON-like data structures, good
error handling, and more.

This page is part of the [Oils Reference](index.html).  (Siblings: [OSH
contents](toc-osh.html), [Data contents](toc-data.html))

<div class="custom-toc">

[type-method](#type-method) &nbsp;
[builtin-func](#builtin-func) &nbsp;
[builtin-cmd](#builtin-cmd) &nbsp;
[front-end](#front-end) &nbsp;
[cmd-lang](#cmd-lang) &nbsp;
[ysh-cmd](#ysh-cmd) &nbsp;
[expr-lang](#expr-lang) &nbsp;
[word-lang](#word-lang) &nbsp;
[mini-lang](#mini-lang) &nbsp;
[option](#option) &nbsp;
[special-var](#special-var) &nbsp;
[plugin](#plugin)

</div>


<h2 id="type-method">
  Types and Methods (<a class="group-link" href="chap-type-method.html">type-method</a>)
</h2>

```chapter-links-type-method
  [Atom Types]     Null           Bool
  [Number Types]   Int            Float
  [Str]          X find()         replace()
                   trim()         trimStart()   trimEnd()
                   startsWith()   endsWith()
                   upper()        lower()
                   search()       leftMatch()
  [List]           append()       pop()         extend()    indexOf()
                 X insert()     X remove()      reverse()
  [Dict]           keys()         values()    X get()     X erase()
                 X inc()        X accum()
  [Range] 
  [Eggex] 
  [Match]          group()        start()       end()
                 X groups()     X groupDict()
  [Place]          setValue()
  [Code Types]     Expr           Command
                   BuiltinFunc    BoundFunc
X [Func]           name()         location()    toJson()
X [Proc]           name()         location()    toJson()
X [Module]         name()         filename()
  [IO]           X eval()       X captureStdout()
                   promptVal()
                 X time()       X strftime()
                 X glob()
X [Guts]           heapId()
```

<h2 id="builtin-func">
  Builtin Functions (<a class="group-link" href="chap-builtin-func.html">builtin-func</a>)
</h2>

```chapter-links-builtin-func
  [Values]        len()        type()   X repeat()
  [Conversions]   bool()       int()      float()   str()   list()   dict()
                X chr()      X ord()    X runes()
  [Str]         X strcmp()   X split()    shSplit()
  [List]          join()       any()      all()
  [Collections] X copy()     X deepCopy()
  [Word]          glob()       maybe()
  [Math]          abs()        max()      min()   X round()   sum()
  [Serialize]     toJson()     fromJson()
                  toJson8()    fromJson8()
X [J8 Decode]     J8.Bool()    J8.Int()   ...
  [Pattern]       _group()     _start()   _end()
  [Introspection] shvarGet()   getVar()   evalExpr()
  [Hay Config]    parseHay()   evalHay()
X [Hashing]       sha1dc()     sha256()
```

<!-- ideas
X [Codecs]        quoteUrl()   quoteHtml()   quoteSh()   quoteC()
                  quoteMake()   quoteNinja()
X [Wok]           _field()
-->

<h2 id="builtin-cmd">
  Builtin Commands (<a class="group-link" href="chap-builtin-cmd">builtin-cmd</a>)
</h2>

<!-- linkify_stop_col is 42 -->

```chapter-links-builtin-cmd_42
  [Memory]        append                 Add elements to end of array
                  pp                     asdl   cell   X gc-stats   line   proc
  [Handle Errors] try                    Run with errexit, set _status _error
                  boolstatus             Enforce 0 or 1 exit status
                  error                  error 'failed' (status=2)
  [Shell State]   ysh-cd       ysh-shopt compatible, and takes a block
                  shvar                  Temporary modify global settings
                  ctx                    Share and update a temporary "context"
                  push-registers         Save registers like $?, PIPESTATUS
  [Modules]       runproc                Run a proc; use as main entry point
                  module                 guard against duplicate 'source'
                  is-main                false when sourcing a file
                  use                    change first word lookup
  [I/O]           ysh-read               flags --all, -0
                  ysh-echo               no -e -n with simple_echo
                  write                  Like echo, with --, --sep, --end
                  fork         forkwait  Replace & and (), and takes a block
                  fopen                  Open multiple streams, takes a block
                X dbg                    Only thing that can be used in funcs
                X log        X die       Common functions (polyfill)
  [Hay Config]    hay          haynode   For DSLs and config files
  [Completion]    compadjust   compexport
  [Data Formats]  json                   read write
                  json8                  read write
                X packle                 read write, graph-shaped
X [TSV8]          rows                   pick rows; dplyr filter()
                  cols                   pick columns ('select' already taken)
                  group-by               add a column with a group ID [ext]
                  sort-by                sort by columns; dplyr arrange() [ext]
                  summary                count, sum, histogram, etc. [ext]
  [Args Parser]   parser                 Parse command line arguments
                  flag
                  arg
                  rest
                  parseArgs()
X [Testing]       describe               Test harness
                  assert                 takes an expression
```

<!--
Naming ideas:

X [External Lang] BEGIN   END   when (awk)
                  rule (make)   each (xargs)   fs (find)
-->

<h2 id="front-end">
  Front End (<a class="group-link" href="chap-front-end.html">front-end</a>)
</h2>

```chapter-links-front-end
  [Usage]         oils-usage                   ysh-usage
  [Lexing]        ascii-whitespace [ \t\r\n]
                  doc-comment ###              multiline-command ...
  [Tools]         cat-em
```

<h2 id="cmd-lang">
  Command Language (<a class="group-link" href="chap-cmd-lang.html">cmd-lang</a>)
</h2>

<!-- linkify_stop_col is 33 -->

```chapter-links-cmd-lang_33
  [YSH Simple]    typed-arg     json write (x)
                  lazy-expr-arg assert [42 === x]
                  block-arg     cd /tmp { echo $PWD }; cd /tmp (; ; blockexpr)
  [YSH Cond]      ysh-case      case (x) { *.py { echo 'python' } }
                  ysh-if        if (x > 0) { echo }
  [YSH Iter]      ysh-while     while (x > 0) { echo }
                  ysh-for       for i, item in (mylist) { echo }
```

<h2 id="ysh-cmd">
  YSH Command Language Keywords (<a class="group-link" href="chap-ysh-cmd.html">ysh-cmd</a>)
</h2>

```chapter-links-ysh-cmd_33
  [Assignment]    const   var   Declare variables
                  setvar        setvar a[i] = 42
                  setglobal     setglobal d.key = 'foo'
  [Expression]    equal =       = 1 + 2*3
                  call          call mylist->append(42)
  [Definitions]   proc          proc p (s, ...rest) {
                                typed proc p (; typed, ...rest; n=0; b) {
                  func          func f(x; opt1, opt2) { return (x + 1) }
                  ysh-return    return (myexpr)
```

<h2 id="expr-lang">
  Expression Language and Assignments (<a class="group-link" href="chap-expr-lang.html">expr-lang</a>)
</h2>

<!-- linkify_stop_col is 33 -->

```chapter-links-expr-lang_33
  [Assignment]    assign        =
                  aug-assign    +=   -=   *=   /=   **=   //=   %=
                                &=   |=   ^=   <<=   >>=
  [Literals]      atom-literal  true   false   null
                  int-literal   42  65_536  0xFF  0o755  0b10
                  float-lit     3.14  1.5e-10
                X num-suffix    42 K Ki M Mi G Gi T Ti / ms us
                  ysh-string    "x is $x"  $"x is $x"   r'[a-z]\n'
                                u'line\n'  b'byte \yff'
                  triple-quoted """  $"""  r'''  u'''  b'''
                  str-template  ^"$a and $b" for Str::replace()
                  list-literal  ['one', 'two', 3]  :| unquoted words |
                  dict-literal  {name: 'bob'}  {a, b}
                  range         1 .. n+1
                  block-literal ^(echo $PWD)
                  expr-lit      ^[1 + 2*3]
                X expr-sub      $[myobj]
                X expr-splice   @[myobj]
  [Operators]     op-precedence Like Python
                  concat        s1 ++ s2,  L1 ++ L2
                  ysh-equals    ===   !==   ~==   is, is not
                  ysh-in        in, not in
                  ysh-compare   <  <=  >  >=  (numbers only)
                  ysh-logical   not  and  or
                  ysh-arith     +  -  *  /  //  %   ** 
                  ysh-bitwise   ~  &  |  ^  <<  >>
                  ysh-ternary   '+' if x >= 0 else '-'
                  ysh-index     s[0]  mylist[3]  mydict['key']
                  ysh-attr      mydict.key
                  ysh-slice     a[1:-1]  s[1:-1]
                  func-call     f(x, y; ...named)
                  thin-arrow    mylist->pop()
                  fat-arrow     mystr => startsWith('prefix')
                  match-ops     ~   !~   ~~   !~~
  [Eggex]         re-literal    / d+ ; re-flags ; ERE /
                  re-primitive  %zero    'sq'
                  class-literal [c a-z 'abc' @str_var \\ \xFF \u0100]
                  named-class    dot   digit   space   word   d  s  w
                  re-repeat     d?   d*   d+   d{3}   d{2,4}
                  re-compound    seq1 seq2   alt1|alt2   (expr1 expr2)
                  re-capture    <capture d+ as name: int>
                  re-splice     Subpattern   @subpattern
                  re-flags      reg_icase   reg_newline
                X re-multiline  ///
```

<h2 id="word-lang">
  Word Language (<a class="group-link" href="chap-word-lang.html">word-lang</a>)
</h2>

<!-- linkify_stop_col is 33 -->

```chapter-links-word-lang_33
  [Quotes]        ysh-string    "x is $x"  $"x is $x"  r'[a-z]\n'
                                u'line\n'  b'byte \yff'
                  triple-quoted """  $"""  r'''  u'''  b'''
                X tagged-str    "<span id=$x>"html
  [Substitutions] expr-sub      echo $[42 + a[i]]
                  expr-splice   echo @[split(x)]
                  var-splice    @myarray @ARGV
                  command-sub   @(split command)
  [Formatting]  X ysh-printf    ${x %.3f}
                X ysh-format    ${x|html}
```

<h2 id="mini-lang">
  Other Mini Languages (<a class="group-link" href="chap-mini-lang.html">mini-lang</a>)
</h2>

<!-- linkify_stop_col is 33 -->

```chapter-links-mini-lang_33
  [Patterns]      glob-pat      *.py
  [Other Sublang] braces        {alice,bob}@example.com
```

<h2 id="option">
  Shell Options (<a class="group-link" href="chap-option.html">option</a>)
</h2>

```chapter-links-option
  [Groups]       strict:all      ysh:upgrade     ysh:all
  [YSH Details]  opts-redefine   opts-internal
```

<h2 id="special-var">
  Special Variables (<a class="group-link" href="chap-special-var.html">special-var</a>)
</h2>

```chapter-links-special-var
  [YSH Vars]      ARGV              X ENV                 X _ESCAPE
                  _this_dir
  [YSH Status]    _status             _error
                  _pipeline_status    _process_sub_status
  [YSH Tracing]   SHX_indent          SHX_punct             SHX_pid_str
  [YSH read]      _reply
  [History]       YSH_HISTFILE
  [Oils VM]       OILS_VERSION
                  OILS_GC_THRESHOLD   OILS_GC_ON_EXIT
                  OILS_GC_STATS       OILS_GC_STATS_FD
```

<!-- ideas 
X [Wok]           _filename           _line
X [Builtin Sub]   _buffer
-->

<h2 id="plugin">
  Plugins and Hooks (<a class="group-link" href="chap-plugin.html">plugin</a>)
</h2>

```chapter-links-plugin
  [YSH]   renderPrompt()
```
