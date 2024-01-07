#ifndef DATA_LANG_J8_H
#define DATA_LANG_J8_H

#include <stdio.h>
#include "data_lang/utf8_impls/bjoern_dfa.h"

// Reads from in and advances it
//
// Writes to out and advances it
//   CALLER MUST CHECK that we are able to write 6 or more bytes!
//
// is_j8: Use j8 escapes, i.e. LOSSLESS encoding of bytes rather than lossy
//   \yff instead of Unicode replacement char
//   \u{1} instead of \u0001 for unprintable low chars

// Return value
//   0   wrote valid UTF-8 (encoded or not)
//   1   wrote byte that's invalid UTF-8
//  -1   not enough space?

inline int EncodeRuneOrByte(unsigned char** in, unsigned char** out, int is_j8) {
  unsigned char ch = **in;

  switch (ch) {
    case '\\':
      **out = '\\'; (*out)++;
      **out = '\\'; (*out)++;
      (*in)++;
      return 0;
    case '\b':
      **out = '\\'; (*out)++;
      **out = 'b'; (*out)++;
      (*in)++;
      return 0;
    case '\f':
      **out = '\\'; (*out)++;
      **out = 'f'; (*out)++;
      (*in)++;
      return 0;
    case '\n':
      **out = '\\'; (*out)++;
      **out = 'n'; (*out)++;
      (*in)++;
      return 0;
    case '\r':
      **out = '\\'; (*out)++;
      **out = 'r'; (*out)++;
      (*in)++;
      return 0;
    case '\t':
      **out = '\\'; (*out)++;
      **out = 't'; (*out)++;
      (*in)++;
      return 0;
  }

  if (ch == '\'' && is_j8) {   // ' is escaped in J8-style
    **out = '\\'; (*out)++;
    **out = '\''; (*out)++;
    (*in)++;
    return 0;
  }

  if (ch == '"' && !is_j8) {  // " is escaped in JSON-style
    **out = '\\'; (*out)++;
    **out = '"'; (*out)++;
    (*in)++;
    return 0;
  }

  if (ch < 0x20) {  // unprintable low
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

  // default
  **out = ch; (*out)++;
  (*in)++;
  return 0;
}

#endif  // DATA_LANG_J8_H
