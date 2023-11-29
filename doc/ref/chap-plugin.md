---
in_progress: yes
body_css_class: width40 help-body
default_highlighter: oils-sh
---

Plugins and Hooks
===

This chapter in the [Oils Reference](index.html) describes extension points for
OSH and YSH

<div id="toc">
</div>


## Signals

## Traps

## Words

<h3 id="PS1">PS1</h3>

First line of a prompt.

<h3 id="PS2">PS2</h3>

Second line of a prompt.

<h3 id="PS3">PS3</h3>

For the 'select' builtin (unimplemented).

<h3 id="PS4">PS4</h3>

For 'set -o xtrace'.  The leading character is special.

## Completion

## Other Plugin

## YSH

### renderPrompt()

Users may define this func to customize their prompt.

The func should take the global `value.IO` instance, and return a prompt string
(type `value.Str`).

To construct the prompt, it can make calls like
[`io->promptVal('$')`]($chap-type-method:promptval).

To render the prompt, YSH first checks if this function exists.  Otherwise, it
uses [`$PS1`]($chap-plugin:PS1) with a `ysh` prefix.

<!-- note: doctools/cmark.py turns promptVal -> promptval -->


