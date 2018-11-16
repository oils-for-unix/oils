#include <assert.h>
#include <stdarg.h>  // va_list, etc.
#include <stdio.h>
#include <stdint.h>
#include <stdlib.h>
#include <string.h>  // memcmp
#include <vector>
#include <unordered_map>

#include "opcode.h"

#define VERBOSE_OPS 0
#define VERBOSE_NAMES 0
#define VERBOSE_VALUE_STACK 0
#define VERBOSE_ALLOC 0  // for New*() functions

using std::vector;
using std::unordered_map;

typedef int32_t Handle;

typedef vector<Handle> Args;
typedef vector<Handle> Rets;

// Like enum why_code in ceval.c.
enum class Why {
  Not,
  Exception,
  Reraise,
  Return,
  Break,
  Continue,
  Yield,
};

enum CompareOp {
	LT,
	LE,
	EQ,
	NE,
	GT,
	GE,
	IS,
	IS_NOT,
};

//
// Forward declarations
//

class OHeap;

//
// Prototypes
//

Why func_print(const OHeap& heap, const Args& args, Rets* rets);

//
// Constants
//

// TODO: Generate this?
const int TAG_NONE = -1;
const int TAG_BOOL = -2;
const int TAG_INT = -3;
const int TAG_FLOAT = -4;
const int TAG_STR =  -5;
const int TAG_TUPLE = -6;
const int TAG_CODE = -7;
const int TAG_FUNC = -8;

// Should this be zero?  Positive are user defined, negative are native, 0 is
// invalid?  Useful for NewCell() to return on allocation failure.  And
// uninitialized handles should be in an invalid state.
const int kInvalidHandle = -10;

// TODO: These should be generated
const int kTrueHandle = -11;
const int kFalseHandle = -12;

const char* kTagDebugString[] = {
  "",
  "None",
  "bool",
  "int",
  "float",
  "str",
  "tuple",
  "code",
};

const char* TagDebugString(int tag) {
  return kTagDebugString[-tag];
}

//
// Utilities
//

// Log messages to stdout.
void log(const char* fmt, ...) {
  va_list args;
  va_start(args, fmt);
  vprintf(fmt, args);
  va_end(args);
  printf("\n");
}

// Implement hash and equality functors for unordered_map.
struct NameHash {
  int operator() (const char* s) const {
    // DJB hash: http://www.cse.yorku.ca/~oz/hash.html
    int h = 5381;

    while (char c = *s++) {
      h = (h << 5) + h + c;
    }
    return h;
  }
};

struct NameEq {
  bool operator() (const char* x, const char* y) const {
    return strcmp(x, y) == 0;
  }
};

// Dictionary of names (char*) to value (Handle).
//
// TODO: if we de-dupe all the names in OHeap, and there's no runtime code
// generation, each variable name string will have exactly one address.  So
// then can we use pointer comparison for equality / hashing?  Would be nice.
typedef unordered_map<const char*, Handle, NameHash, NameEq> NameLookup;


// 16 bytes
struct Cell {
  int16_t tag;
  uint8_t is_slab;
  uint8_t small_len;  // end first 4 bytes

  union {
    // following TWELVE bytes, for small string, tuple, etc.
    uint8_t small_val[1];
    int32_t big_len;  // length of slab.  TODO: Use this.
  };

  union {
    // The wire format
    struct {
      uint8_t pad[4];
      int32_t offset;
    } slab_wire;

    // Resolved memory format
    uint8_t* ptr;  // should be 8 bytes on 64-bit systems
    int64_t i;
    double d;
  };
};

// Same interface for big or small strings.
// What about hash code?  That could be stored with big strings.
struct Str {
  int32_t len;
  const char* data;  // NUL-terminated, but can also contain NUL.
                     // should not be mutated.
};

struct Tuple {
  int32_t len;
  const Handle* handles;
};


// Dicts require special consideration in these cases:
// - When deserializing, we have to create a new DictIndex from the DictItems
//   array.  We compute the size of the index from the number of items.
// - When garbage collecting, we iterate over DictItems and mark 'key' and
// 'value' Handles, skipping over the hash value.
//
// Another possibility: Why isn't the hash stored with the key itself rather
// than in the items array?  I guess it could be both.

struct DictIndex {
    int size;  // power of 2
    int num_used;  // is this the same as the number of items?
                   // For the load factor.

// The slab first has sparse indices, and then dense items, like CPython.

    // Using the same approach as CPython.  
    //
    // NOTE PyDict_MINSIZE == 8
    // "8 allows dicts with no more than 5 active entries; experiments suggested
    // this suffices for the majority of dicts (consisting mostly of
    // usually-small dicts created to pass keyword arguments)."
    // This is always a power of 2 (see dictresize() in dictobject.c).
    // So it goes 8, 16, 32 ...
    //
    // Optimization: DictIndex could be shared among different hash tables!
    // As long as they have the exact same set of keys.  But how would you
    // determine that?

    // Doesn't this produce a lot of unpredictable branches?  Maybe as a
    // compromise we could just use options for 2 bytes and 4 bytes?  Dicts up
    // to 2**32 should be fine.
/*
       The size in bytes of an indice depends on dk_size:

       - 1 byte if dk_size <= 0xff (char*)
       - 2 bytes if dk_size <= 0xffff (int16_t*)
       - 4 bytes if dk_size <= 0xffffffff (int32_t*)
       - 8 bytes otherwise (int64_t*)
*/
    union {
        int8_t as_1[8];
        int16_t as_2[4];
        int32_t as_4[2];
#if SIZEOF_VOID_P > 4
        int64_t as_8[1];
#endif
    } dk_indices;
};

struct DictSlab {
  // number of items is in Cell big_len
  int items_offset;  // offset to later in the slab?

  int indices_size;  // how many we can have without reallocating
  int indices_used;  //

};

struct DictItem {
  uint64_t hash;
  Handle key;
  Handle value;
};

// Wire format for dicts: a hole for the index, and then an array of DictItem.
struct DictSlabWire {
  union {
    uint8_t pad[8];
    DictIndex* index;
  };
  // DictItems here.  Length is stored in the cell?
};

class Code {
 public:
  Code(OHeap* heap, Cell* self) 
      : heap_(heap),
        self_(self) {
  }
  // Assume the pointers are patched below
  int64_t argcount() const {
    return FieldAsInt(1);
  }
  int64_t nlocals() const {
    return FieldAsInt(2);
  }
  int64_t stacksize() const {
    return FieldAsInt(3);
  }
  int64_t flags() const {
    return FieldAsInt(4);
  }
  int64_t firstlineno() const {
    return FieldAsInt(5);
  }
  Str name() const {
    return FieldAsStr(6);
  }
  Str filename() const {
    return FieldAsStr(7);
  }
  Str code() const {
    return FieldAsStr(8);
  }
  Tuple names() const {
    return FieldAsTuple(9);
  }
  Tuple varnames() const {
    return FieldAsTuple(10);
  }
  Tuple consts() const {
    return FieldAsTuple(11);
  }

 private:
  inline Handle GetField(int field_index) const {
    int32_t* slab = reinterpret_cast<int32_t*>(self_->ptr);
    return slab[field_index];
  }

  inline int64_t FieldAsInt(int field_index) const;
  inline Str FieldAsStr(int field_index) const;
  inline Tuple FieldAsTuple(int field_index) const;

  OHeap* heap_;
  Cell* self_;
};

// A convenient "view" on a function object.  To create a function, you create
// the cell and the slab directly!
//
// LATER: This may have a closure pointer too.
class Func {
 public:
  Func(OHeap* heap, Cell* self) 
      : heap_(heap),
        self_(self) {
  }
  // Code is copyable?
#if 0
  Code code() const {
    Handle h = 0;  // TODO: Field access for handle
    Code c(heap_, heap_->cells_ + h);
    return c;
  }
#endif
  Tuple defaults() const {
    Tuple t;
    return t;
    //return FieldAsTuple(1);
  }
  // Fields: code, globals, defaults, __doc__,
  // And note that we have to SET them too.

 private:
  OHeap* heap_;
  Cell* self_;
};

class OHeap {
 public:
  OHeap() : slabs_(nullptr), num_cells_(0), max_cells_(0), cells_(nullptr) {
  }

  ~OHeap() {
    if (slabs_) {
      free(slabs_);
    }
    if (cells_) {
      free(cells_);
    }
  }

  uint8_t* AllocPermanentSlabs(int total_slab_size) {
    slabs_ = static_cast<uint8_t*>(malloc(total_slab_size));
    return slabs_;
  }

  Cell* AllocInitialCells(int num_cells) {
    num_cells_ = num_cells;
    // Allocate 2x the number of cells to account for growth.
    //max_cells_ = num_cells * 2;
    max_cells_ = num_cells * 10;
    cells_ = static_cast<Cell*>(malloc(sizeof(Cell) * max_cells_));
    return cells_;
  }

  bool AsInt(Handle h, int64_t* out) const {
    assert(h >= 0);
    const Cell& cell = cells_[h];
    if (cell.tag != TAG_INT) {
      return false;
    }
    *out = cell.i;
    return true;
  }

  // C string.  NULL if the cell isn't a string.
  // NOTE: Shouldn't modify this?
  const char* AsStr0(Handle h) const {
    assert(h >= 0);
    const Cell& cell = cells_[h];
    if (cell.tag != TAG_STR) {
      log("AsStr0 expected string but got tag %d", cell.tag);
      return nullptr;
    }
    if (cell.is_slab) {
      int32_t* str_slab = reinterpret_cast<int32_t*>(cell.ptr);
      // everything after len
      return reinterpret_cast<const char*>(str_slab + 1);
    } else {
      return reinterpret_cast<const char*>(&cell.small_val);
    }
  }
  // Sets str and len.  Returns false if the Cell isn't a string.
  bool AsStr(Handle h, Str* out) const {
    assert(h >= 0);
    const Cell& cell = cells_[h];
    if (cell.tag != TAG_STR) {
      return false;
    }
    if (cell.is_slab) {
      int32_t* str_slab = reinterpret_cast<int32_t*>(cell.ptr);
      out->len = *str_slab;
      // everything after len
      out->data = reinterpret_cast<const char*>(str_slab + 1);
    } else {
      out->len = cell.small_len;  // in bytes
      out->data = reinterpret_cast<const char*>(&cell.small_val);
    }
    return true;
  }

  bool AsTuple(Handle h, Tuple* out) {
    assert(h >= 0);
    const Cell& cell = cells_[h];
    if (cell.tag != TAG_TUPLE) {
      return false;
    }
    if (cell.is_slab) {
      int32_t* tuple_slab = reinterpret_cast<int32_t*>(cell.ptr);
      out->len = *tuple_slab;
      // everything after len
      out->handles = reinterpret_cast<const Handle*>(tuple_slab + 1);
    } else {
      out->len = cell.small_len;  // in entries
      out->handles = reinterpret_cast<const Handle*>(&cell.small_val);
    }
    return true;
  };

  // TODO: How do we bounds check?
  Code AsCode(Handle h) {
    assert(h >= 0);
    log("tag = %d", cells_[h].tag);
    assert(cells_[h].tag == TAG_CODE);
    return Code(this, cells_ + h);
  }

  // Returns whether the value is truthy, according to Python's rules.
  // Should we unify this with the bool() constructor?
  bool Truthy(Handle h) {
    assert(h >= 0);
    const Cell& cell = cells_[h];
    switch (cell.tag) {
    case TAG_NONE:
      return false;
    case TAG_BOOL:
      return cell.i != 0;  // True or False
    case TAG_INT:
      return cell.i != 0;  // nonzero
    case TAG_FLOAT:
      return cell.d != 0.0;  // Is this correct?
    case TAG_STR: {
      Str s;
      AsStr(h, &s);
      return s.len != 0;
    }
    case TAG_TUPLE:
      assert(0);  // TODO
      break;
    case TAG_CODE:
      return true;  // always truthy

    // NOTE: Instances don't get to override nonzero?  They are always true.

    default:
      assert(0);  // TODO
    }
  }

  // For now just append to end.  Later we have to look at the free list.
  Handle NewCell() {
    // TODO: Should we reserve handle 0 for NULL, an allocation failure?  The
    // file format will bloat by 16 bytes?
    if (num_cells_ == max_cells_) {
      log("Allocation failure: num_cells_ = %d", num_cells_);
      assert(0);
    }
    return num_cells_++;
  }

  // TODO: append to cells_.
  // Zero out the 16 bytes first, and then set cell.i?
  Handle NewInt(int64_t i) {
    Handle h = NewCell();
    memset(cells_ + h, 0, sizeof(Cell));
    cells_[h].tag = TAG_INT;
    cells_[h].i = i;
#if VERBOSE_ALLOC
    log("new int <id = %d> %d", h, i);
#endif
    return h;
  }
  Handle NewStr0(const char* s) {
    Handle h = NewCell();
    memset(cells_ + h, 0, sizeof(Cell));
    cells_[h].tag = TAG_STR;

    // TODO: Determine if its big or small.
    assert(0);
    return h;
  }

  Handle NewTuple(int initial_size) {
    assert(0);
    return kInvalidHandle;
  }

  Handle NewFunc(Handle code, NameLookup* globals) {
    Handle h = NewCell();
    memset(cells_ + h, 0, sizeof(Cell));
    cells_[h].tag = TAG_FUNC;

    // NOTE: This should be a Cell because we want to freeze it!

    // This sould be a pointer to a slab.  TODO: So we need a function to
    // allocate a slab with 3 fields?  code, globals, defaults are essential.
    // THen it could be small.
    //
    // BUT we also want a docstring?  That will be useful for running some code.
    // So it needs to be a slab.
    //
    // Should there be indirection with "globals"?  It should be its own handle?
    // Yes I think it's a handle to an entry of sys.modules?

    cells_[h].ptr = nullptr;

    assert(0);
    return kInvalidHandle;
  }

  int Last() {
    return num_cells_ - 1;
  }

  void DebugString(Handle h) {
    const Cell& cell = cells_[h];

    fprintf(stderr, "  <id %d> ", h);

    switch (cell.tag) {
    case TAG_NONE:
      log("None");
      break;
    case TAG_BOOL:
      log("Bool");
      break;
    case TAG_INT: {
      int64_t i;
      AsInt(h, &i);
      log("Int %d", i);
      break;
    }
    case TAG_FLOAT:
      log("Float");
      break;
    case TAG_STR:
      log("Str %s", AsStr0(h));
      break;
    default:
      log("%s", TagDebugString(cell.tag));
    }
  }

  // Getter
  inline Cell* cells() {
    return cells_;
  }
 private:
  uint8_t* slabs_;  // so we can free it, not used directly
  int num_cells_;
  int max_cells_;
  Cell* cells_;
};


//
// Code implementation.  Must come after OHeap declaration.
//

inline int64_t Code::FieldAsInt(int field_index) const {
  Handle h = GetField(field_index);
  int64_t i;
  assert(heap_->AsInt(h, &i));  // invalid bytecode not handled
  return i;
}

inline Str Code::FieldAsStr(int field_index) const {
  Handle h = GetField(field_index);

  Str s;
  assert(heap_->AsStr(h, &s));  // invalid bytecode not handled
  return s;
}

inline Tuple Code::FieldAsTuple(int field_index) const {
  Handle h = GetField(field_index);

  Tuple t;
  assert(heap_->AsTuple(h, &t));  // invalid bytecode not handled
  return t;
}

//
// File I/O
//

const char* kHeader = "OHP2";
const int kHeaderLen = 4;

bool ReadHeader(FILE* f) {
  char buf[kHeaderLen];
  if (fread(buf, kHeaderLen, 1, f) != 1) {
    log("Couldn't read OHeap header");
    return false;
  }
  if (memcmp(buf, kHeader, kHeaderLen) != 0) {
    log("Error: expected '%s' in OHeap header", kHeader);
    return false;
  }
  return true;
}

bool Load(FILE* f, OHeap* heap) {
  if (!ReadHeader(f)) {
    return false;
  }

  int32_t total_slab_size = 0;
  if (fread(&total_slab_size, sizeof total_slab_size, 1, f) != 1) {
    log("Error reading total_slab_size");
    return false;
  }
  log("total_slab_size = %d", total_slab_size);

  int32_t num_cells = 0;
  if (fread(&num_cells, sizeof num_cells, 1, f) != 1) {
    log("Error reading num_cells");
    return false;
  }
  log("num_cells = %d", num_cells);

  int32_t num_read;

  // TODO: Limit total size of slabs?
  uint8_t* slabs = heap->AllocPermanentSlabs(total_slab_size);
  num_read = fread(slabs, 1, total_slab_size, f);
  if (num_read != total_slab_size) {
    log("Error reading slabs");
    return false;
  }

  size_t pos = ftell(f);
  log("pos after reading slabs = %d", pos);

  Cell* cells = heap->AllocInitialCells(num_cells);
  num_read = fread(cells, sizeof(Cell), num_cells, f);
  if (num_read != num_cells) {
    log("Error: expected %d cells, got %d", num_cells, num_read);
    return false;
  }

  // Patch the offsets into pointers.
  int num_slabs = 0;
  for (int i = 0; i < num_cells; ++i) {
    const Cell& cell = cells[i];
    if (cell.is_slab) {
      num_slabs++;
      int32_t slab_offset = cell.slab_wire.offset;
      //log("i = %d, slab offset = %d", i, slab_offset);
      cells[i].ptr = slabs + slab_offset;
      //log("ptr = %p", cell.ptr);
    }
  }
  log("Patched %d slabs", num_slabs);

  // Print out all the slab lengths for verification.
  for (int i = 0; i < num_cells; ++i) {
    const Cell& cell = cells[i];
    if (cell.is_slab) {
      //log("i = %d", i);
      //log("ptr = %p", cell.ptr);
      int32_t* start = reinterpret_cast<int32_t*>(cell.ptr);
      //log("start = %p", start);
      int32_t len = *start;
      log("slab len = %d", len);
    }
  }

  return true;
}

enum class BlockType : uint8_t {
  Loop,
  Except,
  Finally,
  With,
};

// Like PyTryBlock in frameobject.h
struct Block {
  BlockType type;
  uint8_t level;  // VALUE stack level to pop to.
  uint16_t jump_target;  // Called 'handler' in CPython.
};

class Frame {
 public:
  // TODO: Reserve the right size for these stacks?
  // from co.stacksize
  Frame(const Code& co) 
      : co_(co),
        value_stack_(),
        block_stack_(),
        last_i_(0),
        globals_(),
        locals_() {
  }
  // Take the handle of a string, and return a handle of a value.
  Handle LoadName(const char* name) {
#if VERBOSE_NAMES
    log("-- Looking up %s", name);
#endif

    auto it = locals_.find(name);
    if (it != locals_.end()) {
      return it->second;
    }

    if (strcmp(name, "print") == 0) {
      return -1;  // special value for a C function?
    }

    return 0;  // should this be a specal value?
  }
  void StoreName(const char* name, Handle value_h) {
    locals_[name] = value_h;
  }
  inline void JumpTo(int dest) {
    last_i_ = dest;
  }
  inline void JumpRelative(int offset) {
    last_i_ += offset;  // Is this correct?
  }
  const Code& co_;  // public for now
  vector<Handle> value_stack_;
  vector<Block> block_stack_;
  int last_i_;  // index into bytecode (which is variable length)
  NameLookup globals_;
 private:
  NameLookup locals_;
};

class VM {
 public:
  VM(OHeap* heap) 
      : heap_(heap) {
  }
  ~VM() {
    for (auto* frame : call_stack_) {
      delete frame;
    }
  }

  // Like PyEval_EvalFrameEx.  It has to be on the VM object in order to create
  Why RunFrame(Frame* frame);

  // Treat the last object on the heap as a code object to run.
  Why RunMain();

 private:
  void DebugHandleArray(const vector<Handle>& handles);

  OHeap* heap_;
  vector<Frame*> call_stack_;  // call stack
  Handle modules;  // like sys.modules.  A dictionary of globals.

  // See PyThreadState for other stuff that goes here.
  // Exception info, profiling, tracing, counters, etc.

  // PyInterpreterState: modules, sysdict, builtins, module reloading
  // OVM won't have overridable builtins.
};

void VM::DebugHandleArray(const vector<Handle>& handles) {
  printf("(%zu) [ ", handles.size());
  for (Handle h : handles) {
    printf("%d ", h);
  }
  printf("]\n");

  printf("    [ ");
  for (Handle h : handles) {
    if (h < 0) {
      printf("(native) ");
    } else {
      int tag = heap_->cells()[h].tag;
      printf("%s ", TagDebugString(tag));
    }
  }
  printf("]\n");

}

void CodeDebugString(const Code& co, OHeap* heap) {
  log("argcount = %d", co.argcount());
  log("nlocals = %d", co.nlocals());
  log("stacksize = %d", co.stacksize());
  log("flags = %d", co.flags());
  log("firstlineno = %d", co.firstlineno());

  log("name = %s", co.name().data);
  log("filename = %s", co.filename().data);
  log("len(code) = %d", co.code().len);

  log("len(names) = %d", co.names().len);
  log("len(varnames) = %d", co.varnames().len);
  Tuple consts = co.consts();

  log("len(consts) = %d", consts.len);

  log("consts {");
  for (int i = 0; i < consts.len; ++i) {
    heap->DebugString(consts.handles[i]);
  }
  log("}");
  log("-----");
}

Why VM::RunFrame(Frame* frame) {
  const Code& co = frame->co_;

  Tuple names = co.names();
  //Tuple varnames = co.varnames();
  Tuple consts = co.consts();

  vector<Handle>& value_stack = frame->value_stack_;
  vector<Block>& block_stack = frame->block_stack_;

  CodeDebugString(co, heap_);  // Show what code we're running.

  Why why = Why::Not;
  Handle retval = kInvalidHandle;

  Str b = co.code();
  int code_len = b.len;
  const uint8_t* bytecode = reinterpret_cast<const uint8_t*>(b.data);

  int inst_count = 0;

  while (true) {
    assert(0 <= frame->last_i_);
    assert(frame->last_i_ < code_len);

    uint8_t op = bytecode[frame->last_i_];
    int oparg;
    frame->last_i_++;
#if VERBOSE_OPS
    printf("%20s", kOpcodeNames[op]);
#endif

    if (op >= HAVE_ARGUMENT) {
      int i = frame->last_i_;
      oparg = bytecode[i] + (bytecode[i+1] << 8);
#if VERBOSE_OPS
      printf(" %5d (last_i_ = %d)", oparg, i);
      if (oparg < 0) {
        log(" oparg bytes: %d %d", bytecode[i], bytecode[i+1]);
      }
#endif
      frame->last_i_ += 2;
    }
#if VERBOSE_OPS
    printf("\n");
#endif

    switch(op) {
    case LOAD_CONST:
      //log("load_const handle = %d", consts.handles[oparg]);
      // NOTE: bounds check?
      value_stack.push_back(consts.handles[oparg]);
      break;
    case LOAD_NAME: {
      Handle name_h = names.handles[oparg];
      const char* name = heap_->AsStr0(name_h);
      assert(name != nullptr);  // Invalid bytecode not handled

      //log("load_name handle = %d", names.handles[oparg]);
      Handle h = frame->LoadName(name);
      value_stack.push_back(h);
      break;
    }
    case STORE_NAME: {
      Handle name_h = names.handles[oparg];
      const char* name = heap_->AsStr0(name_h);
      assert(name != nullptr);  // Invalid bytecode not handled

      frame->StoreName(name, value_stack.back());
      value_stack.pop_back();
      break;
    }
    case POP_TOP:
      value_stack.pop_back();
      break;
    case CALL_FUNCTION: {
      int num_args = oparg & 0xff;
      //int num_kwargs = (oparg >> 8) & 0xff;  // copied from CPython
      //log("num_args %d", num_args);

#if VERBOSE_VALUE_STACK
      log("value stack on CALL_FUNCTION");
      DebugHandleArray(value_stack);
#endif

      vector<Handle> args;
      args.reserve(num_args);  // reserve the right size

      // Pop num_args off.  TODO: Could print() builtin do this itself to avoid
      // copying?
      for (int i = 0; i < num_args; ++i ) {
        args.push_back(value_stack.back());
        value_stack.pop_back();
      }
#if VERBOSE_VALUE_STACK
      log("Popped args:");
      DebugHandleArray(args);

      log("Value stack after popping args:");
      DebugHandleArray(value_stack);
#endif

      // Pop the function itself off
      Handle func_handle = value_stack.back();
      value_stack.pop_back();

      //log("func handle %d", func_handle);

      vector<Handle> rets;
      if (func_handle < 0) {
        // TODO: dispatch table for native functions.
        // Call func_print for now.

        why = func_print(*heap_, args, &rets);
        if (why != Why::Not) {
          log("EXCEPTION after calling native function");
          break;
        }
      } else {
        //Func func;  // has CodeObject and more?
        //heap_->AsFunc(func_handle, &func);
        //CallFunction(func, args, &rets);
        rets.push_back(0);
      }

      // Now push return values.
      assert(rets.size() == 1);
      value_stack.push_back(rets[0]);
      break;
    }

    // Computation
    case COMPARE_OP: {
      Handle w = value_stack.back();
      value_stack.pop_back();
      Handle v = value_stack.back();
      value_stack.pop_back();

      // CPython inlines cmp(int, int) too.
      int64_t a, b;
      bool result;
      if (heap_->AsInt(v, &a) && heap_->AsInt(w, &b))  {
        switch (oparg) {
        case CompareOp::LT: result = a <  b; break;
        case CompareOp::LE: result = a <= b; break;
        case CompareOp::EQ: result = a == b; break;
        case CompareOp::NE: result = a != b; break;
        case CompareOp::GT: result = a >  b; break;
        case CompareOp::GE: result = a >= b; break;
        //case CompareOp::IS: result = v == w; break;
        //case CompareOp::IS_NOT: result = v != w; break;
        default:
          log("Unhandled compare %d", oparg);
          assert(0);
        }
        // TODO: Avoid stack movement by SET_TOP().

        // Use canonical handles rather than allocating bools.
        value_stack.push_back(result ? kTrueHandle : kFalseHandle);
      } else {
        assert(0);
      }
      break;
    }

    case BINARY_ADD: {
      Handle w = value_stack.back();
      value_stack.pop_back();
      Handle v = value_stack.back();
      value_stack.pop_back();

      int64_t a, b, result;
      if (heap_->AsInt(w, &a) && heap_->AsInt(v, &b))  {
        result = a + b;
      } else {
        // TODO: Concatenate strings, tuples, lists
        assert(0);
      }

      Handle result_h = heap_->NewInt(result);
      value_stack.push_back(result_h);
      break;
    }

    case BINARY_MODULO: {
      Handle w = value_stack.back();
      value_stack.pop_back();
      Handle v = value_stack.back();
      value_stack.pop_back();

      Str s;
      if (heap_->AsStr(v, &s)) {
        // TODO: Do string formatting
        assert(0);
      }

      int64_t a, b, result;
      if (heap_->AsInt(v, &a) && heap_->AsInt(w, &b)) {
        result = a % b;
        Handle result_h = heap_->NewInt(result);
        value_stack.push_back(result_h);
        break;
      }

      // TODO: TypeError
      assert(0);

      break;
    }

    // 
    // Jumps
    //
    case JUMP_ABSOLUTE:
      frame->JumpTo(oparg);
      break;

    case JUMP_FORWARD:
      frame->JumpRelative(oparg);
      break;

    case POP_JUMP_IF_FALSE: {
      Handle w = value_stack.back();
      value_stack.pop_back();

      // Special case for Py_True / Py_False like CPython.
      if (w == kTrueHandle) {
        break;
      }
      if (w == kFalseHandle || !heap_->Truthy(w)) {
        frame->JumpTo(oparg);
      }
      break;
    }

    //
    // Control Flow
    //

    case SETUP_LOOP: {
      Block b;
      b.type = BlockType::Loop;
      b.level = value_stack.size();
      b.jump_target = frame->last_i_ + oparg;  // oparg is relative jump target
      block_stack.push_back(b);
      break;
    }

    case POP_BLOCK:
      block_stack.pop_back();
      break;

    case BREAK_LOOP:
      why = Why::Break;
      break;

    case RETURN_VALUE:
      // TODO: Set return value here.  It's just a Handle I guess.
      retval = value_stack.back();
      value_stack.pop_back();
      why = Why::Return;
      break;

    case MAKE_FUNCTION: {
      Handle code = value_stack.back();
      value_stack.pop_back();
      // TODO: default arguments are on the stack.
      if (oparg) {
        //Handle defaults = heap_->NewTuple(oparg);  // initial size
        for (int i = 0; i < oparg; ++i) {
          value_stack.pop_back();
        }
      }
      // the function is run with the same globals as the frame it was defined in
      NameLookup* globals = &frame->globals_;
      Handle func = heap_->NewFunc(code, globals);
      value_stack.push_back(func);
    }

    default:
      log("Unhandled instruction");
      break;

    }

    while (why != Why::Not && block_stack.size()) {
      assert(why != Why::Yield);
      Block b = block_stack.back();

      // TODO: This code appears to be unused!  continue compiles as
      // POP_JUMP_IF_FALSE!
      if (b.type == BlockType::Loop && why == Why::Continue) {
        assert(0);
        // TODO: retval?  I guess it's popped off the stack.
        frame->JumpTo(retval);
      }
      block_stack.pop_back();

      // Unwind value stack to the saved level.
      while (value_stack.size() > b.level) {
        value_stack.pop_back();
      }

      if (b.type == BlockType::Loop && why == Why::Break) {
        why = Why::Not;
        frame->JumpTo(b.jump_target);
      }

      if (b.type == BlockType::Finally ||
          b.type == BlockType::Except && why == Why::Exception ||
          b.type == BlockType::With) {
        assert(0);
      }
    }

    // TODO: Handle the block stack.  Break should JUMP to the location in the
    // block handler!
    if (why != Why::Not) {  // return, yield, continue, etc.
      break;
    }
    inst_count++;
  }

  log("Processed %d instructions", inst_count);
  return why;
}

Why VM::RunMain() {
  Code co = heap_->AsCode(heap_->Last());

  Frame* frame = new Frame(co);
  call_stack_.push_back(frame);

  log("co = %p", co);

  return RunFrame(frame);
}

// Need a VM to be able to convert args to Cell?
Why func_print(const OHeap& heap, const Args& args, Rets* rets) {
  Str s;
  if (heap.AsStr(args[0], &s)) {
    //printf("PRINTING\n");
    fwrite(s.data, sizeof(char), s.len, stdout);  // make sure to write NUL bytes!
    puts("\n");

    // This is like Py_RETURN_NONE?
    rets->push_back(0);
    return Why::Not;
  }

  // TODO: We should really call the str() constructor here, which will call
  // __str__ on user-defined instances.
  int64_t i;
  if (heap.AsInt(args[0], &i)) {
    printf("%ld\n", i);

    rets->push_back(0);
    return Why::Not;
  }

  // TODO: Set TypeError
  // I guess you need the VM argument here.
  return Why::Exception;
}

int main(int argc, char **argv) {
  if (argc == 0) {
    log("Expected filename\n");
    return 1;
  }
  FILE *f = fopen(argv[1], "rb");
  if (!f) {
    log("Error opening %s", argv[1]);
    return 1;
  }

  assert(sizeof(Cell) == 16);

  OHeap heap;
  if (!Load(f, &heap)) {
    log("Error loading '%s'", argv[1]);
    return 1;
  }

  VM vm(&heap);
  vm.RunMain();
  return 0;
}
