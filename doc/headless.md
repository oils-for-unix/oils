---
default_highlighter: oil-sh
---

Oil's Headless Mode: For Alternative UIs
========================================

Oil's *headless mode* is a unique feature that other shells don't have.  A GUI
or TUI process can start it like:

    osh --headless

and send messages to it over a Unix domain socket.  This way the language and
shell state are **decoupled** from the user interface.

<div id="toc">
</div>

TODO: Add details

## Background

TODO: Explain GNU readline

Shells are two things



## Implementation: The FANOS Protocol

- See `native/fanos.c` and `client/py_fanos.py`.

## Notes

### No history Expansion

## Related Links

- Wiki: We want there to be a rich ecosystem of interactive shells built upon
  Oil!  Edit these pages!
- Interactive Shell wiki.  With screenshots.  
