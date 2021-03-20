// qsn_qsn.h

#ifndef QSN_QSN_H
#define QSN_QSN_H

#if 1  // TODO: switch this off
#include "mylib.h"
#else
#include "mylib2.h"
#endif

namespace qsn {

inline bool IsUnprintableLow(Str* ch) {
  assert(ch->len_ == 1);
  return ch->data_[0] < ' ';
}

inline bool IsUnprintableHigh(Str* ch) {
  assert(ch->len_ == 1);
  return ch->data_[0] >= 0x7f;
}

inline bool IsPlainChar(Str* ch) {
  assert(ch->len_ == 1);
  uint8_t c = ch->data_[0];
  switch (c) {
  case '.':
  case '-':
  case '_':
    return true;
  }
  return ('a' <= c && c <= 'z') || ('A' <= c && c <= 'Z') ||
         ('0' <= c && c <= '9');
}

inline Str* XEscape(Str* ch) {
  assert(ch->len_ == 1);
  char* buf = static_cast<char*>(malloc(4 + 1));
  sprintf(buf, "\\x%02x", ch->data_[0] & 0xff);
  return new Str(buf);
}

inline Str* UEscape(int codepoint) {
  // maximum length: 3 + 6 + 1 + NUL == 11
  char* buf = static_cast<char*>(malloc(10 + 1));
  sprintf(buf, "\\u{%x}", codepoint);
  return new Str(buf);
}

}  // namespace qsn

#endif  // QSN_QSN_H
