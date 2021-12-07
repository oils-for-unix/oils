FROM debian:buster-slim

# TODO: build/dev.sh buster-deps.  But then we need to put these at the root.

# And like Github Actions
# build/dev.sh install-py2
# build/dev.sh install-py3

RUN apt update && \
    apt install -y python2-dev gawk libreadline-dev \
                   python3-setuptools python3-pip


# TODO: consolidate these
RUN apt install -y python-pip
RUN apt install -y git
# Note: osh-minimal task needs shells; not using spec-bin for now
RUN apt install -y busybox-static mksh zsh

# From .builds/dev-minimal.yml
RUN pip install --user flake8 typing

# MyPy requires Python 3, but Oil requires Python 2.
RUN pip3 install --user mypy

CMD ["sh", "-c", "echo 'hello from oilshell/soil-dev-minimal buildkit'"]
