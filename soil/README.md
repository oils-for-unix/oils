Soil
====

Continuous testing on many platforms.

## Server Setup

    soil/web-init.sh deploy  # deploy static assets and tools

## Code

- `soil/worker.sh` runs on each build service node.  For each job, it
  publishes a few files to `travis-ci.oilshell.org`:
  - JSON metadata about the commit and build environment
  - TSV metadata for each "toil" step
  - A `.wwz` file (servable zip file) of logs
- `soil/web.py` runs on `travis-ci.oilshell.org` and reads the metadata from
  every job to construct an `index.html`.

## Notes

Listening to `oilshell/oil`:

- `dev-minimal`
  - Can a contributor quickly get started with the Oil repo?
  - They just want to run bin/osh without installing much
- `ovm-tarball`
- `cpp`
- `other-tests`

Listening to `oilshell/tarballs`:

- Travis
  - OS X (bin-darwin)
- Sourcehut
  - Alpine (bin-alpine)
  - OpenBSD (bin-openbsd)
  - Alternate architectures like ARM

All of these build both oil.ovm and oil-native.  Need maintainers.  We build
them as a "start".

