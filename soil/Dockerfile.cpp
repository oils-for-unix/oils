FROM debian:buster-slim

RUN apt-get update 

# Copy this file into the container so we can run it.
WORKDIR /app
COPY soil/image-deps.sh .

RUN ./image-deps.sh cpp

RUN ./image-deps.sh cpp-source-deps

CMD ["sh", "-c", "echo 'hello from oilshell/soil-cpp buildkit'"]
