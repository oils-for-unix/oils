#!/bin/bash
set -e

apt-get update
apt-get install -y $1 --no-install-recommends
