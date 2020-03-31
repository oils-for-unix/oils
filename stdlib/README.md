stdlib/
=======

Ideas for shell functions that could be in here:

- Version comparison: https://github.com/oilshell/oil/issues/683
- An automated way to download the latest version of Oil: https://github.com/oilshell/oil/issues/463
  - Maybe functions to lazily download documentation too?
- `errexit` utilities: https://github.com/oilshell/oil/issues/474

Already have:

- `log` and `die`

Note: The file `oil-polyfill.sh` is POSIX shell for functions that should be
portable, e.g. like updating Oil, which may be done from the system shell.

Other functions can be written in Oil.

