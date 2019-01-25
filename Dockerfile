#BUILD EXAMPLE: docker build . -t osh
#Tested with Docker Desktop Version 2.0.0.2 (30215) on MacOS 10.14.1 (18B75) 

#FROM alpine
#RUN apk add --no-cache gcc musl-dev make file sed

FROM ubuntu:18.04

RUN apt update \
&& apt upgrade \
&& apt install -y python2.7 \
&& apt install -y python-pip \
&& apt-get install sudo -y

COPY ./ /tmp

RUN cd /tmp \
&& yes | build/dev.sh ubuntu-deps \
&& build/dev.sh minimal \
&& bin/osh --version

RUN ln -s /tmp/bin/osh /usr/local/bin/osh 
WORKDIR /tmp

ENTRYPOINT [ "/tmp/bin/osh" ]

#USAGE EXAMPLEs: docker run -ti --rm osh -c 'echo hi'
#interactive     docker run -ti --rm osh
#script file     docker run -ti -v /Users/Shared/x.sh:/x.sh --rm osh /x.sh
