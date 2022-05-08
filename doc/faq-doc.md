---
in_progress: yes
---

FAQ on Documentation
====================

Start here if you can't find something!

<div id="toc">
</div>

## How are the docs organized?

While we write the documentation, there are two different starting points:

1. [/release/$VERSION/](../index.html) lists the docs that are ready to read,
   right below the downloads.
2. [/release/$VERSION/doc/](index.html) is a tour through all docs, some of
   which are in progress.

There's also an incomplete reference, separated by compatible features and new
features:

- [OSH Help Topics](osh-help-topics.html) links to [OSH Help](osh-help.html) (big doc)
- [Oil Help Topics](oil-help-topics.html) links to [Oil Help](oil-help.html) (big doc)

And there are various design docs, like:

- [Simple Word Evaluation in Unix Shell](simple-word-eval.html)
- [Oil Fixes Shell's Error Handling](error-handling.html)

Outside of [/release/$VERSION/](../index.html):

- [The blog](https://www.oilshell.org/blog/) has useful background information,
  although older posts are more likely to have incorrect information.
- [The home page](https://www.oilshell.org/) has links to docs for new users.

## Where do I find ...

### A list of all shell builtins?

Right now it's split between the OSH and Oil references.

- [OSH Help Topics > builtins](osh-help-topics.html#builtins)
- [Oil Help Topics > builtins](oil-help-topics.html#builtins)

### A list of all Oil funcs?

- [Oil Help Topics > lib](oil-help-topics.html#lib).  This design is not yet
  done.

### A list of all operators?

They are split between the "sublanguages" of OSH and Oil:

- [Oil Help Topics > expr-lang](oil-help-topics.html#expr-lang) for the new Oil
  expression language
- [OSH Help Topics > word-lang](osh-help-topics.html#word-lang) for `${x}` and
  so forth
- [OSH Help Topics > sublang](osh-help-topics.html#sublang) for other shell
  sublanguages

## I still can't find what I'm looking for.

Please send feedback on Github or Zulip: [Where To Send
Feedback](https://github.com/oilshell/oil/wiki/Where-To-Send-Feedback).
