---
css_files: web/base.css web/release-index.css
all_docs_url: -
version_url: -
---

Oils 0.23.0
===========

<!-- NOTE: This file is published to /release/$VERSION/index.html -->

<span class="date">
<!-- REPLACE_WITH_DATE -->
</span>

This is the home page for version 0.23.0 of Oils, a Unix shell.  To use it,

1. Download a source tarball.
2. Build it and do a "smoke test", as described in [INSTALL][].

These steps take 30 to 60 seconds on most machines.  After installation, see
[Getting Started](doc/getting-started.html).

[INSTALL]: doc/INSTALL.html

## Download

<!-- REPLACE_WITH_DOWNLOAD_LINKS -->

The [Oils Deployments](https://github.com/oilshell/oil/wiki/Oils-Deployments)
wiki page has other ways of getting Oils.  These versions may not be
up-to-date.

## Documentation

- [Published Docs](doc/published.html) - these are ready to read
- [All Docs](doc/index.html) (in progress)
  - The [**Oils Reference**](doc/ref/index.html)
- [Github Wiki for oilshell/oil](https://github.com/oilshell/oil/wiki)

## Packaging

Summary of [Oils Packaging Guidelines]($wiki):

- The `oils-for-unix` tarball is the fast shell in C++, completed in
  2024.  The distro package should be called `oils-for-unix`.
- The `oil` tarball is the slow reference interpreter based on CPython.
  - Don't rename old distro packages.  They can remain `oil`.
  - It's not worth packaging `oil` in new distros.  It may be removed at some
    point.
- The project is now called **Oils**, or [Oils for
  Unix](https://www.oilshell.org/blog/2023/03/rename.html).  There is no more
  `oil`!

## What's New

- Details are in the [raw git change log](changelog.html).  Not all changes
  affect the release tarball.
- I sometimes write a [release announcement](announcement.html) with a
  high-level description of changes.

## Links

- The **[quality page](quality.html)** shows test results, metrics, and
  benchmarks.

