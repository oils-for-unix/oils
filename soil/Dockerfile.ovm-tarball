FROM debian:buster-slim

RUN apt-get update 

WORKDIR /home/uke/tmp

# Copy build scripts into the container and run them

COPY soil/deps-apt.sh /home/uke/tmp/soil/deps-apt.sh

RUN soil/deps-apt.sh layer-for-soil

RUN soil/deps-apt.sh ovm-tarball

RUN soil/deps-apt.sh layer-python-symlink

RUN soil/deps-apt.sh layer-locales

RUN useradd --create-home uke && chown -R uke /home/uke
USER uke

# TODO: Figure out a better way to handle deps?
COPY Python-2.7.13/ /home/uke/tmp/Python-2.7.13/

COPY build/common.sh /home/uke/tmp/build/common.sh
COPY soil/deps-tar.sh /home/uke/tmp/soil/deps-tar.sh

RUN soil/deps-tar.sh layer-cmark
RUN soil/deps-tar.sh layer-re2c
RUN soil/deps-tar.sh layer-cpython

COPY test/spec-common.sh /home/uke/tmp/test/spec-common.sh
COPY test/spec-bin.sh /home/uke/tmp/test/spec-bin.sh

RUN test/spec-bin.sh all-steps

CMD ["sh", "-c", "echo 'hello from oilshell/ovm-tarball'"]
