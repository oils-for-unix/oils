OSH User Manual
===============

OSH is a **Unix shell** designed to run existing shell scripts.  More
precisely, it's

1. POSIX-compatible
2. Has features from GNU Bash, the most commonly used shell.

It's designed to be "stricter" than other shells.  To avoid programs that don't
behave as intended,

1. It produces more errors.
2. It produces them earlier &mdash; at parse time, if possible.

"Batch" programs are most likely to run unmodified under OSH.  Interactive
programs like `.bashrc` and bash completion scripts may require small changes.

This manual covers the **differences** between OSH and other shells.  It leaves
the details of each construct to the `help` builtin and the [Quick
Reference](osh-quick-ref.html) (*Warning: both are incomplete*).  It also
doesn't cover the [Oil language][oil-language], which is a newer part of the
Oil project.

Existing educational materials for the Unix shell apply to OSH, because they
generally don't teach the quirks that OSH disallows.  For example, much of the
information and advice in [BashGuide][] can be used without worrying about
which shell you're using.  See the end of this manual for more resources.


[oil-language]: https://oilshell.org/cross-ref.html?tag=oil-language#oil-language

<!-- cmark.py expands this -->
<div id="toc">
</div>

## Downloading OSH

The [releases page](https://www.oilshell.org/releases.html) links to source
tarballs for every release.  It also links to the documentation tree, which
includes this manual.

## Setup

After running the instructions in [INSTALL](INSTALL.html), run:

    mkdir -p ~/.config/oil

- OSH will create `osh_history` there, to store your command history.
- You can create your own `oshrc` there.

## Startup Files

On startup, the interactive shell sources **only** `~/.config/oil/oshrc`.

Other shells [have a confusing initialization sequence involving many
files][mess] ([original][]).  It's very hard to tell when and if
`/etc/profile`, `~/.bashrc`, `~/.bash_profile`, etc. are executed.

OSH intentionally avoids this.  If you want those files, simply `source` them
in your `oshrc`.

- For example, on Arch Linux and other distros,`$LANG` may not get set without
  `/etc/profile`.  Add `source /etc/profile` to your `oshrc` may solve this
  problem.
- If you get tired of typing `~/.config/oil/oshrc`, symlink it to `~/.oshrc`.

[mess]: https://shreevatsa.wordpress.com/2008/03/30/zshbash-startup-files-loading-order-bashrc-zshrc-etc/

[original]: http://www.solipsys.co.uk/new/BashInitialisationFiles.html

I describe my own `oshrc` file on the wiki: [How To Test
OSH](https://github.com/oilshell/oil/wiki/How-To-Test-OSH).


## Global Execution Options

All Unix shells have global options that affect execution.  There are two
kinds:

- POSIX options like `set -e`, which I prefer to write `set -o errexit`.
- bash extensions like `shopt -s inherit_errexit`

List them all with `set -o` and `shopt -p`.  Other than syntax, there's no
essential difference between the two kinds.

### shopt -s strict:all is Recommended

OSH adds more options on top of those provided by POSIX and bash.  It has  a
shortcut `shopt -s strict:all` which turns on many options at once:

- `errexit`, `nounset` (`sh` modes to get more errors)
- `pipefail` and `inherit_errexit` (`bash` modes to get more errors)
- `nullglob` (a `bash` mode, doesn't confuse code and data)
- `strict_*` (`strict_array`, etc.)
   - Strict options **disallow** certain parts of the language with **fatal
     runtime errors**.

If you want your script to be portable to other shells, use this line:

    shopt -s strict:all 2>/dev/null || true  # suppress errors

You can also turn individual options on or off:

    shopt -s strict_array  # Set this option.  I want more fatal errors.
    shopt -u strict_array  # Unset it.  Ignore errors and keep executing.

### List of Options

`strict_arith`.  Strings that don't look like integers cause a fatal error in
arithmetic expressions.

`strict_argv`.  Empty `argv` arrays are disallowed, since there's no practical
use for them.  For example, the second statement in `x=''; $x` results in a
fatal error.

`strict_array`. No implicit conversions between string an array.  In other
words, turning this on gives you a "real" array type.

`strict_control_flow`. `break` and `continue` outside of a loop are fatal
errors.

`strict_eval_builtin`.  The `eval` builtin takes exactly **one** argument.  It
doesn't concatenate its arguments with a space, or accept zero arguments.

`strict_word_eval`.  More word evaluation errors are fatal.

- String slices with negative arguments like `${s: -1}` and `${s: 1 : -1}`
  result in a fatal error.  (NOTE: In array slices, negative start indices are
  allowed, but negative lengths are always fatal, regardless of
  `strict-word-eval`.)
- UTF-8 decoding errors are fatal when computing lengths (`${#s}`) and slices.

See the [Oil manual](oil-manual.html) for options that fundamentally change the
shell language, e.g. those categorized under `shopt -s oil:all`.

## OSH Has Four `errexit` Options (while Bash Has Two)

The complex behavior of these global execution options requires extra attention
in this manual.

But you don't need to understand all the details.  Simply choose between:

```
# Turn on four errexit options.  I don't run this script with other shells.
shopt -s oil:all
```

and

```
# Turn on three errexit options.  I run this script with other shells.
shopt -s strict:all
```

### Quirk 1: the Shell Sometimes Disables And Restores `errexit`

Here's some background for understanding the additional `errexit` options
described below.

In all Unix shells, the `errexit` check is disabled in these situations:
 
1. The condition of the `if`, `while`, and `until`  constructs
2. A command/pipeline prefixed by `!`
3. Every clause in `||` and `&&` except the last.

Now consider this situation:

1. `errexit` is **on**
2. The shell disables it one of those three situations
3. While disabled, the user touches it with `set -o errexit` (or `+o` to turn
   it off).

Surprising behavior: Unix shells **ignore** the `set` builtin for awhile,
delaying its execution until **after** the temporary disablement.

### Quirk 2: x=$(false) is inconsitent with local x=$(false)

Background: In shell, `local` is a builtin rather than a keyword, which means
`local foo=$(false)` behaves differently than than `foo=$(false)`.

### Additional `errexit` options

OSH aims to fix the many quirks of `errexit`.  It has this bash-compatible
option:

- `inherit_errexit`: `errexit` is inherited inside `$()`, so errors aren't
  ignored.  It's enabled by both `strict:all` and `oil:all`.

And two more options:

- `strict_errexit` makes the quirk above irrelevant.  Compound commands,
  including **functions**, can't be used in any of those three situations.  You
  can write `set -o errexit || true`, but not `{ set -o errexit; false } ||
  true`.  When this option is set, you get a runtime error indicating that you
  should **change your code**.  Consider using the ["at-splice
  pattern"][at-splice] to fix this, e.g. `$0 myfunc || echo errexit`.
- `more_errexit`: Check more often for non-zero status.  In particular, the
  failure of a command sub can abort the entire script.  For example, `local
  foo=$(false)` is a fatal runtime error rather than a silent success.

### Example

When both `inherit_errexit` and `more_errexit` are on, this code

    echo 0; echo $(touch one; false; touch two); echo 3

will print `0` and touch the file `one`.

1. The command sub aborts at `false` (`inherrit_errexit), and
2. The parent process aborts after the command sub fails (`more_errexit`).

### Recap/Summary

- `errexit` -- abort the shell script when a command exits nonzero, except in
  the three situations described above.
- `inherit_errexit` -- A bash option that OSH borrows.
- `strict_errexit` -- Turned on with `strict:all`.
- `more_errexit` -- Turned on with `oil:all`.

Good articles on `errexit`:

- <http://mywiki.wooledge.org/BashFAQ/105>
- <http://fvue.nl/wiki/Bash:_Error_handling>

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

## Completion API

The completion API is modeled after the [bash completion
API](https://www.gnu.org/software/bash/manual/html_node/Command-Line-Editing.html#Command-Line-Editing)

However, an incompatibility is that it deals with `argv` entries and not
command strings.

OSH moves the **responsibility for quoting** into the shell.  Completion
plugins should not do it.

- TODO: describe the `compadjust` builtin.  Derived from a cleanup of the
  `bash-completion` project.

## Exit Codes

- `0` for **success**.
- `1` for **runtime errors**.  Examples:
  - `echo foo > out.txt` and `out.txt` can't be opened.
  - `fg` and there's not job to put in the foreground.
- `2` for **parse errors**.  This means that we didn't *attempt* to do
  anything, rather than doing something and it failing.  Examples:
  - A language parse error, like `echo $(`.
  - Builtin usage error, like `read -z`.
- `0` for **true**, and `1` for **false**.  Example:
  - `test -f foo` and `foo` isn't a file.
- POSIX exit codes:
  - `126` for permission denied when running a command (`errno EACCES`)
  - `127` for command not found

## Unicode

### Program Encoding

Shell **programs** should be encoded in UTF-8 (or its ASCII subset).  Unicode
characters can be encoded directly in the source:

<pre>
echo '&#x03bc;'
</pre>

or denoted in ASCII with C-escaped strings, i.e.  `$''`:

    echo $'[\u03bc]'

(This construct is preferred over `echo -e` because it's statically parsed.)

### Data Encoding

Strings in OSH are arbitrary sequences of **bytes**.  Caveats:

- When passed to external programs, strings are truncated at the first `NUL`
  (`'\0'`) byte.  This is just how Unix and C work.
- The length operator `${#s}` and slicing `${s:1:3}` require their input to be
  **valid UTF-8**.  Decoding errors are fatal if `shopt -s strict-word-eval` is
  on.

The GNU `iconv` program converts text from one encoding to another.

Also see [Notes on Unicode in Shell][unicode.md].

[unicode.md]: https://github.com/oilshell/oil/blob/master/doc/unicode.md

## Bugs

- OSH runs shell scripts too slowly.  Speeding it up is a top priority.

## Links

- [Blog Posts Tagged #FAQ](http://www.oilshell.org/blog/tags.html?tag=FAQ#FAQ)
  tell you why OSH exists and how it's designed.
- [Known Differences](known-differences.html) lists incompatibilities between
  OSH and other shells.  They are unlikely to appear in real programs, or
  there is a trivial workaround.

External:

- [GNU Bash Manual](https://www.gnu.org/software/bash/manual/).  I frequently
  referred to this document when implementing OSH.
- [BashGuide][].  A wiki with detailed information about bash.
  - [BashPitfalls](https://mywiki.wooledge.org/BashPitfalls).
- [Bash Cheat Sheet](https://devhints.io/bash).  A short overview.

[BashGuide]: https://mywiki.wooledge.org/BashGuide

[at-splice]: TODO


