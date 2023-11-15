---
default_highlighter: oils-sh
---

Getting Started
===============

There are many ways to use Oils!

- You can use it *interactively*, or you can write "shell scripts" with it.
  Shell is the best language for *ad hoc* automation.
- You can use it in *compatible* mode with `bin/osh`, or in *legacy-free* mode
  with `bin/ysh`.

As of 2023, [OSH][] is mature, and [YSH][YSH] is under development.  See [blog
posts tagged #FAQ][blog-faqs] for more detail.

[OSH]: https://www.oilshell.org/cross-ref.html?tag=OSH#OSH
[YSH]: https://www.oilshell.org/cross-ref.html?tag=YSH#YSH

This doc walks you through setting up Oils, explains some concepts, and links
to more documentation.

<div id="toc">
</div>

## Setup

### Downloading Oils

The [releases page](https://www.oilshell.org/releases.html) links to source
tarballs for every release.  It also links to the documentation tree, which
includes this page.

### Your Configuration Dir

After running the instructions in [INSTALL](INSTALL.html), run:

    mkdir -p ~/.config/oils       # for oshrc and yshrc
    mkdir -p ~/.local/share/oils  # for osh_history

### Initialization with `rc` Files

Note that

- `bin/osh` runs `~/.config/oils/oshrc`
- `bin/ysh` runs `~/.config/oils/yshrc`

These are the **only** files that are "sourced".  Other shells [have a
confusing initialization sequence involving many files][mess] ([original][]).
It's very hard to tell when and if `/etc/profile`, `~/.bashrc`,
`~/.bash_profile`, etc. are executed.

OSH and YSH intentionally avoid this.  If you want those files, simply `source`
them in your `oshrc`.

[mess]: https://shreevatsa.wordpress.com/2008/03/30/zshbash-startup-files-loading-order-bashrc-zshrc-etc/

[original]: http://www.solipsys.co.uk/new/BashInitialisationFiles.html

I describe my own `oshrc` file on the Wiki: [How To Test
OSH](https://github.com/oilshell/oil/wiki/How-To-Test-OSH).

## Tips

- If you get tired of typing `~/.config/oils/oshrc`, symlink it to `~/.oshrc`.

### Troubleshooting

- If you're running OSH from `bash` or `zsh`, then the prompt string `$PS1` may
  be unintentionally inherited.  Running `PS1=''` before `bin/osh` avoids this.
  This is also true for `$PS2`, `$PS4`, etc.
- On Arch Linux and other distros,`$LANG` may not get set without
  `/etc/profile`.  Adding `source /etc/profile` to your `oshrc` may solve this
  problem.

### `sh` and Bash Docs Are Useful for OSH

Existing educational materials for the Unix shell apply to OSH, because they
generally don't teach the quirks that OSH disallows.  For example, much of the
information and advice in [BashGuide][] can be used without worrying about
which shell you're using.  See the end of this manual for more resources.

For this reason, we're focusing efforts on documenting [YSH][].

## What Is Expected to Run Under OSH

"Batch" programs are most likely to run unmodified under OSH.  On the other
hand, Interactive programs like `.bashrc` and bash completion scripts may
require small changes.

- Wiki: [What Is Expected to Run Under OSH]($wiki)

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


### `OILS_HIJACK_SHEBANG`

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

    OILS_HIJACK_SHEBANG=osh osh myscript.sh

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

### More

For more features unique to Oils, see [Why Use Oils?][why]

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

