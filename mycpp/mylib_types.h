#ifndef MYLIB_TYPES_H
#define MYLIB_TYPES_H

// https://stackoverflow.com/questions/3919995/determining-sprintf-buffer-size-whats-the-standard/11092994#11092994
// Notes:
// - Python 2.7's intobject.c has an erroneous +6
// - This is 13, but len('-2147483648') is 11, which means we only need 12?
// - This formula is valid for octal(), because 2^(3 bits) = 8
const int kIntBufSize = CHAR_BIT * sizeof(int) / 3 + 3;

namespace mylib
{
  inline Str* hex_lower(int i) {
    char* buf = static_cast<char*>(malloc(kIntBufSize));
    int len = snprintf(buf, kIntBufSize, "%x", i);
    return StrFromC(buf, len);
  }

  inline Str* hex_upper(int i) {
    char* buf = static_cast<char*>(malloc(kIntBufSize));
    int len = snprintf(buf, kIntBufSize, "%X", i);
    return StrFromC(buf, len);
  }

  inline Str* octal(int i) {
    char* buf = static_cast<char*>(malloc(kIntBufSize));
    int len = snprintf(buf, kIntBufSize, "%o", i);
    return StrFromC(buf, len);
  }
} // namespace mylib

#endif // MYLIB_TYPES_H
