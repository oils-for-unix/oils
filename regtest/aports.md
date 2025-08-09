regtest/aports
==============

`regtest/aports` tests OSH with Alpine Linux packages, in `aports/main`.  It's
organized as a series of "task files", which you can see with:

    $ regtest/aports-test.sh count-lines    # ~2000 lines including debug code

As usual, there are notes at the top of each task file.  Here is an overview.

## Set up Alpine chroot - `he.oils.pub`

The first step is is in `regtest/aports-setup.sh`:

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

    $ regtest/aports-run.sh build-many-shards shard5 shard6

To run all 17 shards, you can use bash brace expansion:

    $ regtest/aports-run.sh build-many-shards shard{0..16}

## Reports

### Make HTML reports - local machine

    $ regtest/aports-html.sh sync-results  # rsync to _tmp/aports-report

    $ regtest/aports-html.sh write-all-reports _tmp/aports-report/2025-08-07-fix

Now look at this file in your browser:

    _tmp/aports-report/2025-08-07-fix/diff-merged.html  # 17 shards merged

### Publish Reports - `op.oils.pub`

Share the results:

    $ regtest/aports-html.sh make-wwz _tmp/aports-report/2025-08-07-fix

    $ regtest/aports-html.sh deploy-wwz-op _tmp/aports-report/2025-08-07-fix.wwz

Now visit

- <https://op.oils.pub/aports-build/2025-08-07-fix.wwz/>

And then navigate to

- <https://op.oils.pub/aports-build/2025-08-07-fix.wwz/_tmp/aports-report/2025-08-07-fix/diff-merged.html>

### Official link from `pages.oils.pub`

If the results are good, then add a link to:

- <https://pages.oils.pub/>
  - via the repo <https://github.com/oils-for-unix/oils-for-unix.github.io>

TODO: it could be better to keep it consistent and use `op.oils.pub`.  But I
guess I like to have a version-controlled record of all the "good" runs.

## Updating Causes

See [regtest/aports-cause.awk](regtest/aports-cause.awk).

Faster way to test it:

    $ regtest/aports-html.sh merge-diffs _tmp/aports-report/2025-08-07-fix/

## TODO

- Update the top of each task file
- Add bug numbers to the report
- Running under podman could be more reliable
  - that also means we do a bind mount?
