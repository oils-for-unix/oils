FROM debian:buster-slim

RUN apt-get update 

WORKDIR /home/uke/tmp

# Copy build scripts into the container and run them

COPY soil/deps-apt.sh /home/uke/tmp/soil/deps-apt.sh

RUN soil/deps-apt.sh layer-for-soil

RUN soil/deps-apt.sh other-tests

# Build other dependencies as non-root uke
RUN useradd --create-home uke && chown -R uke /home/uke
USER uke

COPY soil/deps-R.sh /home/uke/tmp/soil/deps-R.sh
RUN soil/deps-R.sh other-tests

CMD ["sh", "-c", "echo 'hello from oilshell/soil-other-tests buildkit'"]
