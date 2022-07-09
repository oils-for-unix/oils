FROM debian:buster-slim

RUN apt-get update 

WORKDIR /home/uke/tmp

# Copy build scripts into the container and run them

COPY soil/deps-apt.sh /home/uke/tmp/soil/deps-apt.sh

RUN soil/deps-apt.sh layer-for-soil

RUN soil/deps-apt.sh cpp

# Build other dependencies as non-root uke
RUN useradd --create-home uke && chown -R uke /home/uke
USER uke

# We're in /home/uke/tmp, so these will create /home/uke/oil_DEPS, which will be 
# a sibling of the runtime bind mount /home/uke/oil.

# Used by soil/deps-{binary,tar}.sh
COPY build/common.sh /home/uke/tmp/build/common.sh

# For Clang coverage
COPY soil/deps-binary.sh /home/uke/tmp/soil/deps-binary.sh
#RUN soil/deps-binary.sh layer-clang

# re2c
COPY soil/deps-tar.sh /home/uke/tmp/soil/deps-tar.sh
RUN soil/deps-tar.sh layer-re2c

# Installs from PyPI
COPY mycpp/common.sh /home/uke/tmp/mycpp/common.sh
COPY soil/deps-mycpp.sh /home/uke/tmp/soil/deps-mycpp.sh
RUN soil/deps-mycpp.sh layer-mycpp

CMD ["sh", "-c", "echo 'hello from oilshell/soil-cpp'"]
