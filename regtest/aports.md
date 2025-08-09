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

The result shoudl be:

    $ sudo cat /etc/sudoers.d/no-timeout
    Defaults:andy timestamp_timeout=-1

The -1 value means it's cached forever.

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

TODO: credentials necessary;

- `he.oils.pub` server
  - I think each person has their own account?
- `op.oils.pub` web server (for `.wwz` files)
  - ask for SSH key
- Github pages repo
  - sent github invite

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

- Running under podman could be more reliable
  - that also means we do a bind mount?

## Appendix: Dir Structure

```
he.oils.pub/
  ~/git/oils-for-unix/oils/
    _chroot/aports-build/
      home/udu/    # user name is 'udu'
       oils/       # a subset of the Oils repo
         build/
           py.sh
         _tmp/
           aports-guest/
             baseline/
               7zip.log.txt
               7zip.task.tsv
             osh-as-sh/
             osh-as-bash/
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
