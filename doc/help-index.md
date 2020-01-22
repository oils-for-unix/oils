---
in_progress: yes
css_files: ../web/base.css ../web/help-index.css ../web/toc.css
---

Oil Help Topics
===============

<!--
IMPORTANT: This doc is processed in TWO WAYS.  BE CAREFUL WHEN EDITING.

- First by doctools/{split_doc,cmark}.py to create HTML.
  - <pre><code class="language-oil-help-index"> highlighted using 
    make_help.HelpIndexPlugin

- Then that HTML is split up into cards.
  - <h2 id="assign"> is a heading
  - <pre><code class="language-oil-help-index"> is rendered back into literal
    text.  This makes the escaping of and & < > work.

Special rules:
- [] at start of line is a section
- X for deprecated
- three spaces separating words to be highlighted

TODO: There should be a character for "no links past here?"
- or <span></span>
- this should be turned GREEN?
-->

This is the online version of Oil's `help`.  The linked help topics below are
divided into groups and sections.

For example, typing `help if` in the shell shows you how to use the `if`
statement.  A link to this same text appears in the [`command`](#command)
**group** below, under the `[Conditional]` **section**.

To view this index inside the shell, use:

    help index           # all 12 groups
    help index GROUP+    # show one or more groups

An <span style="color: darkred">X</span> next to a help topic means that it's
an **unimplemented** feature.

<div id="toc">
</div>


<h2 id="overview">
  Overview (<a class="group-link" href="help.html#overview">overview</a>)
</h2>

```oil-help-index
  [Usage]         bundle-usage   osh-usage   oil-usage   config   startup
                  line-editing   prompt
  [Lexing]        comment #   line-continuation \
  [Oil Lexing]    X single-command %%%   X docstring ###
```

<h2 id="command">
  Command Language (<a class="group-link" href="help.html#command">command</a>)
</h2>

```oil-help-index
  [Commands]      simple-command   semicolon ;
  [Conditional]   case   if   true   false   colon :
                  bang !   and &&   or ||   dbracket [[
  [Iteration]     while   until   for   for-expr-sh ((
  [Control Flow]  break   continue   return   exit
  [Grouping]      function   block {   subshell (
  [Concurrency]   pipe   |   X |&
                  ampersand &
  [Redirects]     redir-file  >  >>  >|  <  <>   X &>
                  redir-desc  >&  <&
                  here-doc    <<  <<-  <<<
  [Other Command] dparen ((   time   X coproc   X select
  [Oil Keywords]  proc   return   equal =
```

<h2 id="assign">
  Variable Assignments (<a class="group-link" href="help.html#assign">assign</a>)
</h2>

```oil-help-index
  [Operators]     assign        str='xyz'
                  append        str+='abc'
  [Compound Data] array         array=(a b c)   array[1]=B   "${a[@]}"
                  assoc         assoc=(['a']=1 ['b']=2)   assoc['x']=b
  [Builtins]      local   readonly   export   unset   shift
                  declare   typeset   X let
  [Oil Keywords]  const   var   setvar   set   setglobal   setref
```

<h2 id="expr">
  Oil Expression Language (<a class="group-link" href="help.html#expr">expr</a>)
</h2>

```oil-help-index
  [Functions]     proc-decl     proc p (x, y, @rest, &block) { echo hi }
  [Regexes]       re-literal    /d+/
                  re-compound   ~   (group)   <capture>   sequence
                  re-primitive  %zero   Subpattern   @subpattern
                                'sq'   "dq"   $x   ${x}
                  named-classes dot  digit  space  word  d  s  w
                  class-literal [c a-z 'abc' \\ \xFF \u0100]
                  re-flags      ignorecase etc.
                  re-multiline  ///
                  re-glob-ops   ~   !~
```

<h2 id="word">
  Word Language (<a class="group-link" href="help.html#word">word</a>)
</h2>

```oil-help-index
  [Quotes]        quotes        'abc'  $'\n'  "$var"
  [Substitutions] com-sub       $(command)   `command`
                  var-sub       ${var}   $0   $9   
                  arith-sub     $((1 + 2))
                  tilde-sub     ~/src
                  proc-sub      diff <(sort L.txt) <(sort R.txt)
  [Var Ops]       op-test       ${x:-default}  
                  op-unary      ${x%%suffix}  etc.
                  op-str        ${x//y/z}
                  op-slice      ${a[@]:0:1}
                  op-format     ${x@P}
  [Oil Word]      inline-call   $strfunc(x, y) @arrayfunc(z)
                  splice        @array @ARGV
                  X oil-printf  ${x %.3f}
                  X oil-format  ${x|html}
```

<h2 id="sublang">
  Other Shell Sublanguages (<a class="group-link" href="help.html#sublang">sublang</a>)
</h2>

```oil-help-index
  [Arithmetic]    arith-context Where legacy arithmetic is allowed
                  num-literals  0xFF  0755  etc.
                  math          1 + 2*3
                  arith-logical !a && b
                  bitwise       ~a ^ b
                  arith-assign  a *= 2
  [Boolean]       dbracket      [[ vs. the test builtin
                  bool-expr       [[ ! $x && $y || $z ]]
                                test ! $x -a $y -o $z
                  bool-infix    [[ $a -nt $b ]]  [[ $x == $y ]]
                  bool-path     [[ -d /etc ]]
                  bool-str      [[ -z '' ]]
                  bool-other    [[ -o errexit ]]
  [Patterns]      glob          *.py
                  extglob       @(*.py|*.sh)
                  regex         [[ foo =~ [a-z]+ ]]
  [Brace Expand]  braces        {alice,bob}@example.com
  [History]       histsub       !$  !!  !n
```

<h2 id="builtin">
  Builtin Commands (<a class="group-link" href="help.html#builtin">builtin</a>)
</h2>

```oil-help-index
  [I/O]           read   echo 
                  X readarray   X mapfile
  [Run Code]      source .   eval   trap
  [Set Options]   set   shopt
  [Working Dir]   cd   pwd   pushd   popd   dirs
  [Completion]    complete   compgen   compopt   compadjust
  [Shell Process] exec   X logout 
                  umask   X ulimit   X times
  [Child Process] jobs   wait   ampersand &
                  fg   X bg   X disown 
  [External]      test [   printf   getopts   X kill
  [Introspection] help   hash   type   X caller
  [Word Lookup]   command   builtin
  [Interactive]   alias   unalias   history   X fc   X bind
X [Unsupported]   enable
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
  [Data Formats]  json   X tsv2   X html   X struct/binary
X [External Lang] BEGIN   END   when (awk)
                  rule (make)   each (xargs)   fs (find)
X [Testing]       check
```

<h2 id="option">
  Shell Options (<a class="group-link" href="help.html#option">option</a>)
</h2>

```oil-help-index
  [Errors]        nounset   pipefail   errexit   inherit_errexit
  [Globbing]      noglob   failglob   nullglob
  [Debugging]     xtrace   X verbose   X extdebug
  [Interactive]   emacs   vi
  [Other Option]  X noclobber
  [strict:all]    * All options starting with 'strict_'
                  strict_argv            No empty argv
                  strict_array           Arrays don't decay to strings
                  strict_arith           Fatal parse errors (on by default)
                  strict_errexit         Disallow code that ignores failure
                  strict_eval_builtin    eval takes exactly 1 argument
                  strict_control_flow    Do we need this?  Special builtins?
                  strict_word_eval       Expose unicode and slicing errors
                  X strict_tilde         Tilde subst can result in error
                  X strict_backslash     Parse the sublanguage more strictly
                  X strict_glob          Parse the sublanguage more strictly
                  X strict_trap          Function name only
  [oil:basic]     * Enable Oil functionality
                  parse_at               echo @array @arrayfunc(x, y)
                  parse_brace            if true { ... }; cd ~/src { ... }
                  parse_paren            if (x > 0) ...
                  X parse_redir_expr     >> var x   << 'here string'
                  X longopts             test -file, read -delim, etc.
                  more_errexit           More errexit checks --  at command sub
                  simple_word_eval       No splitting, static globbing
  [oil:nice]      * The full Oil language
                  parse_equals           x = 's' (for cleaner config blocks)
                  parse_set              instead of setvar
                  parse_do               do f(x)
                  X parse_amp            echo hi &2 > /dev/null
                  X parse_dollar_slash   egrep $/ d+ / *.txt
                  X parse_dparen         remove ((
                  X parse_rawc           r'\'   c'\n'   c"$x\n"
                  X simple_test_builtin  Only file tests, remove [, status 2
                  X no_old_builtins      local/declare/etc.  pushd/popd/dirs
                                         ... source  unset  printf  [un]alias
                                         ... getopts
                  X no_old_syntax        [[   $(( ))  ${x%prefix}   $$
                                         $'\n'   @(*.sh|*.py)  `echo comsub`
                                         ${a[@]}
```

<h2 id="env">
  Environment Variables (<a class="group-link" href="help.html#env">env</a>)
</h2>

```oil-help-index
  [Shell Options] SHELLOPTS   X BASHOPTS
  [Other Env]     HOME   PATH   IFS
  [Oil Paths]     ?builtins   ?completion_plugins   ?coprocesses
```


<h2 id="special">
  Special Variables (<a class="group-link" href="help.html#special">special</a>)
</h2>

```oil-help-index
  [POSIX Special] $@  $*  $#     $?  $-     $$  $!   $0  $9
  [Other Special] BASH_REMATCH   @PIPESTATUS
  [Oil Special]   ARGV   STATUS   M
X [Platform]      HOSTNAME   OSTYPE   BASH_VERSION   @BASH_VERSINFO
  [Call Stack]    @BASH_SOURCE   @FUNCNAME   @BASH_LINENO   
                  X @BASH_ARGV   X @BASH_ARGC
  [Tracing]       LINENO   SOURCE_NAME
  [Process State] X BASHPID   X PPID   UID   EUID   
X [Process Stack] BASH_SUBSHELL   SHLVL
X [Shell State]   BASH_CMDS   @DIRSTACK
  [Completion]    @COMP_WORDS   COMP_CWORD   COMP_LINE   COMP_POINT
                  COMP_WORDBREAKS   @COMPREPLY   X COMP_KEY
                  X COMP_TYPE   COMP_ARGV
  [cd]            PWD   OLDPWD   X CDPATH
  [getopts]       OPTIND   OPTARG   X OPTERR
  [read]          REPLY   IFS
  [Functions]     X RANDOM   X SECONDS
```

<h2 id="plugin">
  Plugins and Hooks (<a class="group-link" href="help.html#plugin">plugin</a>)
</h2>

```oil-help-index
  [Signals]       SIGTERM   X SIGINT   X SIGABRT   SIG...
  [Traps]         EXIT   X ERR   X DEBUG   X RETURN
  [Words]         PS1   X PS2   X PS3   PS4
  [Completion]    complete
  [Other Plugin]  X command_not_found   PROMPT_COMMAND
```

<h2 id="lib">
  Oil Libraries (<a class="group-link" href="help.html#lib">lib</a>)
</h2>

```oil-help-index
  [Collections]   len()   copy()
  [Pattern]       regmatch()   fnmatch()
  [String]        find()   sub()   join() 
                  split()             $IFS, awk algorithm, regex
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
