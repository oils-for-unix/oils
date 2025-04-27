Oils Source Code
================

[![Build
Status](https://github.com/oils-for-unix/oils/actions/workflows/all-builds.yml/badge.svg?branch=master)](https://github.com/oils-for-unix/oils/actions/workflows/all-builds.yml) <a href="https://gitpod.io/from-referrer/">
  <img src="https://img.shields.io/badge/Contribute%20with-Gitpod-908a85?logo=gitpod" alt="Contribute with Gitpod" />
</a>

[Oils][home-page] is our upgrade path from bash to a better language and runtime!  

- [OSH][] runs your existing shell scripts.
- [YSH][] is for Python and JavaScript users who avoid shell.

(The project was [slightly renamed][rename] in March 2023, so there are still
old references to "Oil".  Feel free to send pull requests with corrections!)

[home-page]: https://oils.pub/

[OSH]: https://oils.pub/cross-ref.html#OSH
[YSH]: https://oils.pub/cross-ref.html#YSH

[rename]: https://www.oilshell.org/blog/2023/03/rename.html

[Oils 2023 FAQ][faq-2023] / [Why Create a New Unix Shell?][why]

[faq-2023]: https://www.oilshell.org/blog/2023/03/faq.html
[why]: https://www.oilshell.org/blog/2021/01/why-a-new-shell.html

It's written in Python, so the code is short and easy to change.  But we
automatically translate it to C++ with custom tools, to make it fast and small.
The deployed executable doesn't depend on Python.

This README is at the root of the [git repo][git-repo].

If you want to **use** Oils, don't clone this repo.  Instead, visit
<https://oils.pub/release/latest/>.
[The Oils Repo Is Different From theTarball Releases](https://github.com/oils-for-unix/oils/wiki/The-Oils-Repo-Is-Different-From-the-Tarball-Releases).

[git-repo]: https://github.com/oils-for-unix/oils

<div id="toc">
</div>

## Contributing

* Try making the **dev build** of Oils with the instructions on the
  [Contributing][] page.  This should take 1 to 5 minutes if you have a Linux
  machine.
* If it doesn't, let us know.  You can post on the `#oil-dev` channel of
  [oilshell.zulipchat.com][], or file an issue on Github.
* Feel free to grab an [issue from
  Github](https://github.com/oils-for-unix/oils/issues?q=is%3Aissue+is%3Aopen+label%3A%22good+first+issue%22).
  Let us know what you're thinking before you get too far.

[Contributing]: https://github.com/oils-for-unix/oils/wiki/Contributing
[oilshell.zulipchat.com]: https://oilshell.zulipchat.com/
[blog]: https://oils.pub/blog/

### Quick Start on Linux

After following the instructions on the [Contributing][] page, you'll have a
Python program that you can quickly run and change!  Try it interactively:

    bash$ bin/osh

    osh$ name=world
    osh$ echo "hello $name"
    hello world

- Try running a shell script you wrote with `bin/osh myscript.sh`.
- Try [YSH][] with `bin/ysh`.

Let us know if any of these things don't work!  [The continuous
build](https://op.oilshell.org/) tests them at every commit.

### Dev Build vs. Release Build

Again, note that the **developer build** is **very different** from the release
tarball.  The [Contributing][] page describes this difference in detail.

The release tarballs are linked from the [home page][home-page].  (Developer
builds don't work on OS X, so use the release tarballs on OS X.)

### Important: We Accept Small Contributions!

Oils is full of [many ideas](https://oils.pub/blog/), which may be
intimidating at first.

But the bar to contribution is very low.  It's basically a medium size Python
program with many tests, and many programmers know how to change such programs.
It's great for prototyping.

- For OSH compatibility, I often merge **failing [spec
  tests](https://oils.pub/cross-ref.html#spec-test)**.  You don't even
  have to write code!  The tests alone help.  I search for related tests with
  `grep xtrace spec/*.test.sh`, where `xtrace` is a shell feature.
- You only have to make your code work **in Python**.  Plain Python programs
  are easy to modify.  The semi-automated translation to C++ is a separate
  step, although it often just works. 
- You can **influence the design** of [YSH][].  If you have an itch to
  scratch, be ambitious.  For example, you might want to show us how to
  implement [nonlinear pipelines](https://github.com/oils-for-unix/oils/issues/843).

### I aim for 24 hour response time

Please feel free to ping `andychu` on Zulip or Github if you're **waiting** for
a pull request review!  (or to ask questions)

Usually I can respond in 24 hours. I might be traveling, in which case I'll
respond with something like *I hope to look at this by Tuesday*.

I might have also **missed** your Github message, so it doesn't hurt to ping
me.

Thank you for the contributions!

## Docs

The [Wiki](https://github.com/oils-for-unix/oils/wiki) has many developer docs.  Feel
free to edit them.  If you make a major change, let us know on Zulip!

If you're confused, the best thing to do is to ask on Zulip and someone should
produce a pointer and/or improve the docs.

Docs for **end users** are linked from each [release
page](https://oils.pub/releases.html).

## Links

* The [Oils Home Page][home-page] has all the important links.
* Related:
  * Repository Structure: See the [Oils Repo Overview][repo-overview]
  * The [README-index.md](README-index.md) links to docs for some
    subdirectories.  For example, [mycpp/README.md](mycpp/README.md) is pretty
    detailed.
  * FAQ: [The Oils Repo Is Different From the Tarball][repo-tarball-faq]

[repo-overview]: doc/repo-overview.md

[repo-tarball-faq]: https://github.com/oils-for-unix/oils/wiki/The-Oils-Repo-Is-Different-From-the-Tarball-Releases
