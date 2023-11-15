---
default_highlighter: oils-sh
---

Oils Headless Mode: For Alternative UIs
=======================================

A GUI or [TUI][] process can start Oils like this:

    osh --headless

and send messages to it over a Unix domain socket.  In this mode, the language
and shell state are **decoupled** from the user interface.

This is a unique feature that other shells don't have!

[TUI]: https://en.wikipedia.org/wiki/Text-based_user_interface

Note: This doc is **in progress**.  Join the `#shell-gui` channel on
[Zulip]($xref:zulip) for current information.

<div id="toc">
</div>

## The General Idea

The UI process should handle these things:

- Auto-completion.  It should use Oils for parsing, and not try to parse shell
  itself!
- History: Allow the user to retrieve commands typed in the past.
- Cancelling commands in progress.
- Optional: multiplexing among multiple headless shells.

The shell process handles these things:

- Parsing and evaluating the language
- Maintaining state (shell options, variables, etc.)

## How to Write a Client for a Headless Shell

### Implement the FANOS Protocol

FANOS stands for *File descriptors and Netstrings Over Sockets*.  It's a
**control** protocol that already has 2 implementations, which are very small:

- [client/py_fanos.py]($oils-src): 102 lines of code
- [native/fanos.c]($oils-src): 294 lines of code

### Send Commands and File Descriptors to the "Server"

List of commands:

- `EVAL`.  Parse and evaluate a shell command.  The logic is similar to the
  `eval` and `source` builtins.
  - It can be used for both user-entered commands and "behind the scenes"
    functions for the shell UI.
  - The stdin, stdout, and stderr of **the shell and its child processes** will
    be redirected to the descriptors you pass.
  - There's no history expansion for now.  The UI can implement this itself,
    and Oils may be able to help.

TODO: More commands.

### Query Shell State and Render it in the UI

You may want to use commands like these to draw the UI:

- `echo ${PS1@P}` -- render the prompt
- `echo $PWD $_` -- get the current directory and current status

You can redirect them to a pipe, rather than displaying them in the terminal.

Remember that a fundamental difference between a REPL and a GUI is that a GUI
**shows state** explicitly.  This is a good thing and you should take advantage
of it!

### Example Code

See [client/headless_demo.py]($oils-src).  This is pure Python code that's
divorced from the rest of Oils.

## Related Links

Feel free to edit these pages:

- [Headless Mode][] on the wiki.  We want there to be a rich ecosystem of
  interactive shells built upon Oils.
- [Interactive Shell][] on the wiki.  Be inspired by these nice projects, many
  of which have screenshots! 

[Headless Mode]: https://github.com/oilshell/oil/wiki/Headless-Mode

[Interactive Shell]: https://github.com/oilshell/oil/wiki/Interactive-Shell
