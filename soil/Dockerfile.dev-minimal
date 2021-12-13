FROM debian:buster-slim

RUN apt-get update

WORKDIR /home/uke/tmp

# Copy build scripts into the container and run them

COPY soil/deps-apt.sh /home/uke/tmp/soil/deps-apt.sh

RUN soil/deps-apt.sh layer-for-soil

RUN soil/deps-apt.sh dev-minimal

RUN useradd --create-home uke && chown -R uke /home/uke
USER uke

COPY soil/deps-py.sh /home/uke/tmp/soil/deps-py.sh
RUN soil/deps-py.sh dev-minimal

CMD ["sh", "-c", "echo 'hello from oilshell/soil-dev-minimal'"]
