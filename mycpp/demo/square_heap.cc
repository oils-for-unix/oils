// Target language test for Bitmap Marking GC.
//
// Instead of pointers, we'll use pool IDs everywhere.
//
// GOOD:
// - Better memory utilization, especially cache utilization
// - It's cheaper to pass small objects by value
// - Garbage collector is fork()-friendly
//
// BAD:
// - This subverts the C++ type system.  You have reinterpret_cast<> on every
//   field access.
// - It makes the generated code much less readable.  Although it can probably
//   be improved with macros.

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

typedef uint32_t Cell4[4];
typedef uint32_t Cell8[8];
typedef uint32_t Cell16[16];

Cell4* gBase4;
Cell8* gBase8;
Cell16* gBase16;

// TODO:
// pool_id && 0x11 =
//   00 for gBase4
//   01 for gBase8
//   10 for gBase16
//   11 for gBase32
//
// This is the dynamic homogeneous graph on top of the static heterogeneous
// graph.  So the mark process knows where to go.
//
// TODO: look at production quality mark-and-sweep?  Python doesn't have it
// and mark-sweep does a naive Lisp cons-cell.  Maybe look at OCaml.

// These are arrays of mark bits parallel to arrays of cells.
//
// NOTE:
// - Micro Python uses 2 bits per cell
// - oscar uses one bit
//   - hm it doesn't store free bits?  it has a LAZY SWEEP.
//   - I don't think I want that because I want lists, arrays, dicts to be
//   freed upon pool.MarkAndSweep().

uint8_t* gMark4;
uint8_t* gMark8;
uint8_t* gMark16;

struct Slab {
  uint8_t type;  // for the mark process to know what to follow
  uint8_t pad[3];
  int length;
  char* base;
};

typedef uint32_t pool_id_t;

// Slices refer to slabs.  They are like pointers.
// Could this be 8 bytes?  Or does it have a capacity too like Go?
struct Slice {
  uint8_t type;  // for the mark process to know what to follow
  uint8_t pad[3];
  int length;
  pool_id_t slab;
  uint8_t pad2[4];
};

// Macros that make generated code less ugly
// Others will use gBase8, etc.

#define _Slab(id) (reinterpret_cast<Slab*>(gBase4 + id))
#define _Slice(id) (reinterpret_cast<Slice*>(gBase4 + id))

// These are all the same, but make the code more readable.
typedef uint32_t SlabRef;
typedef uint32_t SliceRef;

// Or can you use Handle<Slab> and Handle<Slice> that holds a single uint32_t?
// And then overload operator *?  Actually that's a good idea and maybe it's
// what v8 does.

// TODO:
// - makeSlab() -> bump allocate into gBase4 and return ID with 00
// - makeList() -> bump allocate into gBase8 and return ID with 01

// The garbage collector doesn't statically know the types.

int main(int argc, char** argv) {
  log("heap.cc");
  log("sizeof(Slab) = %d", sizeof(Slab));
  log("sizeof(Slice) = %d", sizeof(Slice));
  // 8 bytes.
  log("sizeof(size_t) = %d", sizeof(size_t));

  gBase4 = new Cell4[10];
  int slab = 5;  // pool ID returned by alloc

  // This is a test for a bitmap marking GC.  We could simplify this with
  // macros.
  //
  // I think this is not too different tha Micro Python's solution.

  // slab.length = 20
  (reinterpret_cast<Slab*>(gBase4 + slab))->length = 20;

  int slice = 6;
  (reinterpret_cast<Slice*>(gBase4 + slice))->slab = slab;

  // print(slab.length)
  log("length = %d", (reinterpret_cast<Slab*>(gBase4 + slab))->length);

  // print(slab.length)
  log("slab = %d", (reinterpret_cast<Slice*>(gBase4 + slice))->slab);

  SlabRef slab2 = 7;
  _Slab(slab2)->length = 30;
  log("length of slab2 = %d", _Slab(slab2)->length);
}
