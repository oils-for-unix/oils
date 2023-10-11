`deps/` Directory
=================

Scripts to build various dependencies.  They can used on the host machine, or
in a Dockerfile to build a container.  The container is used in our CI build,
and can also be used locally.

## Docker Files

Our images:

- <https://hub.docker.com/u/oilshell>

Base image maintained by:

- <https://hub.docker.com/_/debian>
- <https://github.com/debuerreotype/debuerreotype>

Note: we could use names like `buster-20220912-slim` instead of `buster-slim`.

- How can we get notified when the image is updated?
  - <https://crazymax.dev/diun/> has many notification mechanisms


## Container Dir Structure

The file system in our images looks like this:

    /home/uke/
      tmp/             # Dockerfiles copy build scripts here
      oil/             # soil/host-shim.sh mounts the repo here
        _tmp/          # published as .wwz files to CI
      oil_DEPS/        # Built into containers
        cpython-full/  # build of Python
        py3/           # like cpython-full

        mycpp-venv/    # installed by python3 -m pip
        mypy/          # git repo

        spec-bin/
        wild/          # Pure data

        cmark/

        libcmark.so    # shared library
        python3        # Plain executable

Note that `build/dev-shell.sh` puts some executables in `$PATH`.

TODO:

- We should `--mount type=bind` "wedges" into say `/wedge/foo`
  - These can be either data or executable tools
  - I suppose `/home/uke/{oil,oil_DEPS}` are also wedges? They are meant not to conflict
  - But we want wedges to work OUTSIDE containers too.
- We should also be able to COPY wedges into an image, for easier deployment on
  cloud services like Github Actions and fly.io
- Then run an arbitrary shell command that uses the code and data
- Outputs can go back into `/wedge`
  - Problems: absolute paths, root, `make install`, etc.

Dir structure:

    /wedge/   # or you can build your own /home/andy/wedge
      oilshell.org/  # built for this distro, e.g. ubuntu-18.04
        DEPS/
          Python-2.7.13/
          Python-3.10.4/
          bash-4.4/
          bash-5.1/

And then we'll need some symlinks like `python3`, etc.

## Kinds of Tarballs / "Dir Values"

- Source vs. Intermediate - what repo stores it?
- Absolute vs. Relative - where is it mounted?
- Layer vs. Wedge - how is it mounted?

## Soil C++ Tarball Notes

cpp-tarball is consumed by these jobs now:

- raw-vm
- wild
- app-tests for ble.sh

If we use it in more tasks, we could try to remove MyPy/Python 3 from Docker
images.  It should especially speed up the pull on sourcehut -- 30-40 seconds
for pea/other-tests, vs. 2:13 for benchmarks2

So these can also consume the tarball:

- benchmarks
- benchmarks2
- interactive uses the 'benchmarks' image for some reason
- cpp-spec
  - build ASAN binary from tarball
  - needs both osh and ysh
- cpp-coverage -- would need to include C++ unit tests and Ninja in tarball,
  which is not a bad idea

More:

- Alpine testing
- Smoosh testing with OCaml, similar to spec tests

