// Simplest garbage collector that will work.
//
// It's a semi-space collector.  (Later we could add a "large object space",
// managed by mark-and-sweep after each copy step.)
//
// TODO:
// - Immutable Slab, Sheet, and Str
// - Mutable List, Dict that point to Slab/Sheet
//
// - List.append() can realloc
// - Hook up alloactors.  new()?
//   - but Slab and Sheet can't use that.
//
// - How do you make it cooperate with ASAN?
//   - zero length arrays?

#include <cstdarg>  // va_list, etc.
#include <cstdint>  // max_align_t
#include <cstdio>   // vprintf
#include <cstring>  // memcpy

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

// This forces an 8-byte Cell header.  It's better not to have special cases
// like the "how_index" at first.
//
// It may be possible to enforce a limit of 2^24 = 16 MiB on strings and
// arrays.  But let's treat that as an optimization for later.
//
// We don't want to break code like x=$(cat big_file)
typedef uint32_t how_t;

class Cell {
  // The unit of garbage collection.  It has a header describing how to find
  // the pointers within it.
  //
  // (Note: sorting ASDL fields by (non-pointer, pointer) is a good idea, but
  //  it breaks down because mycpp has inheritance.  Could do this later.)

 public:
  Cell() : tag(0), cell_len_(0) {
  }
  Cell(int tag) : tag(tag), cell_len_(0) {
  }

  void SetCellLength(int len) {
    this->cell_len_ = cell_len_;
  }

  uint16_t tag;  // ASDL tags are 0 to 255
                 // Tag::Forwarded is 256?
                 // We could also reserve tags for Str, List, and Dict
                 // Then do we have 7 more bits for the GC strategy / length?

  // How to trace fields in this object.
  union {
    how_t cell_len_;   // # bytes to copy, or # bytes to scan?
    how_t field_mask;  // last 1 bit determines length
                       // so maximum 31 fields?
  };
};

class Forwarded : public Cell {
  // only valid if tag == Tag::Forwarded
  Cell* new_location;
};

// Opaque slab.  e.g. for String data
class Slab : public Cell {
 public:
  Slab() : opaque_("foobar") {
  }
  char opaque_[8];  // minimum string cell_len_
};

// Building block for Dict and List.  Or is this List itself?
// Note: it's not managed with 'new'?
class Sheet : public Cell {
 public:
  Cell* pointers_[4];  // minimum List<Str*> cell_len_
};

// NOT USED.  This object is too big, and it complicates the GC.
class Slice : public Cell {
 public:
  Slice(Slab* slab, int begin, int end)
      : begin_(begin), end_(end), slab_(slab) {
  }
  int begin_;
  int end_;
  int hash_;
  // Note: later this can be an atom_id
  Slab* slab_;
};

// TODO: I think constructors should be private.
// Does "opaque" cause ASAN to complain?
class Str : public Cell {
 public:
  Str(const char* data) {
    int len = strlen(data);
    SetCellLength(len);
    this->len_ = len;
    memcpy(opaque_, data, len);
  }
  Str(const char* data, int len) {
    SetCellLength(len);
    memcpy(opaque_, data, len);
  }
  int len_;
  int unique_id_;   // index into intern table
  char opaque_[1];  // flexible array
};

void PrintSlice(Slice* s) {
  char* data = s->slab_->opaque_;
  char* p = data + s->begin_;
  fwrite(p, 1, s->end_ - s->begin_, stdout);
  puts("");
}

template <class T>
class List : public Cell {
 public:
  int len_;  // container length
  union {
    Slab* slab;    // List<int>
    Sheet* sheet;  // List<Str*>
  };
};

template <class K, class V>
class Dict : public Cell {
 public:
  int len_;       // container length
  Slab* indices;  // indexed by hash value
  union {
    Slab* keys_slab;    // Dict<int, V>
    Sheet* keys_sheet;  // Dict<Str*, V>
  };
  union {
    Slab* values_slab;    // Dict<K, int>
    Sheet* values_sheet;  // Dict<K, Str*>
  };
};

int len(const Str* s) {
  return s->len_;
}

template <typename T>
int len(const List<T>* L) {
  return L->len_;
}

template <typename K, typename V>
inline int len(const Dict<K, V>* d) {
  return d->len_;
}

int main(int argc, char** argv) {
  log("simple_gc");

  // hm this shouldn't be allocated with 'new'
  // it needs a different interface
  auto slab1 = new Slab();

  auto slice1 = new Slice(slab1, 2, 5);

  PrintSlice(slice1);

  auto str1 = new Str("");
  // auto str2 = new Str("buffer overflow?");
  // auto str2 = new Str("food");

  log("");
  log("len(str1) = %d", len(str1));
  // log("len(str2) = %d", len(str2));

  auto list1 = new List<int>();
  auto list2 = new List<Str*>();

  log("len(list1) = %d", len(list1));
  log("len(list2) = %d", len(list2));

  auto dict1 = new Dict<int, int>();
  auto dict2 = new Dict<Str*, Str*>();

  log("len(dict1) = %d", len(dict1));
  log("len(dict2) = %d", len(dict2));

  log("");

  // 24 = 4 + (4 + 4 + 4) + 8
  // Feels like a small string optimization here would be nice.
  log("sizeof(Str) = %d", sizeof(Str));
  // 16 = 4 + pad4 + 8
  log("sizeof(List) = %d", sizeof(List<int>));
  // 32 = 4 + pad4 + 8 + 8 + 8
  log("sizeof(Dict) = %d", sizeof(Dict<int, int>));
}
