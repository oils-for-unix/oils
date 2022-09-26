FROM oilshell/soil-common

# Copy again to prevent unsound caching
COPY deps/from-apt.sh /home/uke/tmp/deps/from-apt.sh

RUN --mount=type=cache,id=var-cache-apt,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,id=var-lib-apt,target=/var/lib/apt,sharing=locked \
    du --si -s /var/cache/apt /var/lib/apt && \
    deps/from-apt.sh cpp

# Build other dependencies as non-root uke
USER uke

# We're in /home/uke/tmp, so these will create /home/uke/oil_DEPS, which will be 
# a sibling of the runtime bind mount /home/uke/oil.

COPY deps/from-R.sh /home/uke/tmp/deps/from-R.sh
RUN deps/from-R.sh other-tests

# Used by deps/from-tar.sh
COPY build/common.sh /home/uke/tmp/build/common.sh
COPY deps/from-tar.sh /home/uke/tmp/deps/from-tar.sh

COPY --chown=uke _cache/bloaty-1.1.tar.bz2 \
  /home/uke/tmp/_cache/bloaty-1.1.tar.bz2
RUN deps/from-tar.sh layer-bloaty && \
    deps/from-tar.sh clean-temp

# TODO: slim down re2c, Python 3, like clean-temp

# re2c
RUN deps/from-tar.sh layer-re2c

# Run MyPy under Python 3.10
# Problem: .py files in _cache are used?
COPY --chown=uke _cache/Python-3.10.4.tar.xz \
  /home/uke/tmp/_cache/Python-3.10.4.tar.xz
RUN deps/from-tar.sh layer-py3

# Installs from PyPI
COPY mycpp/common-vars.sh /home/uke/tmp/mycpp/common-vars.sh
COPY mycpp/common.sh /home/uke/tmp/mycpp/common.sh
COPY deps/from-git.sh /home/uke/tmp/deps/from-git.sh
RUN deps/from-git.sh layer-mycpp

CMD ["sh", "-c", "echo 'hello from oilshell/soil-cpp'"]
