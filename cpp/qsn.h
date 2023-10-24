// cpp/qsn.h

#ifndef QSN_H
#define QSN_H

#include "mycpp/runtime.h"

namespace qsn {

inline bool IsUnprintableLow(BigStr* ch) {
  assert(len(ch) == 1);
  uint8_t c = ch->data_[0];  // explicit conversion necessary
  return c < ' ';
}

inline bool IsUnprintableHigh(BigStr* ch) {
  assert(len(ch) == 1);
  // 255 should not be -1!
  // log("ch->data_[0] %d", ch->data_[0]);
  uint8_t c = ch->data_[0];  // explicit conversion necessary
  return c >= 0x7f;
}

inline bool IsPlainChar(BigStr* ch) {
  assert(len(ch) == 1);
  uint8_t c = ch->data_[0];  // explicit conversion necessary
  switch (c) {
  case '.':
  case '-':
  case '_':
    return true;
  }
  return ('a' <= c && c <= 'z') || ('A' <= c && c <= 'Z') ||
         ('0' <= c && c <= '9');
}

inline BigStr* XEscape(BigStr* ch) {
  assert(len(ch) == 1);
  BigStr* result = NewStr(4);
  sprintf(result->data(), "\\x%02x", ch->data_[0] & 0xff);
  return result;
}

inline BigStr* UEscape(int codepoint) {
  // maximum length:
  // 3 for \u{
  // 6 for codepoint
  // 1 for }
  BigStr* result = OverAllocatedStr(10);
  int n = sprintf(result->data(), "\\u{%x}", codepoint);
  result->MaybeShrink(n);  // truncate to what we wrote
  return result;
}

}  // namespace qsn

#endif  // QSN_H
