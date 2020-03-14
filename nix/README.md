# Oil developer builds with Nix

The [Nix](https://nixos.org/nix/) package manager makes it fairly simple to build a development version of Oil.

If you don't already have Nix, follow [installation instructions](https://nixos.org/nix/download.html) before continuing.

## Quick Start

```shell
git clone https://github.com/oilshell/oil.git    # or use your own fork

cd oil                    # or enter the base directory

nix-build                 # builds Oil from source and runs the test suite

result/bin/osh -c "echo hello, world!"
result/bin/oil -c "echo hello, world!"
```

The first time you run nix-build, it'll take a bit to download and build Oil's
dependencies. 

### Out-of-tree Nix developer builds

When you run `nix-build` from oil's root directory, Nix copies the Oil source
out into an isolated build directory where it only has access to declared
dependencies, builds it, and then creates a `result` symlink in your current
directory to the output. You can use this symlink to run both shells 
(`result/bin/osh` and `result/bin/oil`).

This *out-of-tree* build: 
- takes a little longer
- is better isolated from other software on your system
- only provides access to Oil's own executables

### In-tree Nix developer builds

You can also run `nix-shell` in the root of the Oil repo to create an in-tree developer
build. (Note: because this build is in-tree, it's possible for it to clash with 
artifacts from other in-tree builds.) This command will take a little while to build
dependencies the first time you run it, but it will complete quickly on subsequent runs 
unless the code or dependencies change.

When the command finishes building Oil, you'll be dropped into a sub-shell (with a new prompt indicating that you're in nix-shell) where you'll have access to both oil/osh, 
*and* the software you need to build and test osh (including the other test shells).

```shell
$ nix-shell
Building 'all' Oil.
... [snip]...
Note: nix-shell will clean up the dev build on exit.

[nix-shell:~/work/oil]$ bin/osh -c "echo hello, world!"

# test shells are available inside
[nix-shell:~/work/oil]$ which mksh
/nix/store/0z9qxqkp7ra6l6argcmvjjvbr5d0ng4g-mksh-52/bin/mksh

# exit to return to your regular shell session
$ exit
Cleaning up Oil dev build.
... [snip] ...
```

This *in-tree* build: 
- finishes a little faster
- provides a convenient way to build and access everything you need to build
  and test Oil
- is not as well isolated from other software on your system (including
  any other in-tree build of Oil)
