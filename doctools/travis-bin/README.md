Why Check In libcmark.so ?
==========================

See this commit:

```
commit 3ce6e2974a9c2e4d894c67e86499059624c4fdd4
Author: Andy Chu <andy@oilshell.org>
Date:   Sun Dec 29 22:56:43 2019 -0800

    [travis] Check in libcmark.so to make the build work.

    To run bin/osh, we need the help builtin to work.

    The help builtin needs help text.

    The help text is rendered from __ HTML __.  So we can have the web text
    match the shell text.

    HTML is rendered by doctools/cmark.py, which uses libcmark.so.
```


