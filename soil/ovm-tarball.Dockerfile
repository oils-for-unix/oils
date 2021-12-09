FROM debian:buster-slim

RUN apt-get update 

# Copy this file into the container so we can run it.
WORKDIR /app
COPY soil/image-deps.sh .

RUN ./image-deps.sh ovm-tarball

# This is necessary to build a Python 2.7 tarball, i.e. in build/prepare.sh
RUN ln -s /usr/bin/python2 /usr/bin/python

RUN ./image-deps.sh ovm-tarball-source-deps

CMD ["sh", "-c", "echo 'hello from oilshell/ovm-tarball buildkit'"]
