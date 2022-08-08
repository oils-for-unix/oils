#ifndef MYLIB_TYPES_H
#define MYLIB_TYPES_H

#ifdef OLDSTL_BINDINGS

#else



#endif

// NOTE(Jesse): The python that translates to osh_eval.cc relies on these
// functions being inside this namespace, so we have to live with these.


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
    return ::StrFromC(buf, len);
  }

  inline Str* hex_upper(int i) {
    char* buf = static_cast<char*>(malloc(kIntBufSize));
    int len = snprintf(buf, kIntBufSize, "%X", i);
    return ::StrFromC(buf, len);
  }

  inline Str* octal(int i) {
    char* buf = static_cast<char*>(malloc(kIntBufSize));
    int len = snprintf(buf, kIntBufSize, "%o", i);
    return ::StrFromC(buf, len);
  }

  // Used by generated _build/cpp/osh_eval.cc
  inline Str* StrFromC(const char* s) {
    return ::StrFromC(s);
  }

  template <typename V>
  void dict_remove(Dict<Str*, V>* haystack, Str* needle);

  template <typename V>
  void dict_remove(Dict<int, V>* haystack, int needle);


  Tuple2<Str*, Str*> split_once(Str* s, Str* delim);


  // NOTE(Jesse): This should be able to be taken out of here ..?  I think.
  template <typename T>
  List<T>* NewList() {
    return new List<T>();
  }

  // NOTE(Jesse): This should be able to be taken out of here ..?  I think.
  template <typename T>
  List<T>* NewList(std::initializer_list<T> init) {
    return new List<T>(init);
  }


} // namespace mylib

#endif // MYLIB_TYPES_H
