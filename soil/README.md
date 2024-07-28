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

## Tokens / Authentication

- `SOIL_GITHUB_API_TOKEN` - used by `maybe-merge` task, to use Github API to fast forward
  - appears in `.github/workflows/all-builds.yml` for **only** the `maybe-merge` task
- `OILS_GITHUB_KEY` - used by all tasks to publish HTML
  - - should really be called `OILS_SSH_FROM_GITHUB_ACTIONS`

## Code

Running a job starts at either:

- `.github/workflows/all-builds.yml` for Github Actions
- `.builds/worker{1,2,3,4}.yml` for sourcehut

The YAML files either:

- Directly invoke `soil/worker.sh` for a raw VM job.
- Invoke wrappers `soil/github-actions.sh` / `soil/sourcehut.sh`, which in turn
  uses `soil/host-shim.sh` to run a job in a container.
  - They wrappers also publish via SSH with `soil/web-worker.sh`

`soil/host-shim.sh` pulls and start an OCI container each node, and then runs
`soil/worker.sh` inside the container.

`soil/worker.sh` runs the job, and publishes 3 files to `travis-ci.oilshell.org`:

1. JSON metadata about the commit and build environment
1. TSV metadata for each "toil" step
1. A `.wwz` file (servable zip file) of logs

`soil/web.sh` is a wrapper around `soil/web.py`, and it runs on the SERVER 
(`travis-ci.oilshell.org`).  It reads and joins metadata from every job to
construct `index.html` and `$RUN_NUMBER/index.html`.

The server-side components are deployed by `soil/web-init.sh`.

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
      - this is based on github-jobs/$RUN/*.tsv -- similar to format-wwz-index
      - or srht-jobs/*/*.tsv and filtered by commit
    - github-jobs/tmp-$$.remove.txt - shell script does rm
  - status-api/github-jobs/$RUN/$job -- PUT this

- Start job.  TODO: This doesn't exist.
  - github-jobs/index.html should show Started / Pass / Fail

## Web Interface / Security

This one is a pure uploader, which you can borrow from picdir.

    POST https://test.oils-for-unix.org/results
      ?jobName=dev-minimal
      &workerHost=github

It does multi-part file upload of wwz, TSV, JSON, and saves the files.  Start
with basic auth over HTTPS?  See picdir.


    POST https://test.oils-for-unix.org/event

      ?eventName=start
      &workerHost=github
      &runId=1234
      &jobName=dev-minimal

      ?eventName=start
      &workerHost=sourcehut
      &jobId=345
      &jobName=dev-minimal

      # whether to update the status-api
      ?eventName=done
      &workerHost=github
      &runId=1234
      &jobName=dev-minimal
      &status=124
      &updateStatusApi=1

This PHP script can just run a shell script synchronously?  Events start and
done are meant to be quick.

Other events:

- begin pulling container
- done pulling container
- done with task, although we want to get rid of this abstraction


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



