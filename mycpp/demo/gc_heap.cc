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
//
// Note: I think copying a copying GC has better locality, but it
// requires double indirection to do portably.  I don't think we need double
// indirection here, just some kind of HandleScope

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

  uint32_t gc_policy;  // how should we scan this object?
                       // how long is it?
};

class Managed {
#if 0  // mark and sweep
  Header header;
  Managed* next;
#endif

  uint16_t tag;
};

class Slice : public Managed {
 public:
  const char* data_;
  int start_;
  int len_;
  int hash_;

  // what about is_intern?  Are all strings interned?
  // problem: keying by a Slice: that means the slice itself has a hash, not
  // the underlying Slab.
};

// Hm 32 bytes if managed, 16 bytes otherwise!
//class Str {
class Str : public Managed {
 public:
  Str(const char* data) : data_(data) {
  }

  const char* data_;
  int len_;
  int hash;
};

template <class T>
class List : public Managed {
 public:
  List(std::initializer_list<T> init) : v_() {
    for (T item : init) {
      v_.push_back(item);
    }
  }

  std::vector<T> v_;
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

void f() {
  Str* s = new Str("foo");
  Str* s2 = new Str("bar");

  log(s->data_);
  log(s2->data_);

  // How do we make these roots?
  auto mylist = new List<Str*>({s, s2});
}

int main(int argc, char** argv) {
  if (argc == 2) {
    int num_objects = atoi(argv[1]);
    log("num_objects = %d", num_objects);

    int size = 1000000 / num_objects;
    for (int i = 0; i < num_objects; ++i) {
      void* p = malloc(size);
    }
    return 0;
  }
  log("gc_heap.cc");

  log("sizeof(Header) = %d", sizeof(Header));
  log("sizeof(Managed) = %d", sizeof(Managed));

  log("sizeof(Str) = %d", sizeof(Str));
  log("sizeof(Slice) = %d", sizeof(Slice));

  // 40 bytes:
  // 16 byte managed + 24 byte vector = 40
  log("sizeof(List<int>) = %d", sizeof(List<int>));
  log("sizeof(List<Str*>) = %d", sizeof(List<Str*>));

  // 64 bytes:
  // 16 byte managed + 2 24 byte vectors
  log("sizeof(Dict<int, Str*>) = %d", sizeof(Dict<int, Str*>));
  log("sizeof(Dict<Str*, Str*>) = %d", sizeof(Dict<Str*, Str*>));

  f();
}


