Benchmarks
==========

The benchmarks in this directory can run:

- on one machine, during in the Soil continuous build
- on two machines, during the release

The directory structure is different in each case.

## Dirs for One Machine

```
_tmp/osh-runtime/
  files.html
  index.html
  raw/  # TODO: should be raw.no-host.*
    gc-6.txt
    gc-7.txt
    no-host.2022-12-29__00-33-00.files/
      files-0/
        STDOUT.txt
      files-1/
       STDOUT.txt
        ...
    no-host.2022-12-29__00-33-00.times.tsv
  stage1/
    gc_stats.tsv
    provenance.tsv
    times.tsv
  stage2/
    details.schema.tsv
    details.tsv
    elapsed.schema.tsv
    elapsed.tsv

_tmp/provenance/
  no-host.2022-12-29__00-33-00.provenance.tsv
  no-host.2022-12-29__00-33-00.provenance.txt
  host-id/
    no-host-3063f657/
      cpuinfo.txt
      HASH.txt
      ...
  shell-id/
    bash-9af8f89f/
      HASH.txt
      index.html
      version.txt
    dash-9ff48631/
      dpkg-version.txt
      HASH.txt
       index.html
    osh-0d29d4d3
      git-branch.txt
      ...
```
 

## Dirs for Two Machines

```
../benchmark-data/
  osh-runtime/
    no-host.2022-12-29__00-33-00.provenance.tsv
    no-host.2022-12-29__00-33-00.provenance.txt
    no-host.2022-12-29__00-33-00.times.tsv
    no-host.2022-12-29__00-33-00.files/
  osh-parser/
    ...
   
  shell-id/
  host-id/

```

TODO:

```
../benchmark-data/
  osh-runtime/
    raw.no-host.2022-12-29__00-33-00/
      provenance.tsv  # raw
      times.tsv  # raw
      gc_stats.tsv  # collected
      files/  # raw

    raw.no-host.2022-12-30__00-00-00/

  osh-parser/
    ...

  shell-id/
  host-id/
```

Philosophy to aim for:

- We save the raw/ data in git.
- The derived stage1/ stage2/ dirs are stored in the .wwz file on the web
  server.
  - See `devtools/release.sh compress-benchmarks`

