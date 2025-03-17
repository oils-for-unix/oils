#!/usr/bin/env bash
#
# Testing how to send requests without curl
#
# Client features
#
# - SSL, for HTTPS
# - Connection: Keep-Alive, for latency
# - Timeouts, for robustness
# - Client side redirects
# - Sending arbitrary headers, for auth
# - Encoding: URL encoding, multi-part/MIME
#   - It would be nice to offload this encoding, similar to how CGI v2 offloads
#     parsing
# - Large streaming uploasd and downloads - this might need to be a separate
#   request, e.g. to the wwup process
# 
# Probably don't care about:
# - HTTP Cache - we might have a different mechanism - this is very complex and
#   "best effort"
#   - or there can be local cache of the "Oils SQL Waist"
# - Cookies?  Not sure
#
# Not sure:
# - Proxy support

with-openssl() {
  # Hm, it works for google.com, yahoo, HN, dreamhost.com/
  #
  # But Dreamhost shared hosting doesn't like it for some reason - get 400
  # error
  local hostname=${1:-www.google.com}

  #openssl s_client -connect $hostname:443 <<EOF
  openssl s_client -connect $hostname:443 -quiet <<EOF
GET / HTTP/1.1
Host: $hostname

EOF
}

get-home() {
  local hostname=${1:-oils.pub}
  printf 'GET / HTTP/1.1\r\nHost: %s\r\n\r\n' "$hostname" 
}

# Hm this works, the \r\n does matter.
crlf() {
  local hostname=${1:-oils.pub}
  get-home "$hostname" |
    openssl s_client -connect $hostname:443 -quiet
}

with-curl() {
  curl -v --include https://oils.pub/ |head
}

# TODO:
# - HTTPS
#   - socat
#   - BoringSSL has 's_client' I guess
# - for plain HTTP
#   - nc
#   - telnet

deps() {
  sudo apt-get install socat
}

with-socat() {
  # This closes the pipe
  local hostname=${1:-mb.oils.pub}
  time get-home "$hostname" |
    socat - openssl:$hostname:443
}

with-socat-http() {
  # This closes the pipe
  local hostname=${1:-mb.oils.pub}
  time get-home "$hostname" |
    socat - tcp:$hostname:80
}


with-socat-2() {
  # This sorta works
  local hostname=${1:-mb.oils.pub}

  { get-home "mb.oils.pub";
    get-home "mb.oils.pub";
  } | socat - openssl:$hostname:443,fork
}

with-telnet() {
  # Hm doesn't work
  local hostname=${1:-mb.oils.pub}
  time get-home "$hostname" | telnet $hostname 80
}

with-nc() {
  # Hm doesn't work
  local hostname=${1:-mb.oils.pub}
  time get-home "$hostname" | nc $hostname 80
}

"$@"
