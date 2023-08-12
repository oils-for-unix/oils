---
in_progress: yes
css_files: ../../web/base.css ../../web/ref-index.css ../../web/toc.css
---

Index of YSH Topics
===

These are links to topics in the [Oils Reference](index.html).

Siblings: [OSH Topics](index-osh.html), [Data Topics](index-data.html)

<div id="toc">
</div>


<h2 id="front-end">
  Front End (<a class="group-link" href="chap-front-end.html">front-end</a>)
</h2>

```chapter-links-front-end
  [Usage]         bundle-usage   ysh-usage
  [Oil Lexing]    doc-comment ###   multiline-command ...
```

<h2 id="cmd-lang">
  Command Language (<a class="group-link" href="chap-cmd-lang.html">cmd-lang</a>)
</h2>

```chapter-links-cmd-lang
  [Commands]      proc-def      proc p (out Ref; pos, ...rest; n=0; b Block) {
                  func-def      func f(x; opt1, opt2) { return (x + 1) }
                  ysh-return    return (myexpr)
                  error         error (status=3)
                  equal =       = 1 + 2*3
                  underscore _  _ mylist->append(42)
  [YSH Simple]    typed-arg     json write (x)
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
  [Keywords]      const   var   setvar   setglobal   setref
  [Literals]      bool-literal  true   false   null
                  int-literal   42  65_536  0xFF  0o755  0b10
                  X float-lit   3.14  1.5e-10
                  num-suffix    42 K Ki M Mi G Gi T Ti / ms us
                  rune-literal  #'a'   #'_'   \n   \\   \u{3bc}
                  str-literal   r'[a-z]\n'  X j"line\n"  
                  X multi-str   """  r'''  j"""
                  list-literal  ['one', 'two', 3]  :| unquoted words |
                  dict-literal  {name: 'bob'}
                  block-literal ^(echo $PWD)
                  X expr-lit    ^[1 + 2*3]
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
                  func-call     f(x, y)   s->startswith('prefix')
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
                  X argparse             getopts replacement, sets OPT
                  X setref               Builtin to replace keyword
                  pp                     Pretty print interpreter state
  [Handle Errors] try                    Run with errexit and set _status
                  boolstatus             Enforce 0 or 1 exit status
                  X error                Can be used in both proc and func
  [Shell State]   ysh-cd   ysh-shopt     compatible, and takes a block
                  shvar                  Temporary modify global settings
                  push-registers         Save registers like $?, PIPESTATUS
  [Modules]       runproc                Run a proc; use as main entry point
                  module                 guard against duplicate 'source'
                  use                    change first word lookup
  [I/O]           ysh-read               Buffered I/O with --line, --all, --qsn
                  X ysh-echo             no -e -n with simple_echo
                  write                  Like echo, with --, --sep, --end, ()
                  fork   forkwait        Replace & and (), and takes a block
                  fopen                  Open multiple streams, takes a block
                  X dbg                  Only thing that can be used in funcs
                  X log   X die          common functions (polyfill)
  [Hay Config]    hay   haynode          For DSLs and config files
  [Data Formats]  json
                  X j8str                Upgrade JSON with binary, utf-8
                  X json8                Tree-shaped
                  X tsv8                 Table-shaped
                  X packle               Graph-shaped
X [TSV8]          rows                   pick rows; dplyr filter()
                  cols                   pick columns ('select' already taken)
                  group-by               add a column with a group ID [ext]
                  sort-by                sort by columns; dplyr arrange() [ext]
                  summary                count, sum, histogram, etc. [ext]
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
                  parse_sh_assign (-u)   Are legacy a=b and PATH=. cmd allowed?
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
  [Null]      x
  [Bool]      fromStr()
  [Int]       fromStr()
  [Str]       toJ8()
  [List]      x
  [Dict]      x
  [Eggex]     x
  [Template]  x
  [Expr]      x
  [Command]   x
  [Proc]      x
  [Func]      x
  [Slice]     x
  [Range]     x
```

<h2 id="builtin-func">
  Builtin Functions (<a class="group-link" href="chap-builtin-func.html">builtin-func</a>)
</h2>

```chapter-links-builtin-func
  [Pattern]       _match()   X _start()   X _end()
X [Wok]           _field()
  [Collections]   len()
X [String]        find(eggex)   replace(eggex, template)   join() 
                  split()             $IFS, awk algorithm, regex
  [Word]          glob()   maybe()
  [Arrays]        X index()   append()   extend()
  [Assoc Arrays]  keys()   values()
  [Introspection] shvar_get()   VM.funcs()   VM.procs()
                  VM.types()
X [Hay Config]    parse_hay()   eval_hay()   block_as_str()   
X [Better Syntax] lstrip()   rstrip()   lstripglob()   rstripglob()
                  upper()   lower()
                  strftime()
X [Codecs]        posix-sh-str   html-utf8
X [Hashing]       sha1   sha256 (etc.)
```
