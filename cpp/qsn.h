// cpp/qsn.h

#ifndef QSN_H
#define QSN_H

#include "mycpp/runtime.h"

namespace qsn {

inline bool IsUnprintableLow(Str* ch) {
  NO_ROOTS_FRAME(FUNC_NAME);  // no allocations

  assert(len(ch) == 1);
  return ch->data_[0] < ' ';
}

inline bool IsUnprintableHigh(Str* ch) {
  NO_ROOTS_FRAME(FUNC_NAME);  // no allocations

  assert(len(ch) == 1);
  // 255 should not be -1!
  // log("ch->data_[0] %d", ch->data_[0]);
  unsigned char c = static_cast<unsigned char>(ch->data_[0]);
  return c >= 0x7f;
}

inline bool IsPlainChar(Str* ch) {
  NO_ROOTS_FRAME(FUNC_NAME);  // no allocations

  assert(len(ch) == 1);
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
  NO_ROOTS_FRAME(FUNC_NAME);  // skip to NewStr

  assert(len(ch) == 1);
  Str* result = NewStr(4);
  sprintf(result->data(), "\\x%02x", ch->data_[0] & 0xff);
  return result;
}

inline Str* UEscape(int codepoint) {
  NO_ROOTS_FRAME(FUNC_NAME);  // skip to OverAllocatedStr

  // maximum length:
  // 3 for \u{
  // 6 for codepoint
  // 1 for }
  Str* result = OverAllocatedStr(10);
  int n = sprintf(result->data(), "\\u{%x}", codepoint);
  result->SetObjLenFromStrLen(n);  // truncate to what we wrote
  return result;
}

}  // namespace qsn

#endif  // QSN_H
