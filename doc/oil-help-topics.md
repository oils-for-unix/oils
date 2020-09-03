---
in_progress: yes
css_files: ../web/base.css ../web/help-index.css ../web/toc.css
---

Oil Help Topics
===============

This is the online help for the Oil language.  It underlies the `help` builtin.

For example, typing `help proc` in the shell shows you how to use the `proc`
statement.  A link to this same text appears in the [`command`](#command)
**group** below.

To view this index inside the shell, use:

    help oil

An <span style="color: darkred">X</span> next to a help topic means that the
feature is **unimplemented**.

You may also want to browse [OSH Help Topics](osh-help-topics.html).

<div id="toc">
</div>

<h2 id="overview">
  Overview (<a class="group-link" href="oil-help.html#overview">overview</a>)
</h2>

```oil-help-topics
  [Usage]         bundle-usage   oil-usage
  [Oil Lexing]    X single-command %%%   X docstring ###
```

<h2 id="command">
  Command Language (<a class="group-link" href="oil-help.html#command">command</a>)
</h2>

```oil-help-topics
                  proc       proc p (x, y, @rest, &block) { echo hi }
                  equal =    = 1 + 2*3
                  oil-block  cd /tmp { echo $PWD }
```

<h2 id="assign">
  Assignments and Expression Language (<a class="group-link" href="oil-help.html#assign">assign</a>)
</h2>

```oil-help-topics
  [Keywords]      const   var   setvar   setref   setglobal   setlocal/set
  [Literals]      oil-string    c'line\n'  r'[a-z]\n'
                  oil-array     %(a b c)
                  oil-dict      %{name: 'bob'}
                  oil-numbers    42  3.14  1e100
                  oil-bool      True T   False F   null
  [Operators]     concat        ++ on Str, Array, Dict?
                  oil-equals    ==  !=  ===  !==  in
                  oil-compare   <  <=  >  >=  (numbers only)
                  oil-logical    not  and  or
                  oil-arith     +  -  *  /  div  mod  ^
                  oil-bitwise   ~  &  |  xor  <<  >>
                  oil-ternary   '+' if x >= 0 else '-'
                  oil-index     a[3]  s[3]
                  oil-slice     a[1:-1]  s[1:-1]
                  func-call     f(x, y)
  [Eggex]         re-literal    / d+ /
                  re-compound   ~   (group)   <capture>   sequence
                  re-primitive  %zero   Subpattern   @subpattern
                                'sq'   "dq"   $x   ${x}
                  named-class    dot  digit  space  word  d  s  w
                  class-literal [c a-z 'abc' \\ \xFF \u0100]
                  X re-flags    ignorecase etc.
                  X re-multiline  ///
                  X re-glob-ops   ~~   !~~
```

<h2 id="word">
  Word Language (<a class="group-link" href="oil-help.html#word">word</a>)
</h2>

```oil-help-topics
                  inline-call   $strfunc(x, y) @arrayfunc(z)
                  splice        @myarray @ARGV
                  expr-sub      echo $[3 + a[i]]
                  X oil-printf  ${x %.3f}
                  X oil-format  ${x|html}
```

<h2 id="builtin">
  Builtin Commands (<a class="group-link" href="oil-help.html#builtin">builtin</a>)
</h2>

```oil-help-topics
  [Oil Builtins]  cd   X shopt   X env   compatible, and takes a block
                  X fork   X forkwait    replaces & and (), takes a block
                  X fopen                Many open streams, takes a block
                  X use                  source with namespace, file-relative 
                  X opts                 getopts replacement
                  push                   add elements to end of array
                  repr                   Show debug representation of vars
                  getline                Instead of read -raw :name
                  write                  like echo, but with --, -sep, -end
                  X log   X die          common functions (polyfill)
  [Data Formats]  json   X qtsv
X [External Lang] BEGIN   END   when (awk)
                  rule (make)   each (xargs)   fs (find)
X [Testing]       check
```

<h2 id="option">
  Shell Options (<a class="group-link" href="oil-help.html#option">option</a>)
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
  [oil:all]       * The full Oil language
                  parse_equals           x = 'val' (for cleaner config blocks)
                  parse_set              'set' instead of 'setlocal'
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

<h2 id="env">
  Environment Variables (<a class="group-link" href="oil-help.html#env">env</a>)
</h2>

```oil-help-topics
  [Oil Paths]     ?builtins   ?completion_plugins   ?coprocesses
```

<h2 id="special">
  Special Variables (<a class="group-link" href="oil-help.html#special">special</a>)
</h2>

```oil-help-topics
                  ARGV   STATUS   M
  [Platform]      OIL_VERSION
```

<h2 id="lib">
  Builtin Functions (<a class="group-link" href="oil-help.html#lib">lib</a>)
</h2>

```oil-help-topics
  [Collections]   len()   copy()
X [Pattern]       regmatch()   fnmatch()
X [String]        find()   sub()   join() 
                  split()             $IFS, awk algorithm, regex
  [Word]          glob()   maybe()
X [Arrays]        index()
  [Assoc Arrays]  @keys()   @values()
X [Block]         setvar()            for procs to set in outer scope
                  evalblock()         procs evaluate block to namespace
X [Better Syntax] shquote()
                  lstrip()   rstrip()   lstripglob()   rstripglob()
                  upper()   lower()
                  strftime()
X [Hashing]       sha1   sha256 (etc.)
```
