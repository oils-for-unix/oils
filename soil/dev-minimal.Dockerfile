FROM debian:buster-slim

# TODO: build/dev.sh buster-deps.  But then we need to put these at the root.

# And like Github Actions
# build/dev.sh install-py2
# build/dev.sh install-py3

RUN apt-get update

# Copy this file into the container so we can run it.
WORKDIR /app
COPY soil/image-deps.sh .

RUN ./image-deps.sh dev-minimal

RUN ./image-deps.sh dev-minimal-py

CMD ["sh", "-c", "echo 'hello from oilshell/soil-dev-minimal buildkit'"]
