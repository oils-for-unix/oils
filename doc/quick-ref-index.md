---
css_files: ../web/quick-ref-index.css
title: Index of Help Topics
compact_title: yes
---

<div id="groups">

<!-- this section is only on the web -->

<!--
Below is a list of topics, organized into GROUPS and [Sections].  The X prefix
means "unimplemented".  

This doc can be viewed on the web at:

<https://www.oilshell.org/release/0.7.pre5/doc/quick-ref-index.html>

Or inside Oil with:

    help index
    help index GROUP...

where GROUP is one of:

    intro   cmd   assign   expr   sublang
    builtin   option   vars   plugin   lib

-->

<!--

Format of this doc:

Each <div> gets split up into a "group" panel

- In HTML it can be placed side-by-side, adding links
- In text it becomes 'help index foo'>

- Special rules:
  - [] at start of line is a section
  - X for deprecated
  - three spaces separating words to be highlighted

- TODO: There should be a character for "no links past here?"
  - or <span></span>
  - this should be turned GREEN?
-->


<div id="intro">
<a href="$quick-ref:intro">INTRO</a>
<pre>
  [Usage]         bundle-usage   osh-usage   oil-usage   config   startup
                  line-editing   prompt
  [Lexing]        comments #   line-continuation \
  [Oil Lexing]    single-command %%%   docstring ###
</pre>
</div>


<div id="cmd">
<a href="$quick-ref:cmd">COMMAND LANGUAGE</a>
<pre>
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
  [Oil Keywords]  proc   func   return   do   pass   pp   equal =
X [Coil Keywords] const   try   catch   throw   switch   match
                  data   enum   module   interface   namespace
</pre>
</div>

<div id="assign">
<a href="$quick-ref:assign">VARIABLE ASSIGNMENTS</a>
<pre>
  [Operators]     assign        str='xyz'
                  append        str+='abc'
  [Compound Data] array         array=(a b c)   array[1]=B   "${a[@]}"
                  assoc         assoc=(['a']=1 ['b']=2)   assoc['x']=b
  [Builtins]      local   readonly   export   unset   shift
                  declare   typeset   X let
  [Oil Keywords]  var   setvar   X auto
</pre>
</div>

<div id="expr">
<a href="$quick-ref:expr">OIL EXPRESSION LANGUAGE</a>
<pre>
  [Data Types]    Str           r'\'   c'\n'   "$var"   multiline r""" c'''
                  X Symbol      %foo
                  Null          null
                  Bool          true false
                  Int           1_000_000   0b0100   0xFF  0o377  \n  \\  \u0100
                  Float         3.14   6.022e+23
                  Array[]       @(ls -l)  @[T F F]  @[1 2 3]  @[1.5 2.5] 
                  Tuple[]       ()  tup(42)  (42, "foo")
                  List          [1, 'str', false]  (for JSON compatibility)
                  Dict[]        {name: 'oil'}  {['name']: 'oil'}  {name}
                  Regex         /d+/
                  X Func        fn(x) x+1   func(x) { return x+1 }
                  X Buf         file-like, mutable string
  [Operators]     unary         -a
                  binary        a+b   base^exp  a xor b  p div q  0:n
                  ternary       a if cond else b
                  subscript     a[b, c]   a[start:end]
                  X chain       pass a => f(y, z) => var new
                  getattr       d->key is like d['key'] or d.key
                  scope-attr    module::name
                  genexp   listcomp   X dictcomp
  [Functions]     inline-call   echo $strfunc(x, y) @arrayfunc(z)
                  func-decl     func inc(p, p2=0; n=0, ...named) { echo hi }
                  proc-decl     proc p (x, y, @rest) { echo hi }
  [Regexes]       re-literal    /d+/
                  re-compound   ~   (group)  <capture>    sequence
                  re-primitive  %zero  @other_pattern  'sq'  "dq"  $x  ${x}
                  named-classes dot   digit   space   word   d   s   w
                  class-literal [a-z 'abc' \\ \xFF \u0100]
                  re-flags      ignorecase etc.
                  re-multiline  ///
                  re-api        find()   sub()   split()   regmatch()
                                fnmatch()
                  re-glob-ops   ~   !~
</pre>
</div>

<div id="word">
<a href="$quick-ref:word">WORD LANGUAGE</a>
<pre>
  [Quotes]        quotes        'abc'  $'\n'  "$var"
  [Substitutions] com-sub       $(command)   `command`
                  var-sub       ${var}
                  arith-sub     $((1 + 2))
                  tilde-sub     ~/src
                  proc-sub      diff <(sort L.txt) <(sort R.txt)
  [Special Vars]  special-vars  $@  $*  $#     $?  $-     $$  $!
  [Var Ops]       op-test       ${x:-default}  
                  op-unary      ${x%%suffix}  etc.
                  op-str        ${x//y/z}
                  op-slice      ${a[@]:0:1}
                  op-format     ${x@P}
  [Oil Word]      expr-sub      $[f(x)]   $[obj.attr]   $[d->key]   $[obj[index]]
                  splice        @array @ARGV
                  X oil-printf  ${x %.3f}
                  X oil-format  ${x|html}
</pre>
</div>

<div id="sublang">
<a href="$quick-ref:sublang">OTHER SHELL SUBLANGUAGES</a>
<pre>
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
</pre>
</div>

<div id="builtin">
<a href="$quick-ref:builtin">BUILTIN COMMANDS</a>
<pre>
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
                  X dirname   X basename optimizations
                  X opts                 getopts replacement
                  push                   sugar for 'do array.push( @(a b) )'
                  repr                   Show debug representation of vars
                  X log   X die          common functions (polyfill)
                  X getline              Instead of read -raw :name
                  X json-echo   X json-read  
                  X tsv2-echo   X tsv2-read
X [External Lang] BEGIN   END   when (awk)
                  rule (make)   each (xargs)   fs (find)
</pre>
</div>

<div id="option">
<a href="$quick-ref:option">SHELL OPTIONS</a>
<pre>
  [Errors]        nounset   pipefail   errexit   inherit_errexit
  [Globbing]      noglob   failglob   nullglob
  [Debugging]     xtrace   X verbose   X extdebug
  [Interactive]   emacs   vi
  [Other Option]  X noclobber
  [strict:all]                           All options starting with 'strict_'
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
  [oil:basic]                            Enable Oil functionality
                  parse_at               echo @array @arrayfunc(x, y)
                  parse_brace            if true { ... }; cd ~/src { ... }
                  parse_paren            if (x > 0) ...
                  X parse_redir_expr     >> var x   << 'here string'
                  X longopts             test -file, read -delim, etc.
                  more_errexit           More errexit checks --  at command sub
                  simple_word_eval       No splitting, static globbing
  [oil:nice]                             The full Oil language
                  parse_equals           x = 's' (for cleaner config blocks)
                  parse_set              instead of setvar
                  simple_echo            Doesn't join args; -sep -end and --
                  parse_do               do f(x)
                  X parse_amp            echo hi &2 > /dev/null
                  X parse_dollar_slash   egrep $/ d+ / *.txt
                  X parse_dparen         remove ((
                  X parse_rawc           r'\'   c'\n'   c"$x\n"
                  X simple_test_builtin  Only file tests, remove [, status 2
                  X no_old_builtins      local/declare/etc.  pushd/popd/dirs
                                         source  unset  printf  [un]alias
                                         getopts
                  X no_old_syntax        [[   $(( ))  ${x%prefix}   $$
                                         $'\n'   @(*.sh|*.py)  `echo comsub`
                                         ${a[@]}
</pre>
</div>

<div id="env">
<a href="$quick-ref:env">ENVIRONMENT VARIABLES</a>
<pre>
  [Shell Options] SHELLOPTS   X BASHOPTS
  [Other Env]     HOME   PATH   IFS
  [Oil Paths]     ?builtins   ?completion_plugins   ?coprocesses
</pre>
</div>

<div id="special">
<a href="$quick-ref:special">SPECIAL VARIABLES</a>
<pre>
  [Oil]           ARGV   STATUS
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
  [Other Special] BASH_REMATCH   @PIPESTATUS
</pre>
</div>

<div id="plugin">
<a href="$quick-ref:plugin">PLUGINS AND HOOKS</a>
<pre>
  [Signals]       SIGTERM   X SIGINT   X SIGABRT   SIG...
  [Traps]         EXIT   X ERR   X DEBUG   X RETURN
  [Words]         PS1   X PS2   X PS3   PS4
  [Completion]    complete
  [Other Plugin]  X command_not_found   PROMPT_COMMAND
</pre>
</div>

<div id="lib">
<a href="$quick-ref:lib">OIL LIBRARIES</a>
<pre>
  [Collections]   len()
  [String, Eggex] join()   split()    $IFS, awk algorithm, regex
                  sub()  find()       regex/string functions
  [Block]         setvar()            for procs to set in outer scope
                  evalblock()         procs evaluate block to namespace
  [libc]          read(n)             better than read -n, no short reads?
                  posix::read()       raw bindings?
                  strftime()
X [Testing]       check ?
X [Data Formats]  json   csv   tsv2   struct (binary)
X [Hashing]       sha1, sha256, etc.
</pre>
</div>

<!-- end groups -->
</div>

