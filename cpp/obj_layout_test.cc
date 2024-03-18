#include "_gen/core/runtime.asdl.h"  // Cell, etc
#include "_gen/frontend/syntax.asdl.h"
#include "vendor/greatest.h"

TEST sizeof_syntax() {
  // 40 bytes (after merging with line_span January 2023)
  // - Get rid of 'string val'
  // - Replace 'int line_id' with SourceLine
  // - Maybe recompute length on demand
  log("sizeof(Token) = %d", sizeof(syntax_asdl::Token));
  log("alignof(Token) = %d", alignof(syntax_asdl::Token));
  log("alignof(Token*) = %d", alignof(syntax_asdl::Token *));
  log("");

  // 2024-03 - both of these are 64 bytes
  log("sizeof(BracedVarSub) = %d", sizeof(syntax_asdl::BracedVarSub));
  log("sizeof(command::Simple) = %d", sizeof(syntax_asdl::command::Simple));
  log("");

  // Only 8 bytes
  log("sizeof(CompoundWord) = %d", sizeof(syntax_asdl::CompoundWord));

  // Reordered to be 16 bytes
  log("sizeof(runtime_asdl::Cell) = %d", sizeof(runtime_asdl::Cell));

  // 24 bytes: std::vector
  log("sizeof(List<int>) = %d", sizeof(List<int>));
  log("sizeof(List<BigStr*>) = %d", sizeof(List<BigStr *>));

  log("sizeof(Slab<int>) = %d", sizeof(Slab<int>));
  log("sizeof(Slab<BigStr*>) = %d", sizeof(Slab<BigStr *>));
  // Right after object header
  log("kSlabHeaderSize = %d", kSlabHeaderSize);

  // Unlike Python, this is -1, not 255!
  int mod = -1 % 256;
  log("mod = %d", mod);

  log("alignof(bool) = %d", alignof(bool));
  log("alignof(int) = %d", alignof(int));
  log("alignof(float) = %d", alignof(float));

  log("sizeof(BigStr) = %d", sizeof(BigStr));
  log("alignof(BigStr) = %d", alignof(BigStr));

  log("sizeof(BigStr*) = %d", sizeof(BigStr *));
  log("alignof(BigStr*) = %d", alignof(BigStr *));

  log("alignof(max_align_t) = %d", alignof(max_align_t));

  PASS();
}

// Doesn't really test anything
TEST sizeof_core_types() {
  log("");

  // 8 byte header
  log("sizeof(ObjHeader) = %d", sizeof(ObjHeader));
  // 8 + 128 possible entries
  // log("sizeof(LayoutFixed) = %d", sizeof(LayoutFixed));

  // 24 = 4 + (4 + 4 + 4) + 8
  // Feels like a small string optimization here would be nice.
  log("sizeof(BigStr) = %d", sizeof(BigStr));
  // 16 = 4 + pad4 + 8
  log("sizeof(List) = %d", sizeof(List<int>));
  // 32 = 4 + pad4 + 8 + 8 + 8
  log("sizeof(Dict) = %d", sizeof(Dict<int, int>));

#ifndef MARK_SWEEP
  int min_obj_size = sizeof(LayoutForwarded);
  int short_str_size = aligned(kStrHeaderSize + 1);

  log("kStrHeaderSize = %d", kStrHeaderSize);
  log("aligned(kStrHeaderSize + 1) = %d", short_str_size);
  log("sizeof(LayoutForwarded) = %d", min_obj_size);

  ASSERT(min_obj_size <= short_str_size);
#endif

#if 0
  char* p = static_cast<char*>(gHeap.Allocate(17));
  char* q = static_cast<char*>(gHeap.Allocate(9));
  log("p = %p", p);
  log("q = %p", q);
#endif

  // BigStr = 16 and List = 24.
  // Rejected ideas about slicing:
  //
  // - Use data[len] == '\0' as OWNING and data[len] != '\0' as a slice?
  //   It doesn't work because s[1:] would always have that problem
  //
  // - s->data == (void*)(s + 1)
  //   Owning string has the data RIGHT AFTER?
  //   Maybe works? but probably a bad idea because of GLOBAL BigStr instances.

  log("");
  log("sizeof(BigStr) = %zu", sizeof(BigStr));
  log("sizeof(List<int>) = %zu", sizeof(List<int>));
  log("sizeof(Dict<int, BigStr*>) = %zu", sizeof(Dict<int, BigStr *>));
  log("sizeof(Tuple2<int, int>) = %zu", sizeof(Tuple2<int, int>));
  log("sizeof(Tuple2<BigStr*, BigStr*>) = %zu",
      sizeof(Tuple2<BigStr *, BigStr *>));
  log("sizeof(Tuple3<int, int, int>) = %zu", sizeof(Tuple3<int, int, int>));

  PASS();
}

TEST slab_growth() {
  // TODO: All slabs should start out at 32

  auto li = Alloc<List<int>>();
  log("li->items_ %p", li->slab_);

  // At some point it moves
  for (int i = 0; i < 20; ++i) {
    li->append(42);
    int size = 8 + (sizeof(int) * li->capacity_);
    log("%2d. cap %2d, size %3d, li->slab_ %p", i, li->capacity_, size,
        li->slab_);
  }

  log("---");

  auto lp = Alloc<List<BigStr *>>();
  log("lp->items_ %p", lp->slab_);

  // At some point it moves
  for (int i = 0; i < 20; ++i) {
    lp->append(kEmptyString);
    int size = 8 + (sizeof(BigStr *) * lp->capacity_);
    log("%2d. cap %2d, size %3d, lp->slab_ %p", i, lp->capacity_, size,
        lp->slab_);
  }

  PASS();
}

TEST malloc_address_test() {
  struct timespec start, end;
  if (clock_gettime(CLOCK_PROCESS_CPUTIME_ID, &start) < 0) {
    FAIL("clock_gettime failed");
  }

  // glibc gives us blocks of 32 bytes!
  // 1. diff = -240
  // 2. diff = 94064
  // 3. diff = 32
  // 4. diff = 32
  // 5. diff = 32

  // tcmalloc has tighter packing!
  // 1. diff = -8
  // 2. diff = 32
  // 3. diff = 8
  // 4. diff = 8
  // 5. diff = 8

  // 2023-08: If I pass 4096, I get 4112, so 16 byte diff
  // 2023-08: If I pass 4080, I get 4096

  // int alloc_size = 24 * 682;  // 16368 is close to 16384 - 16 bytes again
  int alloc_size = 48 * 341;  // heap 2 is the same size

  // int alloc_size = 4080;
  // int alloc_size = 1;

#define NUM_ALLOCS 20
  char *p[NUM_ALLOCS];
  for (int i = 0; i < NUM_ALLOCS; ++i) {
    p[i] = static_cast<char *>(malloc(alloc_size));
    if (i != 0) {
      char *prev = p[i - 1];
      log("%2d. diff = %d", i, p[i] - prev);
    }
  }

  for (int i = 0; i < NUM_ALLOCS; ++i) {
    free(p[i]);
  }

  if (clock_gettime(CLOCK_PROCESS_CPUTIME_ID, &end) < 0) {
    FAIL("clock_gettime failed");
  }

  log("start %d %d", start.tv_sec, start.tv_nsec);
  log("end %d %d", end.tv_sec, end.tv_nsec);

  PASS();
}

GREATEST_MAIN_DEFS();

int main(int argc, char **argv) {
  gHeap.Init();

  GREATEST_MAIN_BEGIN();

  RUN_TEST(sizeof_syntax);
  RUN_TEST(sizeof_core_types);
  RUN_TEST(slab_growth);
  RUN_TEST(malloc_address_test);

  gHeap.CleanProcessExit();

  GREATEST_MAIN_END();
  return 0;
}
