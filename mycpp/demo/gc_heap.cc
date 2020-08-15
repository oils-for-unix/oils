// Test for Mark and Sweep GC.
//
// Issues:
// - homogeneous GC graph overlaid on typed heterogeneous object graph
//   - Object header
// - size of various types
// - hash value in Str
// - is Str a value type?
// - value.Str vs. Str
// - Token size
//
// Tags:
// 0 Str  -- don't collect?
// 1 List -- contiguous scanning of pointers
// 2 Dict -- scan key and value, but skip hash?
//        -- or you might need different tags for Dict<int> and Dict<Str*>
//
// 3 .. 200   : ASDL variants?
// 200 .. 255 : shared variants?

#include <stdarg.h>  // va_list, etc.
#include <stdio.h>   // vprintf

#include <initializer_list>
#include <vector>

#include <stdexcept>

void log(const char* fmt, ...) {
  va_list args;
  va_start(args, fmt);
  vprintf(fmt, args);
  va_end(args);
  printf("\n");
}

union Header {
  uint16_t tag;        // for ASDL sum types
                       // and other stuff too?

  uint32_t gc_policy;  // how should we can this object?
                       // how long is it?
};

class Managed {
  Header header;
  Managed* next;
};

class Str {
  const char* data_;
  int len_;
  int hash;
};

template <class T>
class List : public Managed {
  // private:
  std::vector<T> v_;  // ''.join accesses this directly
};

template <class K, class V>
class DictEntry {
  int hash;
  K key;
  V value;
};

// Using Python's representation
// https://mail.python.org/pipermail/python-dev/2012-December/123028.html

template <class K, class V>
class Dict : public Managed {
  // -1 for invalid
  std::vector<int> indices_;

  // This is scanned by the GC for objects.
  std::vector<DictEntry<K, V>> entries_;
};


int main(int argc, char** argv) {
  log("gc_heap.cc");

  log("sizeof(Header) = %d", sizeof(Header));
  log("sizeof(Managed) = %d", sizeof(Managed));

  log("sizeof(Str) = %d", sizeof(Str));

  log("sizeof(List<int>) = %d", sizeof(List<int>));
  log("sizeof(List<Str*>) = %d", sizeof(List<Str*>));

  log("sizeof(Dict<int, Str*>) = %d", sizeof(Dict<int, Str*>));
  log("sizeof(Dict<Str*, Str*>) = %d", sizeof(Dict<Str*, Str*>));
}
