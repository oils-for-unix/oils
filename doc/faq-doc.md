FAQ on Documentation
====================

Start here if you can't find something!

<div id="toc">
</div>

## How are the docs organized?

Every release is published at [/release/$VERSION/](../index.html).  As of 2024,
it links to 2 starting points:

1. [**Published Docs**](published.html) shows docs that are ready to read.
   Examples:
   - [Simple Word Evaluation in Unix Shell](simple-word-eval.html)
   - [YSH Fixes Shell's Error Handling](error-handling.html)
1. [**All Docs**](index.html) shows all docs.

The **Oils Reference** at [/release/$VERSION/doc/ref/](ref/index.html) is still
in progress.

Outside of the release tree:

- [The blog](https://www.oilshell.org/blog/) has useful background info.  Older
  posts are more likely to have incorrect information.
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
