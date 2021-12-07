FROM debian

# gcc: time-helper is needed
# git: for checking out code
# zip: for soil web publishing
RUN apt update && apt install -y gcc git zip python2

CMD ["sh", "-c", "echo 'hello from oilshell/soil-dummy buildkit'"]
