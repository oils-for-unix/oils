---
default_highlighter: oils-sh
---

BYO - Protocols for Test Discovery, Shell Completion
===========

BYO is a simple mechanism to turn CLI processes into "servers" which respond to
requests encoded in environment variables.

Points of reference:

- [Test Anything Protocol][TAP]
  - e.g. Perl scripts parse stdout of test processes in any language
- [Shellac Protocol Proposal V2]($wiki) (wiki, 2019)

(About the name: It originally stood for Bash YSH OSH.  But "bring your own" is
a good acronym!)

[TAP]: https://testanything.org/

<div id="toc">
</div> 

## The General Idea

Executables should respond to the `BYO_COMMAND` environment variable:

    BYO_COMMAND=foo

And `BYO_ARG=bar` varies based on the command.

A library that implements this is:

    source $LIB_OSH/byo-server.sh

But it's designed to be implemented in Python, C++, etc.

A client is:

    test/byo-client.sh detect myscript.sh


## Protocol

### Detecting BYO Servers

Here's how you detect if an executable supports BYO:

    $ BYO_COMMAND=detect ./any-executable </dev/null
    list-tests
    run-tests

    # must exit with code 66, which is ASCII 'B'

### Testing - discover and run

List tests first:

    BYO_COMMAND=list-tests   

Then run them one at a time:

    BYO_COMMAND=run-test
    BYO_ARG=foo

### Shell completion - use these primitives

TODO:

    BYO_COMMAND=list-tasks  # related to task-five
    BYO_COMMAND=list-flags  # only some binaries have flags

<!--
Note: Look at Clang and npm completion?
-->

## Client Tool

The tool should work like this:

    $ byo detect myscript.sh
    $ byo test myscript.sh

(Right now it's [test/byo-client.sh]($oils-src))

## Appendix: Future Work

### Other Applications

- Benchmarking with TSV output
- Building tests first, with Ninja
- Deployment

Runtime:

- Gateway Interface / Coprocess
  - like FastCGI / CGI
- Logs

Points of reference:

- 12 factor app for Hosting (Heroku)
- CGI / FastCGI

### Coprocesses

Instead of a fresh process env variables, we might want to detect coprocesses.

