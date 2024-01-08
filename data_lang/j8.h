#ifndef DATA_LANG_J8_H
#define DATA_LANG_J8_H

#include <stdio.h>

#include "data_lang/utf8_impls/bjoern_dfa.h"

#define J8_OUT(ch) \
  **out = (ch);    \
  (*out)++

inline int EncodeRuneOrByte(unsigned char** in, unsigned char** out,
                            int j8_escape) {
  // We use a slightly weird double pointer style because
  //   'in' may be advanced by 1 to 4 bytes (depending on whether it's UTF-8)
  //   'out' may be advanced by 1 to 6 bytes (depending on escaping)

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

  unsigned char ch = **in;

  //
  // Handle \\ \b \f \n \r \t
  //
  switch (ch) {
  case '\\':
    J8_OUT('\\');
    J8_OUT('\\');
    (*in)++;
    return 0;
  case '\b':
    J8_OUT('\\');
    J8_OUT('b');
    (*in)++;
    return 0;
  case '\f':
    J8_OUT('\\');
    J8_OUT('f');
    (*in)++;
    return 0;
  case '\n':
    J8_OUT('\\');
    J8_OUT('n');
    (*in)++;
    return 0;
  case '\r':
    J8_OUT('\\');
    J8_OUT('r');
    (*in)++;
    return 0;
  case '\t':
    J8_OUT('\\');
    J8_OUT('t');
    (*in)++;
    return 0;
  }

  //
  // Conditionally handle \' and \"
  //
  if (ch == '\'' && j8_escape) {  // J8-style strings \'
    J8_OUT('\\');
    J8_OUT('\'');
    (*in)++;
    return 0;
  }
  if (ch == '"' && !j8_escape) {  // JSON-style strings \"
    J8_OUT('\\');
    J8_OUT('"');
    (*in)++;
    return 0;
  }

  //
  // Unprintable ASCII control codes
  //
  if (ch < 0x20) {
    if (j8_escape) {
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
      if (j8_escape) {
        int n = sprintf((char*)*out, "\\y%2x", ch);
        *out += n;
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
      (*in)++;
      // printf("pstart %p in %p\n", pstart, *in);
      while (pstart < *in) {
        J8_OUT(*pstart);
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
