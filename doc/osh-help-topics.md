---
in_progress: yes
css_files: ../web/base.css ../web/help-index.css ../web/toc.css
---

OSH Help Topics
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

This is the online help for the OSH language.  It underlies the `help` builtin.

For example, typing `help if` in the shell shows you how to use the `if`
statement.  A link to this same text appears in the [`command`](#command)
**group** below, under the `[Conditional]` **section**.

To view this index inside the shell, use:

    help osh

An <span style="color: darkred">X</span> next to a help topic means that the
feature is **unimplemented**.

You may also want to browse [Oil Help Topics](oil-help-topics.html).

<div id="toc">
</div>


<h2 id="overview">
  Overview (<a class="group-link" href="osh-help.html#overview">overview</a>)
</h2>

```osh-help-topics
  [Usage]         osh-usage   config   startup   line-editing   prompt
  [Lexing]        comment #   line-continuation \
```

<h2 id="command">
  Command Language (<a class="group-link" href="osh-help.html#command">command</a>)
</h2>

```osh-help-topics
  [Commands]      simple-command   semicolon ;
  [Conditional]   case   if   true   false   colon :
                  bang !   and &&   or ||   dbracket [[
  [Iteration]     while   until   for   for-expr-sh ((
  [Control Flow]  break   continue   return   exit
  [Grouping]      sh-func   sh-block {   subshell (
  [Concurrency]   pipe   |   X |&
                  ampersand &
  [Redirects]     redir-file  >  >>  >|  <  <>   X &>
                  redir-desc  >&  <&
                  here-doc    <<  <<-  <<<
  [Other Command] dparen ((   time   X coproc   X select
```

<h2 id="assign">
  Assignments and Expressions (<a class="group-link" href="osh-help.html#assign">assign</a>)
</h2>

```osh-help-topics
  [Literals]      sh-array      array=(a b c)   array[1]=B   "${a[@]}"
                  sh-assoc      assoc=(['a']=1 ['b']=2)   assoc['x']=b
  [Operators]     sh-assign     str='xyz'
                  sh-append     str+='abc'
  [Builtins]      local   readonly   export   unset   shift
                  declare   typeset   X let
```

<h2 id="word">
  Word Language (<a class="group-link" href="osh-help.html#word">word</a>)
</h2>

```osh-help-topics
  [Quotes]        quotes        'abc'  $'\n'  "$var"
  [Substitutions] com-sub       $(command)   `command`   @(split command)
                  var-sub       ${var}   $0   $9   
                  arith-sub     $((1 + 2))
                  tilde-sub     ~/src
                  proc-sub      diff <(sort L.txt) <(sort R.txt)
  [Var Ops]       op-test       ${x:-default}  
                  op-strip      ${x%%suffix}  etc.
                  op-replace    ${x//y/z}
                  op-index      ${a[i+1}
                  op-slice      ${a[@]:0:1}
                  op-format     ${x@P}
```

<h2 id="sublang">
  Other Shell Sublanguages (<a class="group-link" href="osh-help.html#sublang">sublang</a>)
</h2>

```osh-help-topics
  [Arithmetic]    arith-context Where legacy arithmetic is allowed
                  sh-numbers    0xFF  0755  etc.
                  sh-arith      1 + 2*3   a *= 2
                  sh-logical    !a && b
                  sh-bitwise    ~a ^ b
  [Boolean]       dbracket      [[ vs. the test builtin
                  bool-expr       [[ ! $x && $y || $z ]]
                                test ! $x -a $y -o $z
                  bool-infix    [[ $a -nt $b ]]  [[ $x == $y ]]
                  bool-path     [[ -d /etc ]]
                  bool-str      [[ -z '' ]]
                  bool-other    [[ -o errexit ]]
  [Patterns]      glob          *.py
                  extglob       ,(*.py|*.sh)
                  regex         [[ foo =~ [a-z]+ ]]
  [Brace Expand]  braces        {alice,bob}@example.com
  [History]       histsub       !$  !!  !n
```

<h2 id="builtin">
  Builtin Commands (<a class="group-link" href="osh-help.html#builtin">builtin</a>)
</h2>

```osh-help-topics
  [I/O]           read   echo 
                  readarray   mapfile
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
```

<h2 id="option">
  Shell Options (<a class="group-link" href="osh-help.html#option">option</a>)
</h2>

```osh-help-topics
  [Errors]        nounset   pipefail   errexit   inherit_errexit
  [Globbing]      noglob   nullglob   X failglob   dashglob
  [Debugging]     xtrace   X verbose   X extdebug
  [Interactive]   emacs   vi
  [Other Option]  X noclobber
```

<h2 id="env">
  Environment Variables (<a class="group-link" href="osh-help.html#env">env</a>)
</h2>

```osh-help-topics
  [Shell Options] SHELLOPTS   X BASHOPTS
  [Other Env]     HOME   PATH   IFS
```


<h2 id="special">
  Special Variables (<a class="group-link" href="osh-help.html#special">special</a>)
</h2>

```osh-help-topics
  [POSIX Special] $@  $*  $#     $?  $-     $$  $!   $0  $9
  [Other Special] BASH_REMATCH   @PIPESTATUS
  [Platform]      HOSTNAME   OSTYPE
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
  Plugins and Hooks (<a class="group-link" href="osh-help.html#plugin">plugin</a>)
</h2>

```osh-help-topics
  [Signals]       SIGTERM   X SIGINT   X SIGABRT   SIG...
  [Traps]         EXIT   X ERR   X DEBUG   X RETURN
  [Words]         PS1   X PS2   X PS3   PS4
  [Completion]    complete
  [Other Plugin]  X command_not_found   PROMPT_COMMAND
```
