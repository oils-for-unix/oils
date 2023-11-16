---
in_progress: yes
css_files: ../../web/base.css ../../web/ref-index.css ../../web/toc.css
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
  [Oil Lexing]    doc-comment ###   multiline-command ...
  [Tools]         cat-em
```

<h2 id="cmd-lang">
  Command Language (<a class="group-link" href="chap-cmd-lang.html">cmd-lang</a>)
</h2>

```chapter-links-cmd-lang
  [Commands]      proc-def      proc p (out Ref; pos, ...rest; n=0; b Block) {
                  func-def      func f(x; opt1, opt2) { return (x + 1) }
                  ysh-return    return (myexpr)
                  equal =       = 1 + 2*3
                  dcolon ::     :: mylist->append(42)
  [YSH Simple]    typed-arg     json write (x)
                  lazy-expr-arg assert [42 === x]
                  block-arg     cd /tmp { echo $PWD }
  [Conditional]   ysh-case      case (x) { *.py { echo 'python' } }
                  ysh-if        if (x > 0) { echo }
  [Iteration]     ysh-while     while (x > 0) { echo }
                  ysh-for       for i, item in (mylist) { echo }
```

<h2 id="expr-lang">
  Expression Language and Assignments (<a class="group-link" href="chap-expr-lang.html">expr-lang</a>)
</h2>

```chapter-links-expr-lang
  [Keywords]      const   var   setvar   setglobal
  [Assign Ops]    =   +=   -=   *=   /=   **=   //=   %=
                  &=   |=   ^=   <<=   >>=
  [Literals]      bool-literal  true   false   null
                  int-literal   42  65_536  0xFF  0o755  0b10
                  float-lit     3.14  1.5e-10
                  num-suffix    42 K Ki M Mi G Gi T Ti / ms us
                  rune-literal  #'a'   #'_'   \n   \\   \u{3bc}
                  str-literal   r'[a-z]\n'  X j"line\n"  
                  X multi-str   """  r'''  j"""
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
                  thin-arrow    s->pop()
                  fat-arrow     s => startswith('prefix')
                  match-ops     ~   !~   ~~   !~~
  [Eggex]         re-literal    / d+ /
                  re-compound   pat|alt   pat seq   (group)
                                <capture>   <capture :name> 
                  re-primitive  %zero   Subpattern   @subpattern   'sq'
                                char-class  ! char-class
                  named-class    dot  digit  space  word  d  s  w
                  class-literal [c a-z 'abc' @str_var \\ \xFF \u0100]
                  X re-flags    ignorecase etc.
                  X re-multiline  ///
```

<h2 id="word-lang">
  Word Language (<a class="group-link" href="chap-word-lang.html">word-lang</a>)
</h2>

```chapter-links-word-lang
  [String Lit]    X multi-str   """  r'''  j"""
                  X j8-str      j"byte \y00 unicode \u{123456}"
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
                  pp                     Pretty print interpreter state
  [Handle Errors] try                    Run with errexit and set _status
                  boolstatus             Enforce 0 or 1 exit status
                  error                  error 'failed' (status=2)
  [Shell State]   ysh-cd   ysh-shopt     compatible, and takes a block
                  shvar                  Temporary modify global settings
                  push-registers         Save registers like $?, PIPESTATUS
  [Modules]       runproc                Run a proc; use as main entry point
                  module                 guard against duplicate 'source'
                  is-main                false when sourcing a file
                  use                    change first word lookup
  [I/O]           ysh-read               Buffered I/O with --line, --all, --qsn
                  ysh-echo               no -e -n with simple_echo
                  write                  Like echo, with --, --sep, --end, ()
                  fork   forkwait        Replace & and (), and takes a block
                  fopen                  Open multiple streams, takes a block
                  X dbg                  Only thing that can be used in funcs
                  X log   X die          common functions (polyfill)
  [Hay Config]    hay   haynode          For DSLs and config files
  [Completion]    compadjust   compexport
  [Data Formats]  json                   read write
                  X j8                   read write
                  X packle               read write, Graph-shaped
X [TSV8]          rows                   pick rows; dplyr filter()
                  cols                   pick columns ('select' already taken)
                  group-by               add a column with a group ID [ext]
                  sort-by                sort by columns; dplyr arrange() [ext]
                  summary                count, sum, histogram, etc. [ext]
X [Flags]         Flags                  getopts replacement: flag arg
                  parseArgs()            
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
  [Oil Upgrade]   ... Migrate Existing Code to Oil
                  parse_at               echo @array @[arrayfunc(x, y)]
                  parse_brace            if true { ... }; cd ~/src { ... }
                  parse_equals           x = 'val' in Caps { } config blocks
                  parse_paren            if (x > 0) ...
                  parse_proc             proc p { ... }
                  parse_raw_string       echo r'\' (command mode)
                  parse_triple_quote     """  '''  r'''  $''' in command mode
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
  [Oil Breaking]  ... The Full Oil Language
                  parse_at_all           @ starting any word is an operator
                  parse_backslash (-u)    Bad backslashes in $''
                  parse_backticks (-u)    Legacy syntax `echo hi`
                  parse_bare_word (-u)   'case unquoted' and 'for x in unquoted'
                  parse_dollar (-u)      Is $ allowed for \$?  Maybe $/d+/
                  parse_dparen (-u)      Is (( legacy arithmetic allowed?
                  parse_ignored (-u)     Parse, but ignore, certain redirects
                  parse_sh_arith (-u)    Is legacy shell arithmetic allowed?
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
  [Oil Paths]     ?builtins   ?completion_plugins   ?coprocesses
  [History]       YSH_HISTFILE
  [Shell Vars]    ARGV   X ENV   X OPT
                  X _ESCAPE   _DIALECT
                  _this_dir
  [Platform]      OILS_VERSION
  [Exit Status]   _status   _pipeline_status   _process_sub_status
  [Tracing]       SHX_indent   SHX_punct   SHX_pid_str
X [Wok]           _filename   _line
X [Builtin Sub]   _buffer
```

<h2 id="type-method">
  Builtin Types and Methods (<a class="group-link" href="chap-type-method.html">type-method</a>)
</h2>

```chapter-links-type-method
  [Primitive] Bool   Int   Float   Str   Slice   Range   
  [Str]       X find(eggex)   X replace(eggex, template)
              startsWith()   X endsWith()
              X trim()   X trimLeft()   X trimRight()
              X trimPrefix()   X trimSuffix()
              upper()   lower()  # ascii or unicode
  [List]      append()   pop()   extend()   X find()
              X insert()   X remove()   reverse()
  [Dict]      keys()   values()   X get()   X erase()
              X inc()   X accum()
X [Func]      toJson()
X [Proc]      toJson()
  [Place]     setValue()

  [IO]        X eval()   X captureStdout()
              promptVal()
  [Quotation] Expr   X Template   Command
  [Code]      BuiltinFunc   BuiltinMethod
```

<h2 id="builtin-func">
  Builtin Functions (<a class="group-link" href="chap-builtin-func.html">builtin-func</a>)
</h2>

```chapter-links-builtin-func
  [Values]        len()   type()
  [Conversions]   bool()   int()   float()   str()   list()   dict()
                  X chr()   X ord()
                  X runes()
X [J8 Decode]     J8.Bool()   J8.Int()  ...
  [List]          any()   all()
  [Collections]   join()   split()  # $IFS, awk algorithm, regex
                  X copy()   X deepCopy()
  [Word]          glob()   maybe()
  [Math]          abs()   max()   min()   X round()   sum()
X [Codecs]        quoteUrl()   quoteHtml()   quoteSh()   quoteC()
                  quoteMake()   quoteNinja()
X [Serialize]     toJ8()   fromJ8()
                  toJson()   fromJson()
  [Pattern]       _match()   X _start()   X _end()
  [Introspection] shvarGet()   evalExpr()
  [Hay Config]    parseHay()   evalHay()
X [Date Time]     strftime()
X [Wok]           _field()
X [Hashing]       sha1dc()   sha256()
```
