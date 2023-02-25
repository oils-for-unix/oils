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

Related:

- git annex
- git LFS

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

    du --si -s   # Total size of the Silo

## Medo (meadow): Named and Versioned Subtrees in `git`

To start, this will untar and uncompress blobs from a Silo.  We can also:

- Materialize a git `tree`, e.g. in a packfile
- Mount a git `tree` directly with FUSE.  I think the pack `.idx` does binary
  search, which makes this possible.
  - TODO: write prototype with pygit2 wrapping libgit2
  - [FUSE bindings seem in question](https://stackoverflow.com/questions/52925566/which-module-is-the-actual-interface-to-fuse-from-python-3)

### Data

    ~/git/oilshell/oil/    
      deps/                         # 3 medo structure is arbitrary; they're
                                    # generally mounted in different places, and
                                    # used by different tools
       
        source.medo/                # Relocatable data
          SILO.json                 # Can point to multiple Silos
          Python-3.10.4.valu        # valu with checksum and provenance (original URL)

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

        opaque.medo/                # Opaque values that can use more provenance.
          SILO.json
          images/                   # 'docker save' format.  Make sure it can be imported.
            debian/
              bullseye/
                slim.valu           

          layers/
            debian/
              bullseye/
                uftrace-build.valu  # packages needed to build it

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

## `/wedge`: A binary-centric "semi-distro" that works with OCI containers, and without

A package exports one or more binaries, and is a `valu`:

- metadata is stored in a `.medo` directory
- data is stored in a Silo

The package typically lives in a subdirectory of `/wedge`.  This is due to to
`configure --prefix=/wedge/...`.

What can you do with it?

- A wedge can be mounted, e.g. `--mount type=bind,...`
- It can be copied into an image: `COPY ...`
  - for quick deployment to cloud services, like Github Actions or fly.io
- It has provenance, like other valus.  The provenance is either:
  - the original URL, for source data
  - the code, data, and environment used to build it

Related:

- GNU Stow (symlinks)
- GoboLinux
- Distri (exchange dirs with FUSE)
- Nix/Bazel: a wedge is a "purely functional" value
- Docker: wedges are meant to be created in containers, and mounted in
  containers

### Data

    /wedge/               # an absolute path, for --configure --prefix=/wedge/..
      oilshell.org/       # scoped to domain
        dev/              # arbitrary structure, for dev dependencies
          Python-3.10.4.valu  # metadata
          Python-3.10.4/
            python            # Executable, which needs a 'python3' symlink

## Design Notes

### Data and Metadata Formats

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

### knot: Incremental, Parallel, Coarse-Grained, Containerized Builds with Ninja

It's a wrapper like `ninja_lib.py`.  Importantly, everything you build should
be versioned, immutable, and cached, so it doesn't use timestamps!  

Distributed builds, too?  Multiple workers can pull and publish intermediate
values to the same Silo.

(Name: it's geometry like "wedge", and hopefully cuts a "Gordian knot.")

## TODO 

### Research

- shrub vs. blob?
  - a shrub is a subtree, unlike a git `tree` object which is like an inode
  - is all of the metadata like paths and sizes stored client side?  Then the
    client can give repacking hints for differential compression, rather than
    the server doing anything smart.
  - medo explode?  You change the reference client-side
  - or silo explode?  It can redirect from blob to shrub
- TODO: look at git tree format, and whether an entire subtree/shrub of
  metadata can be stored client-side.  We want ONLY trees, and blobs should be
  DANGLING.
  - Use pack format, or maybe a text format.

```
~/git/oilshell/oil$ git cat-file -p master^{tree}
040000 tree 37689433372bc7f1db7109fe1749bff351cba5b0    .builds
040000 tree 5d6b8fdbeb144b771e10841b7286df42bfce4c52    .circleci
100644 blob 6385fd579efef14978900830e5fd74bbac907011    .cirrus.yml
100644 blob 343af37bf39d45b147bda8a85e8712b0292ddfea    .clang-format
040000 tree 03400f57a8475d0cc696557833088d718adb2493    .github
```

### More

- Analog for low level `runc`, `crun`
- Analog for high level `docker run`, `podman run`
- The equivalent of inotify() on a silo / medo.
  - could be an REST API on `https://app.oilshell.org/soil.medo/events/` for tarballs
  - it tells you what Silo to fetch from
- Source browser for https://www.oilshell.org/deps.silo

## Ideas / Slogans

- "Distributed OS without RPCs".  We use the paradigms of state
  synchronization, dependency graphs (partial orders), and probably low-level
  "events".
- Silo is the **data plane**; Medo is the **control plane**
  - Hay config files will also be a control plane
- Silo is a **mechanism**; Medo is for **policy**
- `/wedge` is a **middleground** between Docker and Nix/Bazel
  - Nix / Bazel are purely functional, but require rewriting upstream build
    systems in their own language (to fully make use of them)
    - Concretely: I don't want to rewrite the R build system for the tidyverse.
      I want to use the Debian packaging that already works, and that core R
      developers maintain.
  - `/wedge` is purely functional in the sense that wedges are literally
    **values**.  But like Docker, you can use shell commands that mutate layers
    to create them.  You can run entire language package managers and build
    systems via shell.
  - Wedges compose with, and compose better than, Docker layers.
