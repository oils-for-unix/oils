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
