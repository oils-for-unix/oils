Documentation
=============

## HTML Docs

I build these with a wrapper around CommonMark.  Try:

    deps/from-tar.sh layer-cmark

And then:

    build/doc.sh all-markdown

The output HTML shows up in `_release/VERSION/doc`.

See [doc-toolchain.md]() for details.

## Man pages

`osh.1` is a [man page](https://en.wikipedia.org/wiki/Man_page) written using
the [mdoc](http://mandoc.bsd.lv/man/mdoc.7.html) macro language for the troff
(groff) formatter.

You can view it with `man doc/osh.1`. 

