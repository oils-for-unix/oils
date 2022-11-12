// cpp/qsn.h

#ifndef QSN_H
#define QSN_H

#include "mycpp/runtime.h"

namespace qsn {

inline bool IsUnprintableLow(Str* ch) {
  assert(len(ch) == 1);
  return ch->data_[0] < ' ';
}

inline bool IsUnprintableHigh(Str* ch) {
  assert(len(ch) == 1);
  return ch->data_[0] >= 0x7f;
}

inline bool IsPlainChar(Str* ch) {
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
  RootingScope _r;
  assert(len(ch) == 1);
  StackRoots _roots({&ch});
  Str* result = NewStr(4);
  sprintf(result->data(), "\\x%02x", ch->data_[0] & 0xff);
  gHeap.RootOnReturn(result);
  return result;
}

inline Str* UEscape(int codepoint) {
  // maximum length:
  // 3 for \u{
  // 6 for codepoint
  // 1 for }
  RootingScope _r;
  Str* result = OverAllocatedStr(10);
  int n = sprintf(result->data(), "\\u{%x}", codepoint);
  result->SetObjLenFromStrLen(n);  // truncate to what we wrote
  gHeap.RootOnReturn(result);
  return result;
}

}  // namespace qsn

#endif  // QSN_H
