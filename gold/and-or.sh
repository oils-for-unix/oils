#!/usr/bin/env bash
#
# Test chained and/or.

# From Aboriginal sources/download_functions.sh.
noversion()
{
  LOGRUS='s/-*\(\([0-9\.]\)*\([_-]rc\)*\(-pre\)*\([0-9][a-zA-Z]\)*\)*\(\.tar\(\..z2*\)*\)$'
  [ -z "$2" ] && LOGRUS="$LOGRUS//" || LOGRUS="$LOGRUS/$2\\6/"

  echo "$1" | sed -e "$LOGRUS"
}


# Simplified version.
simple() {
  [ -z "$1" ] && LOGRUS="yes" || LOGRUS="no"
}

test-simple() {
  simple 1
  echo $LOGRUS
  simple ''
  echo $LOGRUS
}

"$@"
