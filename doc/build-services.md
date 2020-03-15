---
in_progress: yes
---

Notes on Build Services
=======================

Listening to `oilshell/oil`:

- `dev-minimal`
  - Can a contributor quickly get started with the Oil repo?
  - They just want to run bin/osh without installing much

- `dev-all`
  - run spec tests against `dev-all`
    - TODO: requires test/spec-bin.sh, which should be moved to `_deps/spec-bin`
  - build oil.ovm tarball
  - TODO: build oil-native tarball
    - requires MyPy
  - TODO: push metadata to https://github.com/oilshell/tarballs
    - you need a Github token for this
  - Content lives on http://travis-ci.oilshell.org/tarballs/

- `dev-all-nix`
  - nix environment
  - Run spec tests.  Can also run the release.

Listening to `oilshell/tarballs`:

- Travis
  - OS X (bin-darwin)
- Sourcehut
  - Alpine (bin-alpine)
  - OpenBSD (bin-openbsd)
  - Alternate architectures like ARM

All of these build both oil.ovm and oil-native.  Need maintainers.  We build
them as a "start".

