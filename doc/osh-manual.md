OSH Reference Manual
--------------------

NOTE: This document is in progress.

### Setup

After running the instructions in `INSTALL.txt` (web version linked from
[releases.html](https://www.oilshell.org/releases.html)), run:

    mkdir -p ~/.config/oil

- An `osh_history` file will be created there to store you history.
- You can create your own `oshrc` there.

### Startup Files

On startup, the interactive shell sources **only** `~/.config/oil/oshrc`.  Oil
intends to avoid [this kind of mess][mess] ([original][]).

With most shells, it's very hard to tell when and if `/etc/profile`,
`~/.bashrc`, `~/.bash_profile`, etc. are executed.  (TODO: OSH could use some
tracing features to help users untangle this rat's nest.)

If you want those files, simply add `source <FILE>` to your `oshrc`.

For example, `$LANG` may not get set without `/etc/profile` (e.g. on Arch
Linux).  So you can add `source /etc/profile` to your `oshrc`.

Similarly, if you get tired of typing `~/.config/oil/oshrc`, symlink it to
`~/.oshrc`.

[mess]: https://shreevatsa.wordpress.com/2008/03/30/zshbash-startup-files-loading-order-bashrc-zshrc-etc/

[original]: http://www.solipsys.co.uk/new/BashInitialisationFiles.html

I describe my own `oshrc` file on the wiki: [How To Test
OSH](https://github.com/oilshell/oil/wiki/How-To-Test-OSH).


### Unicode

Encoding of programs should be utf-8.

As an alternative, ASCII can be used like this:

    echo $'[\u03bc]'  # C-escaped string

- `$''` is preferred over `echo -e` because it's statically parsed.

List of operations that are Unicode-aware:

- ${#s} -- number of characters in a string
  - TOOD: provide an option to change this
- slice: ${s:0:1}
- any operations that uses glob, which has '.' and [[:alpha:]] expressions
  - case
  - [[ $x == . ]]
  - ${s/./x}
  - ${s#.}  # remove one character
- sorting [[ $a < $b ]] -- should use current locale?  I guess that is like the
  'sort' command.
- prompt string has time, which is locale-specific.


### Exit Codes

- `1` for runtime errors.  Examples:
  - `echo foo > out.txt` and the file can't be opened
- `2` for parse errors.  This means that we didn't even *attempt* to do
  anything, rather than doing something and it failing.
  - shell language parse error
  - builtin usage error, e.g. `read -z`
- POSIX mentions these:
  - `126` for permission denied when running a command (`errno EACCES`)
  - `127` for command not found

### Completion API

One important incompatibility is that it deals with `argv` entries and not
command strings.

OSH moves the **responsibility for quoting** into the shell.  Completion
plugins should not do it.

- TODO: describe the `compadjust` builtin.  Derived from a cleanup of the
  `bash-completion` project.


### Additional Features in OSH

TODO:

- `OSH_HIJACK_SHEBANG`
- `OSH_CRASH_DUMP_DIR`
- `--debug-file`
- `--xtrace-to-debug-file`

#### Strict Options

- TODO: `strict-control-flow`, etc.

### Known Differences Between OSH and Other Shells

See [doc/known-differences.md][].

[doc/known-differences.md]: ./known-differences.md

