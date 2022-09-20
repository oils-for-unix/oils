FROM debian:buster-slim

RUN apt-get update 

WORKDIR /home/uke/tmp

# Copy build scripts into the container and run them

COPY deps/from-apt.sh /home/uke/tmp/deps/from-apt.sh

RUN deps/from-apt.sh layer-for-soil

RUN deps/from-apt.sh cpp

# Build other dependencies as non-root uke
RUN useradd --create-home uke && chown -R uke /home/uke
USER uke

# We're in /home/uke/tmp, so these will create /home/uke/oil_DEPS, which will be 
# a sibling of the runtime bind mount /home/uke/oil.

# Used by deps/from-tar.sh
COPY build/common.sh /home/uke/tmp/build/common.sh

COPY deps/from-tar.sh /home/uke/tmp/deps/from-tar.sh

# re2c
RUN deps/from-tar.sh layer-re2c

COPY --chown=uke _cache/bloaty-1.1.tar.bz2 \
  /home/uke/tmp/_cache/bloaty-1.1.tar.bz2
RUN deps/from-tar.sh layer-bloaty

# Run MyPy under Python 3.10
COPY --chown=uke _cache/Python-3.10.4.tar.xz \
  /home/uke/tmp/_cache/Python-3.10.4.tar.xz
RUN deps/from-tar.sh layer-py3

# Installs from PyPI
COPY mycpp/common-vars.sh /home/uke/tmp/mycpp/common-vars.sh
COPY mycpp/common.sh /home/uke/tmp/mycpp/common.sh
COPY deps/from-git.sh /home/uke/tmp/deps/from-git.sh
RUN deps/from-git.sh layer-mycpp

CMD ["sh", "-c", "echo 'hello from oilshell/soil-cpp'"]
