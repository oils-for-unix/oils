FROM debian:buster-slim

RUN apt-get update 

WORKDIR /home/uke/tmp

# Copy build scripts file into the container and run them

COPY soil/deps-apt.sh /home/uke/tmp/soil/deps-apt.sh
RUN soil/deps-apt.sh layer-for-soil

RUN soil/deps-apt.sh layer-locales

RUN useradd --create-home uke && chown -R uke /home/uke
USER uke

CMD ["sh", "-c", "echo 'hello from oilshell/soil-dummy'"]
