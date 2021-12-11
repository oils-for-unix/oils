FROM debian:buster-slim

RUN apt-get update 

WORKDIR /app/tmp

# Copy build scripts into the container and run them

COPY soil/deps-apt.sh /app/tmp/soil/deps-apt.sh
RUN soil/deps-apt.sh cpp

# We're in /app/tmp, so this will create /app/oil_DEPS, which will be 
# a sibling of the runtime bind mount /app/oil.

COPY soil/deps-tar.sh /app/tmp/soil/deps-tar.sh
RUN soil/deps-tar.sh cpp

CMD ["sh", "-c", "echo 'hello from oilshell/soil-cpp buildkit'"]
