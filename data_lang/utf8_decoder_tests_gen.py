# For generating the exhaustive utf8 decoder tests in data_lang/utf8_test.cc

DECODERS = ["bjorn", "crockford"]


def min_pat(pat):
    """Given a pattern like '1010xxxx', return the minimum value possible when
    substituting bits for each x.
    """
    return int(pat.replace('x', '0'), base=2)


def max_pat(pat):
    """Like min_pat, but produces the largest value from a substitution."""
    return int(pat.replace('x', '1'), base=2)


def test_patterns_fail(patterns):
    # Extract byte sequences from the input
    seqs = [seq.strip().replace('_', '').split() for seq in patterns]
    for seq in seqs:
        # Assume the patterns are continuous ranges (eg. 1001xxxx, not 10xx00xx)
        seq[:] = [range(min_pat(b), max_pat(b) + 1) for b in seq]

    # Construct test loops
    parts = []
    for seq in seqs:
        n = len(seq)

        iter_vars = list('xyzw')
        for i in range(n):
            iter_var = iter_vars[i]
            min = seq[i].start
            max = seq[i].stop
            # needs to be >= 16 bits as iter_var can be 0xFF (UINT8_MAX)
            parts.append('for (uint16_t %s = %d; %s < %d; ++%s) {' % (iter_var, min,
                                                                      iter_var, max,
                                                                      iter_var))

        input = ', '.join(map(lambda x: '(uint8_t)' + x, iter_vars[:n]))
        parts.append('''uint8_t bytes[] = {%s, 0};
            const uint8_t* ptr = bytes;
            uint32_t codepoint = 0;
            utf8_decode_result result = DECODER_utf8_next(&ptr, &codepoint);

            ASSERT_ENUM_EQ(result, UTF8_DECODE_ERROR, utf8_decode_result_str);
            ''' % input)

        for i in range(n):
            # \n to add an extra newline between for loops
            parts.append('}\n')

    return "\n".join(parts)


# Overlongs
patterns = """
  1100_000x 10xx_xxxx
  1110_0000 100x_xxxx 10xx_xxxx
  1111_0000 1000_xxxx 10xx_xxxx 10xx_xxxx
"""
patterns = (line.strip() for line in patterns.splitlines() if line)
overlongs_test = test_patterns_fail(patterns)

# Too Large
patterns = """
  1111_0101 10xx_xxxx 10xx_xxxx 10xx_xxxx
  1111_0110 10xx_xxxx 10xx_xxxx 10xx_xxxx
  1111_0111 10xx_xxxx 10xx_xxxx 10xx_xxxx
"""
patterns = (line.strip() for line in patterns.splitlines() if line)
too_large_test = test_patterns_fail(patterns)

# Bad bit distributions
patterns = """
  10xx_xxxx

  110x_xxxx 0xxx_xxxx
  110x_xxxx 11xx_xxxx

  1110_xxxx 0xxx_xxxx
  1110_xxxx 11xx_xxxx
  1110_xxxx 10xx_xxxx 0xxx_xxxx
  1110_xxxx 10xx_xxxx 11xx_xxxx

  1111_0xxx 0xxx_xxxx
  1111_0xxx 11xx_xxxx
  1111_0xxx 10xx_xxxx 0xxx_xxxx
  1111_0xxx 10xx_xxxx 11xx_xxxx
  1111_0xxx 10xx_xxxx 10xx_xxxx 0xxx_xxxx
  1111_0xxx 10xx_xxxx 10xx_xxxx 11xx_xxxx

  1111_1xxx
"""
patterns = (line.strip() for line in patterns.splitlines() if line)
bad_bits_test = test_patterns_fail(patterns)

all_tests = []
for decoder in DECODERS:
    tests = '''TEST DECODER_utf8_decoder_identity() {
      // Check that forall unicode scalar values x, decode(encode(x)) = x

      uint8_t bytes[5] = {0};
      for (uint32_t codepoint = 0; codepoint <= 0x10FFFF; ++codepoint) {
        // Skip surrogates
        if (0xD800 <= codepoint && codepoint <= 0xDFFF) {
          continue;
        }

        int length = utf8proc_encode_char(codepoint, bytes);
        ASSERT(length != 0);
        ASSERT(length < 5);
        bytes[length] = 0;

        const uint8_t* ptr = bytes;
        uint32_t decoded = 0;
        utf8_decode_result result = DECODER_utf8_next(&ptr, &decoded);
        ASSERT_ENUM_EQ(result, UTF8_DECODE_OK, utf8_decode_result_str);
        ASSERT_EQ(decoded, codepoint);
        ASSERT_EQ(ptr - bytes, length);
      }

      PASS();
    }

    TEST DECODER_utf8_decoder_surrogates() {
      // Check that decode(surrogate_sequence) => ERROR

      uint8_t bytes[5] = {0};
      for (uint32_t codepoint = 0xD800; codepoint <= 0xDFFF; ++codepoint) {
        int length = utf8proc_encode_char(codepoint, bytes);
        ASSERT(length != 0);
        ASSERT(length < 5);
        bytes[length] = 0;

        const uint8_t* ptr = bytes;
        uint32_t decoded = 0;
        utf8_decode_result result = DECODER_utf8_next(&ptr, &decoded);
        ASSERT_ENUM_EQ(result, UTF8_DECODE_ERROR, utf8_decode_result_str);
      }

      PASS();
    }

    TEST DECODER_utf8_decoder_overlong() {
      // Check that all overlong encodings are rejected

      %s

      PASS();
    }

    TEST DECODER_utf8_decoder_too_large() {
      // Check that all encodings of values over U+10FFFF are rejected

      %s

      PASS();
    }

    TEST DECODER_utf8_decoder_bad_bit_distribution() {
      // Handle all cases of bad bit distribution.

      %s

      PASS();
    }
    ''' % (overlongs_test, too_large_test, bad_bits_test)
    tests = tests.replace("DECODER", decoder)
    all_tests.append(tests)

print("\n".join(all_tests))
