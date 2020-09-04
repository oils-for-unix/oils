// Simplest garbage collector that will work.
//
// It's a semi-space collector.  (Later we could add a "large object space",
// managed by mark-and-sweep after each copy step.)
//
// TODO:
// - Slab and Sheet
// - Str that shares Slabs, List, Dict
//
// - List.append() can realloc
// - Hook up alloactors.  new()?
//   - but Slab and Sheet can't use that.

#include <cstdarg>  // va_list, etc.
#include <cstdio>   // vprintf
#include <cstdint>  // max_align_t

void log(const char* fmt, ...) {
  va_list args;
  va_start(args, fmt);
  vprintf(fmt, args);
  va_end(args);
  puts("");
}

namespace Tag {
  const int Forwarded = 1;
}

class Managed {
  uint16_t tag;  // disjoint from ASDL tags
                 // is forward

  int how_to_trace;  // can be directly encoded, or it's an index into a table
};

class Forwarded : public Managed {
  // only valid if tag == Tag::Forwarded
  Managed* new_location;
};

// Opaque slab.  e.g. for String data
class Slab : public Managed {
 public:
  Slab() 
      : opaque("foobar") {
  }
  char opaque[8];  // minimum string capacity
};

// Building block for Dict and List.  Or is this List itself?
// Note: it's not managed with 'new'?
class Sheet : public Managed {
 public:
  Managed* pointers_[4];  // minimum List<Str*> capacity
};

class Str : public Managed {
 public:
  Str(Slab* slab, int begin, int end)
      : slab(slab), begin(begin), end(end) {
  }
  // Note: later this can be an atom_id
  Slab* slab;
  int begin;
  int end;
  int hash;
};

void Print(Str* s) {
  char* data = s->slab->opaque;
  char* p = data + s->begin;
  fwrite(p, 1, s->end - s->begin, stdout);
  puts("");
}

template <class T>
class List : public Managed {
 public:
  union {
    Slab* slab;  // List<int>
    Sheet* sheet;  // List<Str*>
  };
};

template <class K, class V>
class Dict : public Managed {
 public:
  Slab* indices;  // indexed by hash value
  union {
    Slab* keys_slab;  // Dict<int, V>
    Sheet* keys_sheet;  // Dict<Str*, V>
  };
  union {
    Slab* values_slab;  // Dict<K, int>
    Sheet* values_sheet;  // Dict<K, Str*>
  };
};

int len(const Str* s) {
  return 3;
}

template <typename T>
int len(const List<T>* L) {
  return 4;
}

template <typename K, typename V>
inline int len(const Dict<K, V>* d) {
  return 5;
}

int main(int argc, char** argv) {
  log("simple_gc");


  // hm this shouldn't be allocated with 'new'
  // it needs a different interface
  auto slab1 = new Slab();

  auto str1 = new Str(slab1, 2, 5);

  Print(str1);
  log("len(str1) = %d", len(str1));

  auto list1 = new List<int>();
  auto list2 = new List<Str*>();

  log("len(list1) = %d", len(list1));
  log("len(list2) = %d", len(list2));

  auto dict1 = new Dict<int, int>();
  auto dict2 = new Dict<Str*, Str*>();

  log("len(dict1) = %d", len(dict1));
  log("len(dict2) = %d", len(dict2));
}
