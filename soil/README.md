Soil
====

Continuous testing on many platforms.

## Server Setup

    soil/web-init.sh deploy  # deploy static assets and tools

## Data

    https://test.oils-for-unix.org/  # not Soil, Coil could be a better name

      static-api/  # used by the maybe-merge task
        github/
          1234/  GITHUB_RUN_ID (or NUMBER)
            dev-minimal  # file with status 0
            cpp-small

      github-jobs/
        index.html  # pretty list of runs, links to commits/ and foo.wwz/index
        raw.html  # flat
        1234/  # GITHUB_RUN_NUMBER
          dev-minimal.wwz/
            index.html  # worker runs format-wwz-index for TSV -> HTML
          dev-minimal.{tsv,json}
          cpp-small.wwz/
            index.html
          cpp-small.{tsv,json}
        commits/

      srht-jobs/
        index.html
        raw.html
        345/  # JOB_ID
          dev-minimal.wwz/
            index.html
          dev-minimal.{tsv,json}
        344/
          cpp-small.wwz/
            index.html
          cpp-small.{tsv,json}
        commits/   # index grouped by commit?
          09ab09ab.html  # links to ../345/dev-minimal.wwz/
          1010abab.html

## Code

- `soil/worker.sh` runs on each build service node.  For each job, it
  publishes 3 files to `travis-ci.oilshell.org`:
  - JSON metadata about the commit and build environment
  - TSV metadata for each "toil" step
  - A `.wwz` file (servable zip file) of logs
- `soil/web.py` runs on `travis-ci.oilshell.org` and reads the metadata from
  every job to construct an `index.html`.


## Terminology

Three level hierarchy of executables:

- Run - A group of jobs run per commit, usually on different machines.
  Github has `GITHUB_RUN_{NUMBER,ID}`, but sourcehut lacks this concept.
- Job - A group of tasks run on the same machine, in the same container, or on a raw VM.
- Task - A shell command that's run within the Oil repo.  Tasks are currently
  run sequentially.

TODO:

- Tasks need explicit dependencies
- Dynamically schedule tasks, and remove the idea of a job.  It should just be
  a flat list of tasks run per commit, on various machines, with
  dynamically-scheduled and resolved dependencies.

## Events

- End Job.
  - First upload wwz, tsv, and JSON last
  - web.py can rewrites the following files in one pass, based on list-json
    state
    - github-jobs/tmp-$$.{index,raw}.html - shell script does mv
    - github-jobs/commits/tmp-$$.$HASH.html - shell script does mv
    - github-jobs/tmp-$$.remove.txt - shell script does rm
  - status-api/github-jobs/$RUN/$job -- PUT this

- Start job.  TODO: This doesn't exist.
  - github-jobs/index.html should show Started / Pass / Fail

## Notes

### Idea For Tuple Space?

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

It would nice to implement this as SQL.



