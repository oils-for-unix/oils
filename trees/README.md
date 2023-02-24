trees: Sketch of Storage / Networking Architecture
==================================================

As usual, we try not to invent anything big or new, but instead focus on
composing and rationalizing existing software and protocols:

- Many good implementation of POSIX file systems (Linux ext4, ZFS, etc.)
- git, a distributed version control system
  - in particular the packfile format
  - the ssh send/receive pattern
- Static WWW file servers like Apache and nginx
- tar files, gzip files

## Initial Use Cases

1. Building CI containers faster, with
   - native deps: re2c, bloaty, uftrace, ...
   - Python deps, e.g. MyPy
   - R deps, e.g. dplyr
   - The total size should also be smaller.
2. Running benchmarks on multiple machines
   - `oils-for-unix` tarball from EVERY commit, sync'd to different CI tasks
3. Comparisons across distros and Unixes
   - building same packages on Debian, Ubuntu, Alpine
   - and FreeBSD

## vat: The Value Tree

### Data

    https://oilshell.org/
      deps.vat/
        primary/            # everything is a blob at first
          00/               # checksums calculated with git hash-object
            123456.blob.gz  # may be a .tar file, but vat doesn't know
        cache/    # may contain detlas
          00/
            123456.blob.xz

### Commands

    vat verify  # blobs should have valid checksums

Existing tools:

    rsync        # back up the entire thing
    rclone       # ditto, but works with clod storage

    ssh rm "$@"  # a list of vrefs to delete can be calculated by 'shrub is-live'
    scp          # create a new vat from 'shrub is-live' manifest

## shrub: Named and Versioned Subtrees in `git`

### Data

    ~/git/oilshell/oil/    
      deps.shrub/
        VAT.json                  # points to multiple Vats
        source/
          Python-3.10.4.vref      # vref with checksum and provenance (original URL)

          images/
            debian/
              bullseye-base.vref  # 'docker save' format

        derived/
          ubuntu/
            20.04/
              Python-3.10.4.vref  # derived data has provenance:
                                  # base layer, mounts of input / code, env / shell command
            22.04/
              Python-3.10.4.vref

### Commands

    shrub sync deps.shrub/ /wedge/oilshell.org/deps     # materialize files
                                                        # should it run as root?

    shrub verify deps.shrub/ /wedge/oilshell.org/deps  # checksum files

    # Makes a vref and tarball that you can scp/rsync
    shrub add-dir /wedge/oilshell.org/bash-4.4/ deps.shrub/ubuntu/18.04/bash-4.4.vref 

    shrub reachable deps.shrub/  # first step of garbage collection

    shrub mount  # much later: FUSE mount

## /wedge: A subtree that works well with OCI containers

- It can be mounted, e.g. `--mount type=bind,...`
- It can be copied into an image: `COPY ...`
- It has provenance, like other vrefs.  Either:
  - the original URL
  - the code, data, and environment used to build it

## Data and Metadata Formats

Text:

- lockfile / "world" / manifest
- JSON for .vref and VAT.json

Data:

- Compression: `.gz`, `bzip2`, etc.
- Archiving: `.tar`, `git` packfile, ...
  - OCI layers use `.tar`
- Encryption (well LUKS does the whole system)

## TODO Later

- Analog for high level `docker run`, `podman run`
- Analog for low level `runc`, `crun`
- The equivalent of inotify() on a Vat / Shrub.
  - could be an REST API on `oils-tarballs.shrub/events/` 
  - it tells you what Vat to fetch from

## Ideas / Slogans

- "Distributed OS without RPCs".  Instead, with state synchronization.
