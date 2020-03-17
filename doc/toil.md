---
in_progress: yes
---

Toil: Continuous Testing on Many Platforms
===========================================


Listening to `oilshell/oil`:

- `dev-minimal`
  - Can a contributor quickly get started with the Oil repo?
  - They just want to run bin/osh without installing much
- `ovm-tarball`
- TODO: `dev-all`
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

## Code

- `services/toil-worker.sh` runs on each build service node.  For each job, it
  publishes a few files to `travis-ci.oilshell.org`:
  - JSON metadata about the commit and build environment
  - TSV metadata for each "toil" step
  - A `.wwz` file (servable zip file) of logs
- `services/toil_web.py` runs on `travis-ci.oilshell.org` and reads the
  metadata from every job to construct an `index.html`.

