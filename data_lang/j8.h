#ifndef DATA_LANG_J8_H
#define DATA_LANG_J8_H

#include <stdio.h>

#include "data_lang/utf8_impls/bjoern_dfa.h"

#define J8_OUT(ch) \
  **p_out = (ch);  \
  (*p_out)++

static inline int J8EncodeOne(unsigned char** p_in, unsigned char** p_out,
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
      // printf("Writing for %04x %p\n", ch, *p_out);
      int n = sprintf((char*)*p_out, "\\u{%x}", ch);
      // printf("! Wrote %d bytes for %04x\n", n, ch);
      *p_out += n;
    } else {
      // printf("Writing for %04x %p\n", ch, *p_out);
      int n = sprintf((char*)*p_out, "\\u%04x", ch);
      *p_out += n;
      // printf("Wrote %d bytes for %04x\n", n, ch);
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

  while (1) {
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
  // Unreachable
}

// Like the above, but
//
//   \xff instead of \yff
//   \u001f always, never \u{1f}
//   No JSON vs. J8
//     No \" escape ever
//     No errors -- it can encode everything

static inline void BashDollarEncodeOne(unsigned char** p_in,
                                       unsigned char** p_out) {
  unsigned char ch = **p_in;

  //
  // Handle \\ \b \f \n \r \t
  //
  switch (ch) {
  case '\\':
    J8_OUT('\\');
    J8_OUT('\\');
    (*p_in)++;
    return;
  case '\b':
    J8_OUT('\\');
    J8_OUT('b');
    (*p_in)++;
    return;
  case '\f':
    J8_OUT('\\');
    J8_OUT('f');
    (*p_in)++;
    return;
  case '\n':
    J8_OUT('\\');
    J8_OUT('n');
    (*p_in)++;
    return;
  case '\r':
    J8_OUT('\\');
    J8_OUT('r');
    (*p_in)++;
    return;
  case '\t':
    J8_OUT('\\');
    J8_OUT('t');
    (*p_in)++;
    return;
  case '\'':
    J8_OUT('\\');
    J8_OUT('\'');
    (*p_in)++;
    return;
  }

  //
  // Unprintable ASCII control codes
  //
  if (ch < 0x20) {
    // printf("Writing for %04x %p\n", ch, *p_out);
    int n = sprintf((char*)*p_out, "\\u%04x", ch);
    *p_out += n;
    // printf("Wrote %d bytes for %04x\n", n, ch);
    (*p_in)++;
    return;
  }

  //
  // UTF-8 encoded runes and invalid bytes
  //
  unsigned char* start = *p_in;  // save start position
  uint32_t codepoint = 0;
  uint32_t state = UTF8_ACCEPT;

  while (1) {
    decode(&state, &codepoint, ch);
    // printf("  state %d\n", state);
    switch (state) {
    case UTF8_REJECT: {
      (*p_in)++;
      int n = sprintf((char*)*p_out, "\\x%2x", ch);
      *p_out += n;
      return;
    }
    case UTF8_ACCEPT: {
      (*p_in)++;
      // printf("start %p p_in %p\n", start, *p_in);
      while (start < *p_in) {
        J8_OUT(*start);
        start++;
      }
      return;
    }
    default:
      (*p_in)++;  // advance, next UTF8_ACCEPT will write it
      ch = **p_in;
      break;
    }
  }
  // Unreachable
}

// BourneShellEncodeOne rules:
//
//   must be valid UTF-8
//   no control chars
//   no ' is required
//   no \ -- not required, but avoids ambiguous '\n'
//
// For example we write $'\\' or b'\\' not '\'
// The latter should be written r'\', but we're not outputing

static inline int BourneShellEncodeOne(unsigned char** p_in,
                                       unsigned char** p_out) {
  unsigned char ch = **p_in;

  if (ch == '\'' || ch == '\\') {  // can't encode these in Bourne shell ''
    return 1;
  }
  if (ch < 0x20) {  // Unprintable ASCII control codes
    return 1;
  }

  // UTF-8 encoded runes and invalid bytes
  unsigned char* start = *p_in;  // save start position
  uint32_t codepoint = 0;
  uint32_t state = UTF8_ACCEPT;

  while (1) {
    decode(&state, &codepoint, ch);
    // printf("  state %d\n", state);
    switch (state) {
    case UTF8_REJECT: {
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
  // Unreachable
}

// Right now \u001f and \u{1f} are the longest output sequences for a byte.
// Bug fix: we need 6 + 1 for the NUL terminator that sprintf() writes!  (Even
// though we don't technically need it)

#define J8_MAX_BYTES_PER_INPUT_BYTE 7

static inline int J8EncodeChunk(unsigned char** p_in, unsigned char* in_end,
                                unsigned char** p_out, unsigned char* out_end,
                                int j8_escape) {
  while (*p_in < in_end && (*p_out + J8_MAX_BYTES_PER_INPUT_BYTE) <= out_end) {
    // printf("iter %d  %p < %p \n", i++, *p_out, out_end);
    int invalid_utf8 = J8EncodeOne(p_in, p_out, j8_escape);
    if (invalid_utf8 && !j8_escape) {  // first JSON pass got binary data?
      return invalid_utf8;             // early return
    }
  }
  return 0;
}

inline int BashDollarEncodeChunk(unsigned char** p_in, unsigned char* in_end,
                                 unsigned char** p_out,
                                 unsigned char* out_end) {
  while (*p_in < in_end && (*p_out + J8_MAX_BYTES_PER_INPUT_BYTE) <= out_end) {
    BashDollarEncodeOne(p_in, p_out);
  }
  return 0;
}

inline int BourneShellEncodeChunk(unsigned char** p_in, unsigned char* in_end,
                                  unsigned char** p_out,
                                  unsigned char* out_end) {
  while (*p_in < in_end && (*p_out + J8_MAX_BYTES_PER_INPUT_BYTE) <= out_end) {
    int cannot_encode = BourneShellEncodeOne(p_in, p_out);
    if (cannot_encode) {     // we need escaping, e.g. \u0001 or \'
      return cannot_encode;  // early return
    }
  }
  return 0;
}

inline int CanOmitQuotes(unsigned char* s, int len) {
  for (int i = 0; i < len; ++i) {
    unsigned char ch = s[i];

    // Corresponds to regex [a-zA-Z0-9./_-]
    if ('a' <= ch && ch <= 'z') {
      continue;
    }
    if ('A' <= ch && ch <= 'Z') {
      continue;
    }
    if ('0' <= ch && ch <= '9') {
      continue;
    }
    if (ch == '.' || ch == '/' || ch == '_' || ch == '-') {
      continue;
    }
    // some byte requires quotes
    // Not including UTF-8 here because it can have chars that look like space
    // or quotes
    return 0;
  }
  return 1;  // everything OK
}

#endif  // DATA_LANG_J8_H
