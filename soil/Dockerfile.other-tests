FROM debian:buster-slim

RUN apt-get update 

# Copy this file into the container so we can run it.
WORKDIR /app
COPY soil/image-deps.sh .

RUN ./image-deps.sh other-tests

RUN ./image-deps.sh other-tests-R

CMD ["sh", "-c", "echo 'hello from oilshell/soil-other-tests buildkit'"]
