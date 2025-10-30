regtest/aports
==============

`regtest/aports` tests OSH with Alpine Linux packages, in `aports/main`.  It's
organized as a series of "task files", which you can see with:

    $ regtest/aports-test.sh count-lines    # ~2000 lines including debug code

As usual, there are notes at the top of each task file.  Here is an overview.

## Set Up Machine to avoid `sudo` prompts

Add a file to `/etc/sudoers.d` so that `sudo` doesn't ask for a password after
a given time period.  Otherwise building the second shard may get "stuck".

This is how I did it manually:

    $ sudo visudo -f /etc/sudoers.d/no-timeout

The result should be:

    $ sudo cat /etc/sudoers.d/no-timeout
    Defaults:andy timestamp_timeout=-1

The -1 value means it's cached forever.

## Note on Directory Structure

The following scripts assume a directory structure like this:

```
*this can be any path*/
    oils-for-unix/
        oils/      # dir where this git repo is cloned
    alpinelinux/   # created by scripts below
```

This layout mimics the GitHub URL namespace.  If the layout on your machine differs, you might run into problems.

## Set up Alpine chroot - `he.oils.pub`

The first step is in `regtest/aports-setup.sh`:

    $ regtest/aports-setup.sh remove-chroot     # optional; for a CLEAN build

    $ regtest/aports-setup.sh fetch-all         # git clone, download Oils from CI
    $ regtest/aports-setup.sh prepare-all       # make a chroot

This usually happens on the **build server**, e.g. `he.oils.pub`.

    $ regtest/aports-setup.sh unpack-distfiles  # optional: requires _chroot/distfiles.tar

The file `_chroot/distfiles.tar` may contain ~6 GB of
`$CHROOT_DIR/var/cache/distfiles`.  Keeping the tarball saves the ~30 minutes
it takes to download all the `.tar.gz` source tarballs.

## Build aports Packages - `he.oils.pub`

If you didn't unpack `_chroot/distfiles.tar`, run:

    $ regtest/aports-run.sh fetch-packages '.*'

I do this separately, because contacting hundreds of servers is inherently reliable.

The results are not that consistent, so we divide the ~1640 `APKBUILD` files
into 17 *shards*.  You can run two shards like this:

    $ export APORTS_EPOCH=2025-08-07-fix   # directory name, and .wwz name

    $ regtest/aports-run.sh build-many-shards-overlayfs shard5 shard6

This is the normal way to run all 17 shards (using bash brace expansion):

    $ regtest/aports-run.sh build-many-shards-overlayfs shard{0..16}

But this is how I run it right now, due to flakiness:

      # weird order!
    $ regtest/aports-run.sh build-many-shards-overlayfs shard{10..16} shard{0..5}

      # Now BLOW AWAY CHROOT, to work around errors
    $ regtest/aports-setup.sh remove-chroot
    $ regtest/aports-setup.sh prepare-chroot
    $ regtest/aports-setup.sh unpack-distfiles

      # Run remaining shards
    $ regtest/aports-run.sh build-many-shards-overlayfs shard{6..9}

(This was discovered empirically; we should remove this workaround eventually.)


## Make Reports with Tables

### Credentials

You will need these credentials:

- to rsync from the `he.oils.pub` server
  - I think each person should have their own account
- to `scp` to `.wwz` and `.html` to the `op.oils.pub` server
  - ask for SSH key; give user name

### Sync and Preview - local machine

You can sync results while the build is running:

    $ regtest/aports-html.sh sync-results  # rsync from he.oils.pub to _tmp/aports-report

This creates a structure like:

    _tmp/aports-report/
      2025-08-07-fix/
        shard10/
        shard11/

And then make a partial report:

    $ regtest/aports-html.sh write-all-reports _tmp/aports-report/2025-08-07-fix

Now look at this file in your browser:

    _tmp/aports-report/2025-08-07-fix/diff_merged.html  # 17 shards merged


### Checking for Flakiness

The `aports` build can be flaky for a couple reasons, which are currently
unexplained:

1. The `abuild builddeps` step fails
1. "cannot create executable" or "cannot compile programs" errors.
   - Associated with "PHDR segment not covered".

Both of these errors happen with the baseline build, not only with OSH.

---

So right now, I periodically sync the results to my local machine, and check
the results with:

    $ regtest/aports-debug.sh grep-c-bug-2
    $ regtest/aports-debug.sh grep-phdr-bug-2
    $ regtest/aports-debug.sh grep-b-bug-2

If there are too many results, the chroot may have "crapped out".

TODO: we can fix this by:

- running under `podman` (`aports-container.sh`)
- running under a VM

### Publish Reports - `op.oils.pub`

After verifying the output of `write-all-reports`, add a line to the markdown
in `aports-html.sh published-html`.

Then share the results:

    $ regtest/aports-html.sh make-wwz _tmp/aports-report/2025-08-07-fix

    $ regtest/aports-html.sh deploy-wwz-op _tmp/aports-report/2025-08-07-fix.wwz

Now visit

- <https://op.oils.pub/aports-build/published.html>

which will link to:

- <https://op.oils.pub/aports-build/2025-08-07-fix.wwz/_tmp/aports-report/2025-08-07-fix/diff-merged.html>

### Add reports to `published.html`

If the results look good, add a line to the markdown in `regtest/aports-html.sh
published-html`, and then run:

    $ regtest/aports-html.sh deploy-published

And then visit:

- <https://op.oils.pub/aports-build/published.html>

## Other Instructions

### Reproducing a single package build failure

You can reproduce build failures on your own machine.  Do the same steps you did on `he.oils.pub`:

    $ regtest/aports-setup.sh fetch-all
    $ regtest/aports-setup.sh prepare-all

    $ regtest/aports-setup.sh unpack-distfiles  # optional

And then ONE of these commands:

    $ regtest/aports-run.sh set-baseline    # normal Alpine config
    $ regtest/aports-run.sh set-osh-as-sh   # replace /bin/sh with OSH

And then

    # 7zip is the PKG_FILTER
    # $config is either 'baseline' or 'osh-as-sh'
    $ regtest/aports-run.sh build-packages '7zip' $config

Then look at the logs in

    _chroot/aports-build/
      /home/udu/oils/
        _tmp/aports-guest/baseline/
          7zip.log.txt

### Get a Shell in the Chroot

    $ regtest/aports-run.sh enter-rootfs-user  # as unprivileged 'udu' user

    $ regtest/aports-run.sh enter-rootfs       # as root user

## TODO

- Running under podman could be more reliable
  - `regtest/aports-container.sh` shows that podman is able to run `abuild
    rootbld` -> `bwrap`, if it's passed the `--privileged` flag

## Related Links

- [Updating-Causes-of-Aports-Failures](https://github.com/oils-for-unix/oils/wiki/Updating-Causes-of-Aports-Failures) (wiki)

## Appendix: Dir Structure

```
he.oils.pub/
  ~/git/oils-for-unix/oils/
    _chroot/
      aports-build/
        enter-chroot  # you can run this, passing -u udu
        home/udu/     # user name is 'udu'
         oils/        # a subset of the Oils repo
           build/
             py.sh
           _tmp/
             aports-guest/
               baseline/
                 7zip.log.txt
                 7zip.task.tsv
               osh-as-sh/
               osh-as-bash/
      osh-as-sh.overlay/
        layer/
        merged/
          enter-chroot        # you can run this, passing -u udu
        work/
    _tmp/aports-build/ 
      2025-08-07-fix/         # $APORTS_EPOCH
        shard0/
          baseline/
            tasks.tsv         # concatenated .task.tsv
            log/     
              7zip.log.txt
            abridged-log/     # tail -n 1000 ont he log
              gcc.log.txt
        shard1/
          ...

localhost/
  ~/git/oils-for-unix/oils/
    _tmp/aports-report/         # destination for sync-results
        2025-08-07-fix/         # $APORTS_EPOCH
          diff-merged.html
          shard0/
            baseline/
              index.html        # from tasks.tsv
              tasks.tsv 
              log/     
                7zip.log.txt
              abridged-log/     # tail -n 1000 ont he log
                gcc.log.txt
            osh-as-sh/          # from tasks.tsv
              tasks.tsv
              log/
              abridged-log/
          index.html
```
