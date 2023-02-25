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
4. Maybe: serving `.wwz` files

## Silo: Large Trees Managed Outside Git

You can `git pull` and `git push` without paying for these large objects, e.g.
container images.

To start, trees use regular compression with `gzip`.  Later, it will introspect
trees and take **hints** for **differential** compression.

### Data

    https://oilshell.org/
      deps.silo/
        objects/            # everything is a blob at first
          00/               # checksums calculated with git hash-object
            123456.gz       # may be a .tar file, but silo doesn't know
        pack/               # like git, it can have deltas, and be repacked
          foo.pack
          foo.idx
        derived/            # DERIVED trees, e.g. different deltas,
                            # different compression, SquashFS, ...

### Commands

    silo verify             # blobs should have valid checksums

Existing tools:

    rsync        # back up the entire thing
    rclone       # ditto, but works with cloud storage

    ssh rm "$@"  # a list of vrefs to delete can be calculated by 'medo reachable'
    scp          # create a new silo from 'medo reachable' manifest

## Medo (meadow): Named and Versioned Subtrees in `git`

To start, this will untar and uncompress blobs from a Silo.  We can also:

- Materialize a git `tree`, e.g. in a packfile
- Mount a git `tree` directly with FUSE.  I think the pack `.idx` does binary
  search, which makes this possible.
  - TODO: write prototype with pygit2 wrapping libgit2
  - [FUSE bindings seem in question](https://stackoverflow.com/questions/52925566/which-module-is-the-actual-interface-to-fuse-from-python-3)

### Data

    ~/git/oilshell/oil/    
      deps/
        source.medo/                # Relocatable data
          SILO.json                 # Can point to multiple Silos
          Python-3.10.4.valu        # valu with checksum and provenance (original URL)

          images/
            debian/
              bullseye/
                slim.valu           # 'docker save' format

          layers/
            debian/
              bullseye/
                uftrace-build.valu  # packages needed to build it

        derived.medo/               # derived values, some are wedges with absolute paths
          SILO.json                 # Can point to multiple Silos
          debian/
            bullseye/
              Python-3.10.4.valu
          ubuntu/
            20.04/
              Python-3.10.4.valu    # derived data has provenance:
                                    # base layer, mounts of input / code, env / shell command
            22.04/
              Python-3.10.4.valu

### Commands

    # Get files to build.  This does uncompress/untar.
    medo sync deps/source.medo/Python-3.10.4.valu _tmp/source/

    # Or sync files that are already built.  If they already exist, verify
    # checksums.
    medo sync deps/derived.medo/debian/bullseye/ /wedge/oilshell.org/deps

    # Combine SILO.json and the JSON in the .valu
    medo url-for deps/source.medo/Python-3.10.4.valu

    # Verify checksums.
    medo verify deps.medo/ /wedge/oilshell.org/deps

    # Makes a tarball and .valu that you can scp/rsync
    medo add /wedge/oilshell.org/bash-4.4/ deps.medo/ubuntu/18.04/bash-4.4.valu

    medo reachable deps.medo/  # first step of garbage collection

    medo mount  # much later: FUSE mount

## /wedge: A subtree that works well with OCI containers

- It can be mounted, e.g. `--mount type=bind,...`
- It can be copied into an image: `COPY ...`
- It has provenance, like other vrefs.  Either:
  - the original URL
  - the code, data, and environment used to build it

## Data and Metadata Formats

Text:

- JSON for .valu and SILO.json
- lockfile / "world" / manifest - what does this look like?

Data:

- `git`
  - blob
  - tree for FS metadata 
  - no commit objects!
  - packfile for multiple objects
- Archiving: `.tar`, 
  - OCI layers use `.tar`
- Compression: `.gz`, `bzip2`, etc.
- Encryption (well LUKS does the whole system)

## TODO Later

- Analog for low level `runc`, `crun`
- Analog for high level `docker run`, `podman run`
- The equivalent of inotify() on a silo / medo.
  - could be an REST API on `https://app.oilshell.org/soil.medo/events/` for tarballs
  - it tells you what Silo to fetch from

## Ideas / Slogans

- "Distributed OS without RPCs".  Instead, with state synchronization.
