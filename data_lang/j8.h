#ifndef DATA_LANG_J8_H
#define DATA_LANG_J8_H

#include <stdio.h>

#include "data_lang/utf8_impls/bjoern_dfa.h"

#define J8_OUT(ch) \
  **p_out = (ch);  \
  (*p_out)++

inline int J8EncodeOne(unsigned char** p_in, unsigned char** p_out,
                       int j8_escape) {
  // We use a slightly weird double pointer style because
  //   *p_in may be advanced by 1 to 4 bytes (depending on whether it's UTF-8)
  //   *p_out may be advanced by 1 to 6 bytes (depending on escaping)

  // CALLER MUST CHECK that we are able to write up to 6 bytes!
  //   Because the longest output is \u001f or \u{1f} for control chars, since
  //   we don't escapes like \u{1f926} right now
  //
  // j8_escape: Whether to use j8 escapes, i.e. LOSSLESS encoding of data
  //   \yff instead of Unicode replacement char
  //   \u{1} instead of \u0001 for unprintable low chars

  // Returns:
  //   0   wrote valid UTF-8 (encoded or not)
  //   1   wrote byte that's invalid UTF-8

  unsigned char ch = **p_in;

  //
  // Handle \\ \b \f \n \r \t
  //
  switch (ch) {
  case '\\':
    J8_OUT('\\');
    J8_OUT('\\');
    (*p_in)++;
    return 0;
  case '\b':
    J8_OUT('\\');
    J8_OUT('b');
    (*p_in)++;
    return 0;
  case '\f':
    J8_OUT('\\');
    J8_OUT('f');
    (*p_in)++;
    return 0;
  case '\n':
    J8_OUT('\\');
    J8_OUT('n');
    (*p_in)++;
    return 0;
  case '\r':
    J8_OUT('\\');
    J8_OUT('r');
    (*p_in)++;
    return 0;
  case '\t':
    J8_OUT('\\');
    J8_OUT('t');
    (*p_in)++;
    return 0;
  }

  //
  // Conditionally handle \' and \"
  //
  if (ch == '\'' && j8_escape) {  // J8-style strings \'
    J8_OUT('\\');
    J8_OUT('\'');
    (*p_in)++;
    return 0;
  }
  if (ch == '"' && !j8_escape) {  // JSON-style strings \"
    J8_OUT('\\');
    J8_OUT('"');
    (*p_in)++;
    return 0;
  }

  //
  // Unprintable ASCII control codes
  //
  if (ch < 0x20) {
    if (j8_escape) {
      int n = sprintf((char*)*p_out, "\\u{%x}", ch);
      *p_out += n;
    } else {
      int n = sprintf((char*)*p_out, "\\u%04x", ch);
      *p_out += n;
    }
    (*p_in)++;
    return 0;
  }

  //
  // UTF-8 encoded runes and invalid bytes
  //
  unsigned char* start = *p_in;  // save start position
  uint32_t codepoint = 0;
  uint32_t state = UTF8_ACCEPT;

  while (true) {
    decode(&state, &codepoint, ch);
    // printf("  state %d\n", state);
    switch (state) {
    case UTF8_REJECT: {
      (*p_in)++;
      if (j8_escape) {
        int n = sprintf((char*)*p_out, "\\y%2x", ch);
        *p_out += n;
      } else {
        // Unicode replacement char is U+FFFD, so write encoded form
        // >>> '\ufffd'.encode('utf-8')
        // b'\xef\xbf\xbd'
        J8_OUT('\xef');
        J8_OUT('\xbf');
        J8_OUT('\xbd');
      }
      return 1;
    }
    case UTF8_ACCEPT: {
      (*p_in)++;
      // printf("start %p p_in %p\n", start, *p_in);
      while (start < *p_in) {
        J8_OUT(*start);
        start++;
      }
      return 0;
    }
    default:
      (*p_in)++;  // advance, next UTF8_ACCEPT will write it
      ch = **p_in;
      break;
    }
  }

  //
  // Unreachable
  //
}

// Right now \u001f and \u{1f} are the longest output sequences for a byte.
#define J8_MAX_BYTES_PER_INPUT_BYTE 6

inline int J8EncodeChunk(unsigned char** p_in, unsigned char* in_end,
                         unsigned char** p_out, unsigned char* out_end,
                         bool j8_escape) {
  while (*p_in < in_end && (*p_out + J8_MAX_BYTES_PER_INPUT_BYTE) <= out_end) {
    int invalid_utf8 = J8EncodeOne(p_in, p_out, j8_escape);
    if (invalid_utf8 && !j8_escape) {  // first JSON pass got binary data?
      return invalid_utf8;             // early return
    }
  }
  return 0;
}

// TODO: $'\x00\u1234' escaping
inline int ShellEncodeOne(unsigned char** p_in, unsigned char** p_out) {
  return 0;
}

inline int ShellEncodeChunk(unsigned char** p_in, unsigned char* in_end,
                            unsigned char** p_out, unsigned char* out_end) {
  while (*p_in < in_end && (*p_out + J8_MAX_BYTES_PER_INPUT_BYTE) <= out_end) {
    int dollar_fallback = ShellEncodeOne(p_in, p_out);
    if (dollar_fallback) {     // we need escaping, e.g. \u0001 or \'
      return dollar_fallback;  // early return
    }
  }
  return 0;
}

#endif  // DATA_LANG_J8_H
