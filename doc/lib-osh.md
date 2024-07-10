---
default_highlighter: oils-sh
---

OSH Standard Library - Based on Years of Experience
===========

## Intro

### Example of Task File


## List of Libraries

### bash-strict

Saves you some boilerplate.

### two

### no-quotes

### byo-server

- Test discovery
- Probably:
  - task discovery 
  - auto-completion

### task-five

Task files

## Appendix

### Why no standard way to set `$REPO_ROOT`?

repo-root is left off because different people use different variants:

    pwd -P
    readlink -f $0

There is not one way to do it when symlinks are involved.  And most of our
scripts must be run from root, and aren't symlinked.
