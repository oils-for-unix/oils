---
in_progress: yes
css_files: ../../web/base.css ../../web/ref-index.css ../../web/toc.css
preserve_anchor_case: yes
---

OSH Table of Contents
===

These are links to topics in the [Oils Reference](index.html).

Siblings: [OSH Topics](toc-osh.html), [Data Topics](toc-data.html)

<div id="toc">
</div>


<h2 id="front-end">
  Front End (<a class="group-link" href="chap-front-end.html">front-end</a>)
</h2>

```chapter-links-front-end
  [Usage]         bundle-usage   ysh-usage
  [YSH Lexing]    doc-comment ###   multiline-command ...
  [Tools]         cat-em
```

<h2 id="cmd-lang">
  Command Language (<a class="group-link" href="chap-cmd-lang.html">cmd-lang</a>)
</h2>

```chapter-links-cmd-lang
  [YSH Simple]    typed-arg     json write (x)
                  lazy-expr-arg assert [42 === x]
                  block-arg     cd /tmp { echo $PWD }
  [YSH Assign]    const   var   setvar   setglobal
  [YSH Expr]      equal =       = 1 + 2*3
                  call          call mylist->append(42)
  [YSH Code]      proc-def      proc p (out Ref; pos, ...rest; n=0; b Block) {
                  func-def      func f(x; opt1, opt2) { return (x + 1) }
                  ysh-return    return (myexpr)
  [YSH Cond]      ysh-case      case (x) { *.py { echo 'python' } }
                  ysh-if        if (x > 0) { echo }
  [YSH Iter]      ysh-while     while (x > 0) { echo }
                  ysh-for       for i, item in (mylist) { echo }
```

<h2 id="expr-lang">
  Expression Language and Assignments (<a class="group-link" href="chap-expr-lang.html">expr-lang</a>)
</h2>

```chapter-links-expr-lang
  [Assign Ops]    =   +=   -=   *=   /=   **=   //=   %=
                  &=   |=   ^=   <<=   >>=
  [Literals]      bool-literal  true   false   null
                  int-literal   42  65_536  0xFF  0o755  0b10
                  float-lit     3.14  1.5e-10
                  X num-suffix  42 K Ki M Mi G Gi T Ti / ms us
                  rune-literal  #'a'   #'_'   \n   \\   \u{3bc}
                  ysh-string    "$x"  r'[a-z]\n'  u'line\n'  b'byte \yff'
                  triple-quoted """  r'''  u'''  b'''
                  list-literal  ['one', 'two', 3]  :| unquoted words |
                  dict-literal  {name: 'bob'}
                  range         1 .. n+1
                  block-literal ^(echo $PWD)
                  expr-lit      ^[1 + 2*3]
                  X template    ^"$a and $b" for Str::replace()
                  X to-string   $[myobj]
                  X to-array    @[myobj]
  [Operators]     concat        s1 ++ s2,  L1 ++ L2
                  ysh-equals    ===   !==   ~==   is, is not, in, not in
                  ysh-compare   <  <=  >  >=  (numbers only)
                  ysh-logical    not  and  or
                  ysh-arith     +  -  *  /  //  %   ** 
                  ysh-bitwise   ~  &  |  ^  <<  >>
                  ysh-ternary   '+' if x >= 0 else '-'
                  ysh-index     a[3]  s[3]
                  ysh-attr      mydict.key
                  ysh-slice     a[1:-1]  s[1:-1]
                  func-call     f(x, y)
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

```chapter-links-word-lang
  [Quotes]        ysh-string    "$x"  r'[a-z]\n'  u'line\n'  b'byte \yff'
                  triple-quoted """  r'''  u'''  b'''
                  X tagged-str  "<span id=$x>"html
  [Expression]    expr-sub      echo $[42 + a[i]]
                  expr-splice   echo @[split(x)]
                  var-splice    @myarray @ARGV
  [Formatting]    X ysh-printf  ${x %.3f}
                  X ysh-format  ${x|html}
```

<h2 id="builtin-cmd">
  Builtin Commands (<a class="group-link" href="chap-builtin-cmd">builtin-cmd</a>)
</h2>

```chapter-links-builtin-cmd
  [Memory]        append                 Add elements to end of array
                  pp                     asdl   cell   X gc-stats   line   proc
  [Handle Errors] try                    Run with errexit, set _status _error
                  boolstatus             Enforce 0 or 1 exit status
                  error                  error 'failed' (status=2)
  [Shell State]   ysh-cd   ysh-shopt     compatible, and takes a block
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
                  fork   forkwait        Replace & and (), and takes a block
                  fopen                  Open multiple streams, takes a block
                  X dbg                  Only thing that can be used in funcs
                  X log   X die          common functions (polyfill)
  [Hay Config]    hay   haynode          For DSLs and config files
  [Completion]    compadjust   compexport
  [Data Formats]  json                   read write
                  json8                  read write
                  X packle               read write, Graph-shaped
X [TSV8]          rows                   pick rows; dplyr filter()
                  cols                   pick columns ('select' already taken)
                  group-by               add a column with a group ID [ext]
                  sort-by                sort by columns; dplyr arrange() [ext]
                  summary                count, sum, histogram, etc. [ext]
  [Args]          X parser               argument parsing
                  X flag
                  X arg
                  X rest
                  X parseArgs()
X [Testing]       describe               Test harness
                  assert                 takes an expression
X [External Lang] BEGIN   END   when (awk)
                  rule (make)   each (xargs)   fs (find)
```

<h2 id="option">
  Shell Options (<a class="group-link" href="chap-option.html">option</a>)
</h2>

```chapter-links-option
  [Option Groups] strict:all   ysh:upgrade   ysh:all
  [Strictness]    ... More Runtime Errors
                  strict_argv            No empty argv
                  strict_arith           Fatal parse errors (on by default)
                  strict_array           Arrays don't decay to strings
                  strict_control_flow    Disallow misplaced keyword, empty arg
                  strict_errexit         Disallow code that ignores failure
                  strict_nameref         trap invalid variable names
                  strict_word_eval       Expose unicode and slicing errors
                  strict_tilde           Tilde subst can result in error
                  X strict_glob          Parse the sublanguage more strictly
  [YSH Upgrade]   ... Migrate Existing Code to YSH
                  parse_at               echo @array @[arrayfunc(x, y)]
                  parse_brace            if true { ... }; cd ~/src { ... }
                  parse_equals           x = 'val' in Caps { } config blocks
                  parse_paren            if (x > 0) ...
                  parse_proc             proc p { ... }
                  parse_triple_quote     """$x"""  '''x''' (command mode)
                  parse_ysh_string       echo r'\' u'\\' b'\\' (command mode)
                  command_sub_errexit    Synchronous errexit check
                  process_sub_fail       Analogous to pipefail for process subs
                  sigpipe_status_ok      status 141 -> 0 in pipelines
                  simple_word_eval       No splitting, static globbing
                  xtrace_rich            Hierarchical and process tracing
                  xtrace_details (-u)    Disable most tracing with +
                  dashglob (-u)          Disabled to avoid files like -rf
                  expand_aliases (-u)    Whether aliases are expanded
                  redefine_proc (-u)     Can procs be redefined?
  [Interactive]   redefine_module        'module' builtin always returns 0
                  X redefine_const       Can consts be redefined?
  [Simplicity]    ... More Consistent Style
                  simple_echo            echo takes 0 or 1 arguments
                  simple_eval_builtin    eval takes exactly 1 argument
                  simple_test_builtin    3 args or fewer; use test not [
                  X simple_trap          Function name only
  [YSH Breaking]  ... The Full YSH Language
                  parse_at_all           @ starting any word is an operator
                  parse_backslash (-u)    Allow bad backslashes in "" and $''
                  parse_backticks (-u)    Allow legacy syntax `echo hi`
                  parse_bare_word (-u)   'case unquoted' and 'for x in unquoted'
                  parse_dollar (-u)      Allow bare $ to mean \$  (maybe $/d+/)
                  parse_dparen (-u)      Is (( legacy arithmetic allowed?
                  parse_ignored (-u)     Parse, but ignore, certain redirects
                  parse_sh_arith (-u)    Allow legacy shell arithmetic
                  X copy_env (-u)        Use $[ENV->PYTHONPATH] when false
                  X old_builtins (-u)    local/declare/etc.  pushd/popd/dirs
                                         ... source  unset  printf  [un]alias
                                         ... getopts
                  X old_syntax (-u)      [[   $(( ))  ( )   ${x%prefix}
                                         ${a[@]}   $$
  [Compatibility] eval_unsafe_arith      Allow dynamically parsed a[$(echo 42)]
                  verbose_errexit        Whether to print detailed errors
  [More Options]  _allow_command_sub     To implement strict_errexit, eval_unsafe_arith
                  _allow_process_sub     To implement strict_errexit
                  dynamic_scope          To implement 'proc'
```

<h2 id="special-var">
  Special Variables (<a class="group-link" href="chap-special-var.html">special-var</a>)
</h2>

```chapter-links-special-var
  [YSH Vars]      ARGV   X ENV  X _ESCAPE
                  _this_dir
  [YSH Status]    _status   _error
                  _pipeline_status   _process_sub_status
  [YSH Tracing]   SHX_indent   SHX_punct   SHX_pid_str
  [YSH read]      _reply
  [History]       YSH_HISTFILE
  [Oils VM]       OILS_VERSION
                  OILS_GC_THRESHOLD   OILS_GC_ON_EXIT
                  OILS_GC_STATS   OILS_GC_STATS_FD
X [Wok]           _filename   _line
X [Builtin Sub]   _buffer
```

<h2 id="type-method">
  Builtin Types and Methods (<a class="group-link" href="chap-type-method.html">type-method</a>)
</h2>

```chapter-links-type-method
  [Primitive] Bool   Int   Float   Str   Slice   Range   
  [Str]       X find(eggex)   replace()
              startsWith()   X endsWith()
              trim()   trimLeft()   trimRight()
              X trimPrefix()   X trimSuffix()
              upper()   lower()  # ascii or unicode
              search()   leftMatch()              
  [Match]     group()   start()   end()
              X groups()   X groupDict()
  [List]      append()   pop()   extend()   indexOf()
              X insert()   X remove()   reverse()
  [Dict]      keys()   values()   X get()   X erase()
              X inc()   X accum()
X [Func]      name()   location()   toJson()
X [Proc]      name()   location()   toJson()
X [Module]    name()   filename()
  [Place]     setValue()
  [IO]        X eval()   X captureStdout()
              promptVal()
              X time()   X strftime()
              X glob()
  [Quotation] Expr   X Template   Command
  [Code]      BuiltinFunc   BuiltinMethod
X [Guts]      heapId()
```

<h2 id="builtin-func">
  Builtin Functions (<a class="group-link" href="chap-builtin-func.html">builtin-func</a>)
</h2>

```chapter-links-builtin-func
  [Values]        len()   type()   X repeat()
  [Conversions]   bool()   int()   float()   str()   list()   dict()
                  X chr()   X ord()   X runes()
X [Str]           strcmp()   X split()   shSplit()
  [List]          join()   any()   all()
  [Collections]   X copy()   X deepCopy()
  [Word]          glob()   maybe()
  [Math]          abs()   max()   min()   X round()   sum()
  [Serialize]     toJson()   fromJson()
                  toJson8()   fromJson8()
X [J8 Decode]     J8.Bool()   J8.Int()  ...
X [Codecs]        quoteUrl()   quoteHtml()   quoteSh()   quoteC()
                  quoteMake()   quoteNinja()
  [Pattern]       _group()   _start()   _end()
  [Introspection] shvarGet()   evalExpr()
  [Hay Config]    parseHay()   evalHay()
X [Wok]           _field()
X [Hashing]       sha1dc()   sha256()
```

<h2 id="plugin">
  Plugins and Hooks (<a class="group-link" href="chap-plugin.html">plugin</a>)
</h2>

```chapter-links-plugin
  [YSH]   renderPrompt()
```
