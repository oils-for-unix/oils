#ifndef DATA_LANG_J8_H
#define DATA_LANG_J8_H

#include <stdio.h>

#include "data_lang/utf8_impls/bjoern_dfa.h"

#define OUT_J8(ch) \
  **out = (ch);    \
  (*out)++

inline int EncodeRuneOrByte(unsigned char** in, unsigned char** out,
                            int is_j8) {
  // Reads from in and advances it
  //
  // Writes to out and advances it
  //   CALLER MUST CHECK that we are able to write 6 or more bytes!
  //   The longest output is \u001f or \u{1f} for control chars, since right now
  //   we're not writing escapes like \u{1f926}
  //
  // is_j8: Use j8 escapes, i.e. LOSSLESS encoding of bytes, not lossy
  //   \yff instead of Unicode replacement char
  //   \u{1} instead of \u0001 for unprintable low chars

  // Return value
  //   0   wrote valid UTF-8 (encoded or not)
  //   1   wrote byte that's invalid UTF-8

  unsigned char ch = **in;

  //
  // Handle \\ \b \f \n \r \t
  //
  switch (ch) {
  case '\\':
    OUT_J8('\\');
    OUT_J8('\\');
    (*in)++;
    return 0;
  case '\b':
    OUT_J8('\\');
    OUT_J8('b');
    (*in)++;
    return 0;
  case '\f':
    OUT_J8('\\');
    OUT_J8('f');
    (*in)++;
    return 0;
  case '\n':
    OUT_J8('\\');
    OUT_J8('n');
    (*in)++;
    return 0;
  case '\r':
    OUT_J8('\\');
    OUT_J8('r');
    (*in)++;
    return 0;
  case '\t':
    OUT_J8('\\');
    OUT_J8('t');
    (*in)++;
    return 0;
  }

  //
  // Conditionally handle \' and \"
  //
  if (ch == '\'' && is_j8) {
    OUT_J8('\\');
    OUT_J8('\'');  // escape code \'
    (*in)++;
    return 0;
  }
  if (ch == '"' && !is_j8) {  // " is escaped in JSON-style
    OUT_J8('\\');
    OUT_J8('"');  // escape code \"
    (*in)++;
    return 0;
  }

  //
  // Unprintable ASCII control codes
  //
  if (ch < 0x20) {
    if (is_j8) {
      int n = sprintf((char*)*out, "\\u{%x}", ch);
      *out += n;
    } else {
      int n = sprintf((char*)*out, "\\u%04x", ch);
      *out += n;
    }
    (*in)++;
    return 0;
  }

  //
  // UTF-8 encoded runes and invalid bytes
  //
  unsigned char* pstart = *in;  // save start position
  uint32_t codepoint = 0;
  uint32_t state = UTF8_ACCEPT;

  while (true) {
    decode(&state, &codepoint, ch);
    // printf("  state %d\n", state);
    switch (state) {
    case UTF8_REJECT: {
      (*in)++;
      int n = sprintf((char*)*out, "\\y%2x", ch);
      *out += n;
      return 1;
    }
    case UTF8_ACCEPT: {
      (*in)++;
      // printf("pstart %p in %p\n", pstart, *in);
      while (pstart < *in) {
        OUT_J8(*pstart);
        pstart++;
      }
      return 0;
    }
    default:
      (*in)++;  // advance, next UTF8_ACCEPT will write it
      ch = **in;
      break;
    }
  }

  //
  // Unreachable
  //
}

#endif  // DATA_LANG_J8_H
