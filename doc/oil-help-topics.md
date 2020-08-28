---
in_progress: yes
css_files: ../web/base.css ../web/help-index.css ../web/toc.css
---

Oil Help Topics
===============

You may also want to browse [OSH Help Topics](help-index.html).

<h2 id="overview">
  Overview (<a class="group-link" href="help.html#overview">overview</a>)
</h2>

```oil-help-topics
  [Usage]         bundle-usage   oil-usage
  [Oil Lexing]    X single-command %%%   X docstring ###
```

<h2 id="command">
  Command Language (<a class="group-link" href="help.html#command">command</a>)
</h2>

```oil-help-topics
  [Oil Keywords]  proc   equal =
  [Oil Blocks]  block
```

<h2 id="assign">
  Variable Assignments (<a class="group-link" href="help.html#assign">assign</a>)
</h2>

```oil-help-topics
  [Oil Keywords]  const   var   setvar   setref   setglobal   setlocal/set
```

<h2 id="word">
  Word Language (<a class="group-link" href="help.html#word">word</a>)
</h2>

```oil-help-topics
  [Oil Word]      inline-call   $strfunc(x, y) @arrayfunc(z)
                  splice        @array @ARGV
                  expr-sub      echo $[3 + a[i]]
                  X oil-printf  ${x %.3f}
                  X oil-format  ${x|html}
```

<h2 id="expr">
  Oil Expression Language (<a class="group-link" href="help.html#expr">expr</a>)
</h2>

```oil-help-topics
  [Functions]     proc-decl     proc p (x, y, @rest, &block) { echo hi }
                  func-call     f(x, y)
  [Literals]      oil-string    c'line\n'  r'[a-z]\n'
                  oil-array     %(a b c)
                  oil-dict      %{name: 'bob'}
                  oil-numbers    42  3.14  1e100
                  oil-bool      true  false
  [Operators]     oil-compare   ==  <=  in
                  oil-logical    not  and  or
                  oil-arith     div  mod
                  oil-bitwise    xor
                  oil-ternary    x if len(s) else y
                  oil-index     a[3]  s[3]
                  oil-slice     a[1:-1]  s[1:-1]
  [Regexes]       re-literal    /d+/
                  re-compound   ~   (group)   <capture>   sequence
                  re-primitive  %zero   Subpattern   @subpattern
                                'sq'   "dq"   $x   ${x}
                  named-classes dot  digit  space  word  d  s  w
                  class-literal [c a-z 'abc' \\ \xFF \u0100]
                  re-flags      ignorecase etc.
                  re-multiline  ///
                  re-glob-ops   ~~   !~~
```

<h2 id="builtin">
  Builtin Commands (<a class="group-link" href="help.html#builtin">builtin</a>)
</h2>

```oil-help-topics
  [Oil Builtins]  cd   X shopt   X env   compatible, and takes a block
                  X fork   X wait        replaces & and (), takes a block
                  X fopen                Many open streams, takes a block
                  X use                  source with namespace, file-relative 
                  X opts                 getopts replacement
                  push                   add elements to end of array
                  repr                   Show debug representation of vars
                  getline                Instead of read -raw :name
                  write                  like echo, but with --, -sep, -end
                  X log   X die          common functions (polyfill)
  [Data Formats]  json   X qtsv   X html   X struct/binary
X [External Lang] BEGIN   END   when (awk)
                  rule (make)   each (xargs)   fs (find)
X [Testing]       check
```

<h2 id="option">
  Shell Options (<a class="group-link" href="help.html#option">option</a>)
</h2>

```oil-help-topics
  [strict:all]    * All options starting with 'strict_'
                  strict_argv            No empty argv
                  strict_arith           Fatal parse errors (on by default)
                  strict_array           Arrays don't decay to strings
                  strict_control_flow    trap misplaced break/continue
                  strict_echo            echo takes 0 or 1 arguments
                  strict_errexit         Disallow code that ignores failure
                  strict_eval_builtin    eval takes exactly 1 argument
                  strict_nameref         trap invalid variable names
                  strict_word_eval       Expose unicode and slicing errors
                  strict_tilde           Tilde subst can result in error
                  X strict_backslash     Parse the sublanguage more strictly
                  X strict_glob          Parse the sublanguage more strictly
                  X strict_trap          Function name only
                  parse_ignored          Parse and silently ignore?
  [oil:basic]     * Enable Oil functionality
                  parse_at               echo @array @arrayfunc(x, y)
                  parse_brace            if true { ... }; cd ~/src { ... }
                  parse_paren            if (x > 0) ...
                  X parse_redir_expr     >> var x   << 'here string'
                  X longopts             test -file, read -delim, etc.
                  more_errexit           More errexit checks --  at command sub
                  simple_word_eval       No splitting, static globbing
                  dashglob               Disabled to avoid files like -rf
  [oil:nice]      * The full Oil language
                  parse_equals           x = 's' (for cleaner config blocks)
                  parse_set              instead of setvar
                  X parse_amp            echo hi &2 > /dev/null
                  X parse_dollar_slash   egrep $/ d+ / *.txt
                  X parse_dparen         remove ((
                  X parse_rawc           r'\'   c'\n'   c"$x\n"
                  X simple_test_builtin  Only file tests, remove [, status 2
                  X no_old_builtins      local/declare/etc.  pushd/popd/dirs
                                         ... source  unset  printf  [un]alias
                                         ... getopts
                  X no_old_syntax        [[   $(( ))  ${x%prefix}   $$
                                         $'\n'   @(*.py|*.sh)  `echo comsub`
                                         ${a[@]}
  [Compatibility] eval_unsafe_arith   parse_dynamic_arith
                  verbose_errexit
```

<h2 id="special">
  Special Variables (<a class="group-link" href="help.html#special">special</a>)
</h2>

```oil-help-topics
  [Oil Special]   ARGV   STATUS   M
  [Platform]      OIL_VERSION
```

<h2 id="lib">
  Oil Libraries (<a class="group-link" href="help.html#lib">lib</a>)
</h2>

```oil-help-topics
  [Collections]   len()   copy()
  [Pattern]       regmatch()   fnmatch()
  [String]        find()   sub()   join() 
                  split()             $IFS, awk algorithm, regex
  [Word]          glob()   maybe()
  [Better Syntax] shquote()
                  lstrip()   rstrip()   lstripglob()   rstripglob()
                  upper()   lower()
                  strftime()
  [Arrays]        index()
  [Assoc Arrays]  @names()   @values()
  [Block]         setvar()            for procs to set in outer scope
                  evalblock()         procs evaluate block to namespace
X [Hashing]       sha1   sha256 (etc.)
```
