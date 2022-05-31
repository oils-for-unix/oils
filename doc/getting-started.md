---
default_highlighter: oil-sh
---

Getting Started
===============

Oilshell provides a **multi-purpose interpreter** runtime.

- You can use it *interactively*, or run and write "shell scripts" for it.</br>
  (Shell is the best language for *ad hoc* automation.)
  
- You can start it to use a language that's *compatible* with other shells (using `bin/osh`),</br>
  or, to use the much improved Oil language, a very coherent *pitfall-freed* shell upgrade with</br>
  selected python/js/etc. features (using `bin/oil`).

As of 2021, the [OSH language][osh-language] is mature, and the [Oil
language][oil-language] is under development.  The interactive shell exists,
but it will be spartan until clients for the "[headless
shell](headless.html)" appear.  (You should still try it!)

See [blog posts tagged #FAQ][blog-faqs] for more detail.

[oil-language]: https://www.oilshell.org/cross-ref.html?tag=oil-language#oil-language
[osh-language]: https://www.oilshell.org/cross-ref.html?tag=osh-language#osh-language


<!-- cmark.py expands this -->
<div id="toc">
</div>

## Install / Setup / Config (move this into INSTALL ?)

### Download

The [releases page](https://www.oilshell.org/releases.html) links to downloads
and documentation (incl. this page) for every release.

After downloading follow the instructions in [INSTALL](INSTALL.html)

### Optional Configuration Directory

After creating the directory:

    mkdir -p ~/.config/oil

OSH will create `osh_history` there to store your command history.

### Initialization with `rc` Files

You can also create your own startup files in this directory:

- `bin/osh` runs `~/.config/oil/oshrc`
- `bin/oil` runs `~/.config/oil/oilrc`

These are the **only** files that are "sourced".  Other shells [have a
confusing initialization sequence involving many files][mess] ([original][]).
It's very hard to tell when and if `/etc/profile`, `~/.bashrc`,
`~/.bash_profile`, etc. are executed.

OSH and Oil intentionally avoid this.  If you want those files, simply `source`
them in your `oshrc`.

[mess]: https://shreevatsa.wordpress.com/2008/03/30/zshbash-startup-files-loading-order-bashrc-zshrc-etc/

[original]: http://www.solipsys.co.uk/new/BashInitialisationFiles.html

I describe my own `oshrc` file on the Wiki: [How To Test
OSH](https://github.com/oilshell/oil/wiki/How-To-Test-OSH).


- If you get tired of typing `~/.config/oil/oshrc`, symlink it to `~/.oshrc`.




## Oilshell Usage (as osh and oil)


<table>
<thead>  <tr>
     <th>
       Task
     </th>
     <th>
       Usage
     </th>
 </tr></thead>
 <tbody> <tr>
     <td>
       **Running an existing script** as initially written for other shells. </br>* Usually not even minimal quoting/spacing adjustments needed. <br/><br/>(Adjustments may only be required due to implementing the "Common Subset" of consistent and sane shell execution compatibility. For example, if a script was using an inconsistent associative array pattern, or relied on dynamic parsing.) </br></br>NB: By default, basic Oil language features without a side-effect beyond occupying namespace do already work as well (e.g. `const`/`var`/`setvar` incl. Oil expressions, `read --line/all/qsn/-0/...`, `write`, etc). So, these only break in other shells if not shipping a fallback.
     </td>
     <td>
       Execute script in osh interpreter:</br>`osh my.sh`</br><br/></br> Or, adapt script, and let it begin with: </br>```#!/usr/bin/env osh```
     </td>
  </tr>
    <tr>
     <td>
       **...and, lint shell fragilities.** <br/> * Improved scripts will run with less errors in other shells.</br><br/>NB: The example on the right enables all strict options at once, but individual strict_* options allow fixing issue by issue.
     </td>
     <td>
       Add a line near the top of the script, to set a shell option with error fallback (keep #!/shebang):</br>`shopt --set strict:all  2>/dev/null || true`</br><br/> *After that* execute the script in osh:</br>`osh my.sh`
     </td>
  </tr>
    <tr>
     <td>
       **...and, allow adding new Oil language syntax.**  <br/> * Adjustments to legacy code will only be needed for a [minimized amount of limited syntax](https://www.oilshell.org/release/latest/doc/deprecations.html). <br/> * However, adding new syntax/semantics to a script will drop compatibility with other shells.</br><br/>(The adjustments needed in legacy code should mostly be just quoting/spacing, for disambiguation. Except, requirements for proper error handling, and for explicit split/glob functions on variables due to the default [Simple Word Evaluation](http://www.oilshell.org/release/latest/doc/simple-word-eval.html). Of course only where variables were originally left correctly(!) unquoted and split/globbed.)
     </td>
     <td>
       Adapt script to begin with: </br>`#!/usr/bin/env osh` </br> `shopt --set oil:upgrade`
     </td>
  </tr>
    <tr>
     <td>
       Coming pretty close to the Oil interpreter. <br/>(Intersection of osh & oil & strict.)
     </td>
     <td>
       `#!/usr/bin/env osh` </br>  `shopt --set oil:upgrade strict:all`</br><!-- prevent line breaks: --> &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;
     </td>
  </tr>
    <tr>
     <td>
       **Using all of the Oil interpeter.** </br>* Implements all positive features of classic shells, compatibly. </br>* All identified pitfalls removed. </br>* Gracefully adding the best from Python, JavaScript and others.<br/><br/> (Everything parsed as Oil syntax. Only unavoidable Oil language warts remain.) 
     </td>
     <td>
       Adapt script to begin with:</br> `#!/usr/bin/env osh` </br> `shopt --set oil:all`</br></br> Or, simply use:</br> `#!/usr/bin/env oil`
     </td>
  </tr>
</tbody>
</table>

 
 For more information see: https://www.oilshell.org/release/latest#Documentation
 
 
### What Is Expected to Run Under OSH

"Batch" programs are most likely to run unmodified under OSH.  On the other
hand, Interactive programs like `.bashrc` and bash completion scripts may
require small changes.

- Wiki: [What Is Expected to Run Under OSH]($wiki)


### `sh` and Bash Docs Are Useful for OSH

Existing educational materials for the Unix shell apply to OSH, because they
generally don't teach the quirks that OSH disallows.  For example, much of the
information and advice in [BashGuide][] can be used without worrying about
which shell you're using.  See the end of this manual for more resources.

For this reason, we're focusing the documenting efforts on the [Oil
language][oil-language].




## Troubleshooting

- If you're running OSH from `bash` or `zsh`, then the prompt string `$PS1` may
  be unintentionally inherited.  Running `PS1=''` before `bin/osh` avoids this.
  This is also true for `$PS2`, `$PS4`, etc.
- On Arch Linux and other distros,`$LANG` may not get set without
  `/etc/profile`.  Adding `source /etc/profile` to your `oshrc` may solve this
  problem.





## Features Unique to OSH

### Dumping the AST

The `-n` flag tells OSH to parse the program rather than executing it.  By
default, it prints an abbreviated abstract syntax tree:

    $ bin/osh -n -c 'ls | wc -l'
    (command.Pipeline children:[(C {(ls)}) (C {(wc)} {(-l)})] negated:F)

You can also ask for the full `text` format:

    $ bin/osh -n --ast-format text -c 'ls | wc -l'
    (command.Pipeline
      children: [
        (command.Simple
          words: [
            (word.Compound
              parts: [(word_part.Literal
                       token:(token id:Lit_Chars val:ls span_id:0))]
            )
          ]
        )
        (command.Simple
          words: [
            (word.Compound
              parts: [(word_part.Literal
                       token:(token id:Lit_Chars val:wc span_id:4))]
            )
            (word.Compound
              parts: [(word_part.Literal
                       token:(token id:Lit_Chars val:-l span_id:6))]
            )
          ]
        )
      ]
      negated: F
      spids: [2]
    )

This format is **subject to change**.  It's there for debugging the parser, but
sophisticated users may use it to interpret tricky shell programs without
running them.


### `OSH_HIJACK_SHEBANG`

This environment variable can be set to the path of a **shell**.  Before OSH
executes a program, it will inspect the shebang line to see if it looks like a
shell script.  If it does, it will use this shell instead of the one specified
in the shebang line.

For example, suppose you have `myscript.sh`:

    #!/bin/sh
    # myscript.sh

    ./otherscript.sh --flag ...

and `otherscript.sh`:

    #!/bin/sh
    # otherscript.sh

    echo 'hello world'

Then you can run `myscript.sh` like this:

    OSH_HIJACK_SHEBANG=osh osh myscript.sh

and `otherscript.sh` will be executed with OSH rather than the `/bin/sh`.

Note that `osh` appears **twice** in that command line: once for the initial
run, and once for all recursive runs.

(This is an environment variable rather than a flag because it needs to be
**inherited**.)

### `--debug-file`

Print internal debug logs to this file.  It's useful to make it a FIFO:

    mkfifo _tmp/debug
    osh --debug-file _tmp/debug

Then run this in another window to see logs as you type:

    cat _tmp/debug

Related:

- The `OSH_DEBUG_DIR` environment variable is the inherited version of
  `--debug-file`.  A file named `$PID-osh.log` will be written in that
  directory for every shell process.
- The `--xtrace-to-debug-file` flag sends `set -o xtrace` output to that file
  instead of to `stderr`.

### Crash Dumps

- TODO: `OSH_CRASH_DUMP_DIR`

This is implemented, but a JSON library isn't in the release build.





## Features Unique to Oil

For more features unique to Oil, see [Why Use Oil?][why]

[why]: https://www.oilshell.org/why.html





## Appendix

### Bugs

- OSH runs shell scripts too slowly.  Speeding it up is a top priority.

### Links

- [Blog Posts Tagged #FAQ][blog-faqs]
  tell you why OSH exists and how it's designed.
- [Known Differences](known-differences.html) lists incompatibilities between
  OSH and other shells.  They are unlikely to appear in real programs, or
  there is a trivial workaround.

[blog-faqs]: https://www.oilshell.org/blog/tags.html?tag=FAQ#FAQ

External:

- [GNU Bash Manual](https://www.gnu.org/software/bash/manual/).  I frequently
  referred to this document when implementing OSH.
- [BashGuide][].  A wiki with detailed information about bash.
  - [BashPitfalls](https://mywiki.wooledge.org/BashPitfalls).
- [Bash Cheat Sheet](https://devhints.io/bash).  A short overview.

[BashGuide]: https://mywiki.wooledge.org/BashGuide

