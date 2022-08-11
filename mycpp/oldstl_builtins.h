
class Str;

inline Str* chr(int i) {
  char* buf = static_cast<char*>(malloc(2));
  buf[0] = i;
  buf[1] = '\0';
  return CopyBufferIntoNewStr(buf, 1);
}

inline int ord(Str* s) {
  assert(len(s) == 1);
  // signed to unsigned conversion, so we don't get values like -127
  uint8_t c = static_cast<uint8_t>(s->data_[0]);
  return c;
}

inline Str* str(int i) {
  char* buf = static_cast<char*>(malloc(kIntBufSize));
  int len = snprintf(buf, kIntBufSize, "%d", i);
  return CopyBufferIntoNewStr(buf, len);
}

inline Str* str(double f) {  // TODO: should be double
  NotImplemented();          // Uncalled
}

// mycpp doesn't understand dynamic format strings yet
inline Str* dynamic_fmt_dummy() {
  /* NotImplemented(); */
  return StrFromC("dynamic_fmt_dummy");
}
