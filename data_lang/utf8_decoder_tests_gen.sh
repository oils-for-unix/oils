#!/usr/bin/env bash

mkdir -p _gen/test/utf8
clang-format <(python3 data_lang/utf8_decoder_tests_gen.py) >_gen/test/utf8/decoder-exhaustive.inc
