// Demo for Garbage Collection.
//
// Design goals:
//
// - Simple and correct.  Hopefully 500-1000 lines of code.  The GC policy
//   headers seem like the most complicated bit.
// - Portable.  Built on top of realloc() / free(), not anything lower level.
// - Works with native pointers.  No "object tables" for now.
// - Arbitrarily sized heap.  The heap can't be an array.
// - Reasonably fast.
// - fork() friendly.  Mutation should be limited in order to facilitate page
//   sharing.
//
// Why not mark and sweep:
// - The simplest design wants to use the system allocator.  Measured to be
//   slower.
// - Bitmap marking hard to do without "object tables".
// - Object header is probably bigger (the heap turns into a linked list, if
//   you want it to be arbitrarily sized)
//
// Why not reference counting:
// - The only idea I have is the shared_ptr one.  It makes the code less
//   readable for debuggers, and seems like a dead end in terms of performance.
// - Also it's not fork() friendly because there is more mutation of object
//   headers.  Merely referencing an object mutates it.
//
// Downsides to copying GC (most likely solution)
// - In theory, it has double the space usage.  Counterarguments:
//   - Objects headers should be smaller, and Oil has lots of tiny objects
//   - Page sharing due to being fork() friendly
//   - Copying collectors eliminate fragmentation
//   - Later optimization: I think we can partition the heap into moving small
//     objects and non-moving malloc'd "slabs".  Slabs are owned by small
//     objects.  They are a "large object space".  (I think Slabs can be
//     managed by mark and sweep?  They will have mark bits and a "next"
//     pointer in their header.)
// - Breadth-first reduces locality of parents and children.  This seems like
//   it will matter, but there are some approxiately depth-first algorithms
//   we could try out later.  It would be cool if GC can improve locality!
//
// Performance goal / benchmark:
// - configure-coreutils can be parsed in ~250 ms on a slow machine, and ~90 ms
//   on a fast machine.  Copy-collecting that heap should take less time,
//   hopefully 2x or 5x less.
// - Also, parsing will slow down because of the object header size increase.
//   Goal: shouldn't be slower than bash.  (This depends how many collections
//   we do though!)
//
// Copying GC Parameters
// - Initial size of from space and to space
// - Growth policy: collect when it's 90% full?  or 100%?  Then increase space
//   by 2x?
//
// Object Model:
//   By Value: integer, Slice, Tuple (multiple return value)
//   By Reference: Structs (data/enum), List, Dict, Str
//
// Version 1, no deallocators:
//   Use Str (first-class object) and Array (on-heap)
// Version 2, with deallocators:
//   Use Slice (a kind of "pointer") and Slab (off-heap)
//
// GC policy tag
//
// how_to_trace =
//   Slab(uint16_t len, uint16_t capacity),  -- opaque, for string data, and
//   also List<int> Sheet(uint16_t len, uint16_t capacity),  -- for List<Str*>*
// | Record(uint16_t bitmap)  -- for inheritance
//                               for the fixed schema of Str, List, Dict
//                            -- the last 1 encodes the length
//                            -- isn't that an interview trick?
//                            -- highest bit
// | BigData(int external_strategy)  -- for large strings and arrays
//
//   -- later: if we want to sort fields.  It might make them pack better --
//   sort 32-bit integers before 64-bit pointers?
//   -- for ASDL types, for Str (1)
//   -- also the vectors underlying List and Dict??  Unless we do destructors.
// | PointerPrefix(int num_pointers, int len)
//
// Idea for capacity of Slab/Sheet
//   - Starts at 4
//   - Then it's the next power of 2 above len?  So 5 -> 8, 8 -> 16, 9 -> 16,
//   etc.
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
// TODO:
// - test out new Str() vs. the vector constructor
// - test out double indirection
// - encode how_to_trace in object header
// - figure out how to call the destructors -- DEFERRED
// - figure out std::vector vs. another GC slab?  vector does not have Managed
//   header -- DONE, using Array
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

#include <assert.h>
#include <stdarg.h>  // va_list, etc.
#include <stdio.h>   // vprintf
#include <string.h>  // strcmp

#include <cstddef>  // max_align_t
#include <initializer_list>
#include <stdexcept>
#include <vector>

void log(const char* fmt, ...) {
  va_list args;
  va_start(args, fmt);
  vprintf(fmt, args);
  va_end(args);
  printf("\n");
}

// 400 MiB of memory
char kMem[400 << 20];

int gMemPos = 0;
int gNumNew = 0;
int gNumDelete = 0;

#define DUMB_ALLOC 1

#ifdef DUMB_ALLOC

#include "cpp/aligned.h"

void* operator new(size_t size) {
  char* p = &(kMem[gMemPos]);
  fprintf(stderr, "new %zu\n", size);
  gMemPos += aligned(size);
  ++gNumNew;
  return p;
}

void operator delete(void* p) noexcept {
  fprintf(stderr, "\tdelete %p\n", p);
  ++gNumDelete;
}
#endif

#if 0
union Header {
  uint16_t tag;        // for ASDL sum types
                       // and other stuff too?

  uint32_t how_to_trace;  // how should we scan this object?
                       // how long is it?
};
#endif

class Managed {
#if 0  // mark and sweep
  Header header;
  Managed* next;
#endif

  uint16_t tag;  // disjoint from ASDL tags
                 // is forward

  int how_to_trace;  // can be directly encoded, or it's an index into a table
};

// only valid if tag == FORWARDED
// reinterpret_cast to this type
class Forwarded {
  uint16_t tag;
  Managed* forwarded;
};

struct Space {
  const char* heap;  // small objects to scan

  // List of destructors to call?  This is a little weird.
  // - List OWNS 1 vector, and has to destroy it.
  // - Dict OWNS 3 vectors, and has to destroy them.
  //
  // In contrast, Slice does NOT own the slab.  ASDL types don't have
  // destructors.  They are plain data.

  // Alternative: create your own vector with header?
  // Dict is made of headers?
  //
  // Just use realloc().  Except the data has to be on the heap.
  // Yeah how do you grow something on the GC heap.  I guess you just copy
  // it to a new location
  // Hm for this reason I like having separate slabs.
  //
  // Problem: these containers can have forwarding pointers!!!
  // List<Str*>* has to be modified

  // How do we determine which slabs we need to free?
  // We need to free the ones that were NOT moved to the other space.
  // TODO: First pass can avoid this by putting EVERYTHING on the same heap.
  // We will copy 70 MiB for configure-coreutils.  Would be nice to get that
  // down though.  TODO: write a microbenchmark for how long that takes?
  // Parse that AST and traverse it and copy it?
  const char* deallocators;

  // TODO:
  // scan pointer
  // next pointer
};

// Problem: can you have a max array / string size of uint16_t?
// I guess they can use a different tracing strategy in that case.  The
// "Custom" one

// Opaque slab.  e.g. for String data
class Slab : public Managed {
  char opaque[8];  // minimum string capacity
};

// Building block for Dict and List.  Or is this List itself?
// Note: it's not managed with 'new'?
class Sheet : public Managed {
  Managed* pointers_[4];  // minimum List<Str*> capacity
};

// Indexed by slab ID.  free() these individually?
std::vector<const char*> slabs;

Space* gFromSpace;
Space* gToSpace;

// DEFERRED until version 2
class Slice_2 {  // value type, not managed
 public:
  int slab_id_;  // index
  int atom_id_;  // for fast equality testing
  int start_;
  int len_;
};

// Idea for FAST STRING KEY LOOKUP with Atom table:
//
// A Str or Slice_2 does NOT store a hash value.  And it doesn't store the
// contents either.
//
// Instead the atom table is a HASH SET (a little like hash table)
//
// Another use case: Producing NUL terminated strings!

class AtomEntry {
 public:
  int hash;  // hash value for initial comparison, then linear probing
  int len;
  const char* data;  // We OWN a COPY of this data now, never freed!

  // Store the age here?  Then we prune entries from the table when it gets
  // big.  (Or do it based on size?)  They can always be recreated from the Str
  // or Slice object.
};

class AtomTable {
 public:
  int Intern(Slice_2 slice) {
    // TODO(Jesse): Does this get called?
    // Is this NotImplemented() or InvalidCodePath() ??
    assert(0);
  }

  std::vector<int> indices;        // like a hash_set
  std::vector<AtomEntry> entries;  // indexed by
};

// Interface:
//
// auto s = new Str(...)
// auto s2 = s->slice(1);  // derive a string
// auto s3 = s->slice(0, -2);  // derive another string
//
// int id2 = gAtoms.Intern(s2)
// int id3 = gAtoms.Intern(s2)
//
// Now id2 == id2 IF AND ONLY IF they are equal.  This is NOT true for a hash
// value!
//
// Whenever a Str or Slice is used as a key, it gets its atom_id key filled in.
//
// Str* s;  // may not be NUL termianted
// getenv(gAtoms.Str0(s));  // cache it
//
// Both Intern() and Str0() MUTATE the slice by adding the atom_id.

// We're going to start out with this reference type.
class Str : public Managed {
 public:
  Str(const char* data) : data_(data) {
  }

  // TODO: This should change to a Array reference?
  // It has to point to the header of the object!

  const char* data_;  // problem: how is this freed?
                      // two solutions:
                      // - no sharing: zero length array so it's "inline"
                      // - sharing, with its own GC header.
                      //   - So both Str instances and Slab instances are
                      //     on the to/from space
                      //     This works but causes more GC pressure
  int len_;
  int hash_;
};

template <class T>
class List : public Managed {
 public:
  List() : v_() {
  }
  List(std::initializer_list<T> init) : v_() {
    for (T item : init) {
      v_.push_back(item);
    }
  }

  // Problem: nontrivial destructor needs to be called when switching spaces
  ~List() {
    log("Destroying List");
  }

  std::vector<T> v_;
};

// Using Python's representation
// https://mail.python.org/pipermail/python-dev/2012-December/123028.html

template <class K, class V>
class Dict : public Managed {
 public:
  // Problem: nontrivial destructor needs to be called when switching spaces
  ~Dict() {
    log("Destroying Dict");
  }

  // -1 for invalid
  // Dict<int> doesn't need to use this at all?  It coudl just use a linear
  // search.
  std::vector<int> indices_;

  // I think parallel arrays are easier to scan, rather a single array like
  // Python's PyDictEntry.
  std::vector<K> keys_;
  std::vector<V> values_;
};

void f() {
  Str* s = StrFromC("foo");
  Str* s2 = StrFromC("bar");

  log(s->data_);
  log(s2->data_);

  // How do we make these roots?
  auto mylist = new List<Str*>({s, s2});
}

int main(int argc, char** argv) {
  if (argc == 2) {
    // how many allocations are there?  which allocators are used
    if (strcmp(argv[1], "allocator") == 0) {
      auto mylist = new List<int>();  //{1, 2, 3});

      // BAD: this causes another allocation via new().  Because we're using
      // std::vector.
      //
      // Options:
      // 1. malloc() is the lower layer, and new is the higher
      // 2. auto list = make_gc<List<int>>({1,2,3})
      //    This is like make_shared.
      //    Should it use templates or macros?
      mylist->v_.push_back(1);

      return 0;
    }

    int num_objects = atoi(argv[1]);
    log("num_objects = %d", num_objects);

    int size = 1000000 / num_objects;
    for (int i = 0; i < num_objects; ++i) {
      void* p = malloc(size);
    }
    return 0;
  }

  log("gc_containers.cc");

  // log("sizeof(Header) = %d", sizeof(Header));
  log("sizeof(Managed) = %d", sizeof(Managed));

  log("sizeof(Str) = %d", sizeof(Str));
  log("sizeof(Slice_2) = %d", sizeof(Slice_2));

  // log("sizeof(Array) = %d", sizeof(Array));

  // 40 bytes:
  // 16 byte managed + 24 byte vector = 40
  log("sizeof(List<int>) = %d", sizeof(List<int>));
  log("sizeof(List<Str*>) = %d", sizeof(List<Str*>));

  // 64 bytes:
  // 16 byte managed + 2 24 byte vectors
  log("sizeof(Dict<int, Str*>) = %d", sizeof(Dict<int, Str*>));
  log("sizeof(Dict<Str*, Str*>) = %d", sizeof(Dict<Str*, Str*>));

  f();

  List<int> mylist;
  Dict<Str*, int> mydict;
  log("mylist = %p", &mylist);

  // We probably don't want destructors -- I think we just want plain functions
  // That are registered with the heap space
  log("Manually calling destructor...");
  mylist.~List<int>();
}
