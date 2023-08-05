FAQ on Documentation
====================

Start here if you can't find something!

<div id="toc">
</div>

## How are the docs organized?

While we write the documentation, there are two different starting points:

1. [/release/$VERSION/](../index.html) lists the docs that are ready to read,
   right below the downloads.
1. [/release/$VERSION/doc/](index.html) is a tour through all docs, some of
   which are in progress.
1. [/release/$VERSION/doc/ref/](ref/index.html) is the Oils reference.

It has two indexes:

- [Index of OSH Topics](ref/index-osh.html)
- [Index of YSH Topics](ref/index-ysh.html)


There are various design docs, like:

- [Simple Word Evaluation in Unix Shell](simple-word-eval.html)
- [Oil Fixes Shell's Error Handling](error-handling.html)

Outside of [/release/$VERSION/](../index.html):

- [The blog](https://www.oilshell.org/blog/) has useful background information,
  although older posts are more likely to have incorrect information.
- [The home page](https://www.oilshell.org/) has links to docs for new users.

## Where do I find ...

### A list of all shell builtins?

See the [Chapter on Builtin Commands](ref/chap-builtin-cmd.html) in the reference.

### A list of all YSH functions?

See the [Chapter on Builtin Functions](ref/chap-builtin-func.html) in the reference.

### A list of all operators?

They are split between the "sublanguages" of OSH and YSH:

- [Expression Language](ref/chap-expr-lang.html) for the YSH expression
  language
- [Word Language](ref/chap-word-lang.html) for `${x}` and so forth
- [Mini Languages](ref/chap-mini-lang.html) for other shell sublanguages.

## I still can't find what I'm looking for.

Please send feedback on Github or Zulip: [Where To Send
Feedback](https://github.com/oilshell/oil/wiki/Where-To-Send-Feedback).
