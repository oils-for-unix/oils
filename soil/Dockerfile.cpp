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

# We're in /home/uke/tmp, so this will create /home/uke/oil_DEPS, which will be 
# a sibling of the runtime bind mount /home/uke/oil.

COPY soil/deps-tar.sh /home/uke/tmp/soil/deps-tar.sh

RUN soil/deps-tar.sh layer-re2c

CMD ["sh", "-c", "echo 'hello from oilshell/soil-cpp'"]
