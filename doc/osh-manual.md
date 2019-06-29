OSH User Manual
---------------

<p style="text-align: right">
  Version 0.6.0
  <!-- REPLACE_WITH_DATE -->
</p>


OSH is a POSIX- and bash-compatible Unix shell.

This document is in progress.

<!-- cmark.py expands this -->
<div id="toc">
</div>

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


### Strict Options

Strict options **disallow** certain parts of the language with **fatal runtime
errors**.

They are used like this:

    shopt -s strict-array  # Set this option.  I want more fatal errors.
    shopt -u strict-array  # Unset it.  Ignore errors and keep executing.

You can turn all of them on or off at once:

    shopt -s all:strict
    shopt -u all:strict

To use all strict modes in a script that must also run under other shells:

    shopt -s all:strict 2>/dev/null || true  # supress errors

**List of strict options**:

`strict-argv`.  Empty `argv` arrays are disallowed, since there's no practical
use for them.

- For example, the second statement in `x=''; $x` results in a fatal error.

`strict-array`. No implicit conversions between string an array.  That is, turn
this on if you want a "real" array type.  (NOTE: Only partially implemented.)

`strict-control-flow`. `break` and `continue` outside of a loop are fatal
errors.

`strict-errexit`.  The `errexit` setting also applies to command subs.

- For example, `echo 0; echo $(touch one; false; touch two); echo 3` will print
  `0` and touch the file `one`.  The whole script aborts at `false`, including
  the **parent process**.
- NOTE: This is even stricter than bash 4.4's `inherit_errexit`, which stops at
  `false` in the command sub, but keeps running the parent process.

`strict-word-eval`.  More word evaluation errors are fatal.  For example:

- String slices with negative arguments like `${s: -1}` and `${s: 1 : -1}`
  result in a fatal error.  (NOTE: In array slices, negative start indices are
  allowed, but negative lengths are always fatal, regardless of
  `strict-word-eval`.)
- UTF-8 decoding errors are fatal when computing lengths (`${#s}`) and slices.

**On by default**:

`strict-arith`.  Strings that don't look like integers cause a fatal error in
arithmetic expressions.  NOTE: This option may be removed if no scripts rely on
the old, bad behavior.


### Additional Features in OSH

TODO:

- `OSH_HIJACK_SHEBANG`
- `OSH_CRASH_DUMP_DIR`
- `--debug-file`
- `--xtrace-to-debug-file`

### Known Differences Between OSH and Other Shells

See the [Known Differences](known-differences.html) doc.

### Completion API

One important incompatibility is that it deals with `argv` entries and not
command strings.

OSH moves the **responsibility for quoting** into the shell.  Completion
plugins should not do it.

- TODO: describe the `compadjust` builtin.  Derived from a cleanup of the
  `bash-completion` project.

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

### Unicode

Shell programs should be encoded in UTF-8 (or its ASCII subset).

To express Unicode characters while not worrying about the encoding of the
program, use C-escaped strings, i.e. `$''`:

    echo $'[\u03bc]'

(This construct is preferred over `echo -e` because it's statically parsed.)

Also see [Notes on Unicode in Shell][unicode.md].

[unicode.md]: https://github.com/oilshell/oil/blob/master/doc/unicode.md

### Other Resources

TODO: Link to bash manual, etc.?

