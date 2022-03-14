---
in_progress: yes
---

What is Oil?
============

Oil is an interactive shell and programming language.  It's **our upgrade path
from bash**.

The language is designed to be easier to learn, more consistent, and more
powerful.

It runs existing shell scripts, but also borrows features from Python,
JavaScript, Ruby, and Perl.  It has rich data structures, declarative DSLs, and
reflection/metaprogramming features.

The rest of this doc gives various

<div id="toc">
</div> 

## It Runs Your Existing Shell Scripts

## It's a New Language, which mostly borrows from other languages


## Examples For the Impatient

This post is long, so here are some concrete examples.

An important part of Oil is that existing shell code runs!  These examples from
[Pipelines Support Vectorized, Point-Free, and Imperative
Style][pipelines-post] still run.

[pipelines-post]: ../../2017/01/15.html

--> syntax sh
hist() {
}
f() {
  hist
}
<--

That illustrates some of the good parts of shell.  The bad parts still run as well!

However, Oil is a brand new language.  Due to some tricks I practiced while
#[parsing-shell][], like lexer modes, very few compromises had to be made.

- Linux kernel?
- rsync command line?
- Brendan Gregg shell tools?  Show off awk and make?


TODO: function for fib, and then write it to a different directory?
  or maybe look up something in /usr/share/dict/words

  use it as a seven letter scrabble rack?

Fibonacci

    func fib(n) {
      var a = 0
      var b = 1
      for (_ in range(n)) {
        set a, b = b, a+b
      }
      return b
    }

    proc fib {
      var n = $1
      var a = 0
      var b = 1
      for _ in @split($(seq n)) {
        set a, b = b, a+b
      }
      return b
    }

Shell Script

    shopt -s all:oil

    # something with a pipeline
    find . -

    proc main {
    }

### What Should It Be Used For?

- System Administration / Distributed Systems / Cloud / Containers
  - Particularly glueing together build systems and package managers in
    different languages.  It's a "meta" tool.
- Scientific Computing / Data Science / "Data Engineering"  -- gluing things
  together that weren't meant to be glued together


## Oil Compared to Other Shells

- link nushell comment from reddit

## Links To Older Descriptions

- The [design notes in the last post](22.html), in particular the array
  rewrites on Zulip.
- Posts tagged #[oil-language][]
  - Particularly two posts on [Translating Shell to Oil][osh-to-oil].  (As
    noted in the last post, the project is no longer focused on translation.)
  - arrays I did sigils
- [2019 FAQ][faq-what-happened]
- Implementing the Oil Expression language (wkki)
- why-a-new-shell ?

[faq-what-happened]: ../06/17.html#toc_5

==> md-blog-tag oil-language
==> md-blog-tag osh-to-oil


Zulip: Oil as a clean slate ?

## `bin/oil` is `bin/osh` with the option group `all:oil`

Everything described here is part of the `osh` binary.  In other words, the Oil
language is implemented with a set of backward-compatible extensions, often
using shell options that are toggled with the `shopt` builtin.

## More Links

- [Why Create a New Unix Shell?](/blog/2018/01/28.html) describes the
  motivation for the Oil project.
- [2019 FAQ](/blog/2018/01/28.html)

