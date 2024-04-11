#!/usr/bin/env sh

mkdir -p _gen/test/utf8
python3 data_lang/utf8_decoder_tests_gen.py >_gen/test/utf8/decoder-exhaustive.inc
clang-format -i _gen/test/utf8/decoder-exhaustive.inc
