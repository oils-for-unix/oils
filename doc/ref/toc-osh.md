---
title: OSH Table of Contents
all_docs_url: ..
css_files: ../../web/base.css ../../web/manual.css ../../web/ref-index.css
preserve_anchor_case: yes
---

<div class="doc-ref-header">

[Oils Reference](index.html) &mdash;
**OSH Table of Contents** | [YSH](toc-ysh.html) | [Data Notation](toc-data.html)

</div>

[OSH]($xref) is a POSIX- and [bash]($xref)-compatible shell.

<!--
<div class="custom-toc">

[OSH Types](#type-method) <br/>
[Builtin Commands](#builtin-cmd) <br/>
[Front End](#front-end) <br/>
[Command Language](#cmd-lang) <br/>
[OSH Assignment](#osh-assign) <br/>
[Word Language](#word-lang) <br/>
[Mini Languages](#mini-lang) <br/>
[Shell Options](#option) <br/>
[Special Variables](#special-var) <br/>
[Plugins and Hooks](#plugin) <br/>

[type-method](#type-method) &nbsp;
[builtin-cmd](#builtin-cmd) &nbsp;
[front-end](#front-end) &nbsp;
[cmd-lang](#cmd-lang) &nbsp;
[osh-assign](#osh-assign) &nbsp;
[word-lang](#word-lang) &nbsp;
[mini-lang](#mini-lang) &nbsp;
[option](#option) &nbsp;
[special-var](#special-var) &nbsp;
[plugin](#plugin)

</div>
-->

<h2 id="type-method">
  OSH Types <a class="group-link" href="chap-type-method.html">type-method</a>
</h2>

```chapter-links-type-method
  [OSH]           BashArray   BashAssoc
```

<h2 id="builtin-cmd">
  Builtin Commands <a class="group-link" href="chap-builtin-cmd.html">builtin-cmd</a>
</h2>

```chapter-links-builtin-cmd
  [I/O]           read        echo      printf
                  readarray   mapfile
  [Run Code]      source .    eval      trap
  [Set Options]   set         shopt
  [Working Dir]   cd          pwd       pushd     popd         dirs
  [Completion]    complete    compgen   compopt   compadjust   compexport
  [Shell Process] exec      X logout 
                  umask       ulimit    times
  [Child Process] jobs        wait
                  fg        X bg      X kill        X disown 
  [External]      test [      getopts
  [Introspection] help        hash      cmd/type    X caller
  [Word Lookup]   command     builtin
  [Interactive]   alias       unalias   history     X fc     X bind
X [Unsupported]   enable
```

<h2 id="stdlib">
  Standard Library <a class="group-link" href="chap-stdlib.html">stdlib</a>
</h2>

```chapter-links-stdlib
  [two]            log             die
  [byo-server-lib] byo-maybe-run   byo-must-run
```
  <!--
  [bash-strict.sh]
  [taskfile.sh]
  -->

<h2 id="front-end">
  Front End <a class="group-link" href="chap-front-end.html">front-end</a>
</h2>

```chapter-links-front-end
  [Usage]         oils-usage   osh-usage             config
                  startup      line-editing          exit-codes
  [Lexing]        comment #    line-continuation \   ascii-whitespace [ \t\r\n]
```

<h2 id="cmd-lang">
  Command Language <a class="group-link" href="chap-cmd-lang.html">cmd-lang</a>
</h2>

```chapter-links-cmd-lang
  [Commands]      simple-command            semicolon ;
  [Conditional]   case        if            dbracket [[
                  true        false         colon :
                  bang !      and &&        or ||
  [Iteration]     while       until         for            for-expr-sh ((
  [Control Flow]  break       continue      return         exit
  [Grouping]      sh-func     sh-block {    subshell (
  [Concurrency]   pipe |    X pipe-amp |&   ampersand &
  [Redirects]     redir-file  >  >>  >|  <  <>   not impl: &>
                  redir-desc  >&  <&
                  here-doc    <<  <<-  <<<
  [Other Command] dparen ((   time        X coproc       X select
```

<h2 id="osh-assign">
  Assignments and Expressions <a class="group-link" href="chap-osh-assign.html">osh-assign</a>
</h2>

```chapter-links-osh-assign
  [Literals]      sh-array      array=(a b c)   array[1]=B   "${a[@]}"
                  sh-assoc      assoc=(['a']=1 ['b']=2)   assoc['x']=b
  [Operators]     sh-assign     str='xyz'
                  sh-append     str+='abc'
  [Builtins]      local     readonly    export   unset   shift
                  declare   typeset   X let
```

<h2 id="word-lang">
  Word Language <a class="group-link" href="chap-word-lang.html">word-lang</a>
</h2>

<!-- linkify_stop_col is 33 -->

```chapter-links-word-lang_33
  [Quotes]        osh-string    'abc'  $'line\n'  "$var"
  [Substitutions] command-sub   $(command)   `command`
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

<h2 id="mini-lang">
  Other Mini Languages <a class="group-link" href="chap-mini-lang.html">mini-lang</a>
</h2>

<!-- linkify_stop_col is 33 -->

```chapter-links-mini-lang_33
  [Arithmetic]    arith-context Where legacy arithmetic is allowed
                  sh-numbers    0xFF  0755  etc.
                  sh-arith      1 + 2*3   a *= 2
                  sh-logical    !a && b
                  sh-bitwise    ~a ^ b
  [Boolean]       bool-expr     [[ ! $x && $y || $z ]]
                                test ! $x -a $y -o $z
                  bool-infix    $a -nt $b    $x == $y
                  bool-path     -d /etc
                  bool-str      -n foo   -z '' 
                  bool-other    -o errexit   -v name[index]
  [Patterns]      glob-pat      *.py
                  extglob       ,(*.py|*.sh)
                  regex         [[ foo =~ [a-z]+ ]]
  [Other Sublang] braces        {alice,bob}@example.com
                  histsub       !$  !!  !n
                  char-escapes  \t  \c  \x00  \u03bc
```

<h2 id="option">
  Global Shell Options <a class="group-link" href="chap-option.html">option</a>
</h2>

<!-- linkify_stop_col is 20 since we only want section links -->

```chapter-links-option_22
  [Errors]         nounset -u      errexit -e   inherit_errexit   pipefail
  [Globbing]       noglob -f       nullglob     failglob        X dotglob
                   dashglob (true)
  [Debugging]      xtrace        X verbose    X extdebug
  [Interactive]    emacs           vi
  [Other POSIX]  X noclobber
  [Compat]         eval_unsafe_arith            ignore_flags_not_impl
```

<h2 id="special-var">
  Special Variables <a class="group-link" href="chap-special-var.html">special-var</a>
</h2>

```chapter-links-special-var
  [POSIX Special] $@  $*  $#     $?  $-     $$  $!   $0  $9
  [Shell Vars]    IFS             X LANG       X GLOBIGNORE
  [Shell Options] SHELLOPTS       X BASHOPTS
  [Other Env]     HOME              PATH
  [Other Special] BASH_REMATCH     @PIPESTATUS
  [Platform]      HOSTNAME          OSTYPE
  [Call Stack]    @BASH_SOURCE     @FUNCNAME    @BASH_LINENO   
                X @BASH_ARGV     X @BASH_ARGC
  [Tracing]       LINENO
  [Process State] UID               EUID         PPID       X BASHPID
X [Process Stack] BASH_SUBSHELL     SHLVL
X [Shell State]   BASH_CMDS        @DIRSTACK
  [Completion]   @COMP_WORDS        COMP_CWORD    COMP_LINE   COMP_POINT
                  COMP_WORDBREAKS  @COMPREPLY   X COMP_KEY
                X COMP_TYPE         COMP_ARGV
  [History]       HISTFILE
  [cd]            PWD               OLDPWD      X CDPATH
  [getopts]       OPTIND            OPTARG      X OPTERR
  [read]          REPLY
  [Functions]   X RANDOM            SECONDS
```

<h2 id="plugin">
  Plugins and Hooks <a class="group-link" href="chap-plugin.html">plugin</a>
</h2>

```chapter-links-plugin
  [Signals]       SIGTERM     SIGINT     SIGQUIT
                  SIGTTIN     SIGTTOU    SIGWINCH
  [Traps]         DEBUG       ERR        EXIT    X RETURN
  [Words]         PS1       X PS2      X PS3       PS4
  [Completion]    complete
  [Other Plugin]  PROMPT_COMMAND       X command_not_found    
```
