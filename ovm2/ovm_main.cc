#include <assert.h>
#include <stdarg.h>  // va_list, etc.
#include <stdio.h>
#include <stdint.h>
#include <stdlib.h>
#include <string.h>  // memcmp
#include <vector>
#include <unordered_map>

#include "opcode.h"

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

// TODO: Generate this?
const int TAG_NONE = -1;
const int TAG_BOOL = -2;
const int TAG_INT = -3;
const int TAG_FLOAT = -4;
const int TAG_STR =  -5;
const int TAG_TUPLE = -6;
const int TAG_CODE = -7;

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

class Code {
 public:
  Code(OHeap* heap, Cell* self) 
      : heap_(heap),
        self_(self) {
  }
  inline int64_t FieldAsInt(int field_index) const;
  inline Str FieldAsStr(int field_index) const;
  inline Tuple FieldAsTuple(int field_index) const;

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
  OHeap* heap_;
  Cell* self_;
};

class OHeap {
 public:
  OHeap() : slabs_(nullptr), num_cells_(0), cells_(nullptr) {
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
    // Allocate double the amount to account for growth.
    // TODO: Store this and realloc.
    int max_cells = num_cells * 2;
    cells_ = static_cast<Cell*>(malloc(sizeof(Cell) * max_cells));
    return cells_;
  }

  // C string.  NULL if the cell isn't a string.
  // NOTE: Shouldn't modify this?
  const char* AsStr0(Handle h) const {
    const Cell& cell = cells_[h];
    if (cell.tag != TAG_STR) {
      log("AsStr0 expected string but got tag %d", cell.tag);
      return nullptr;
    }
    if (cell.is_slab) {
      int32_t* str_slab = reinterpret_cast<int32_t*>(cell.ptr);
      return reinterpret_cast<const char*>(str_slab + 1);  // everything after len
    } else {
      return reinterpret_cast<const char*>(&cell.small_val);
    }
  }
  // Sets str and len.  Returns false if the Cell isn't a string.
  bool AsStr(Handle h, Str* out) const {
    const Cell& cell = cells_[h];
    if (cell.tag != TAG_STR) {
      return false;
    }
    if (cell.is_slab) {
      int32_t* str_slab = reinterpret_cast<int32_t*>(cell.ptr);
      out->len = *str_slab;
      out->data = reinterpret_cast<const char*>(str_slab + 1);  // everything after len
    } else {
      out->len = cell.small_len;  // in bytes
      out->data = reinterpret_cast<const char*>(&cell.small_val);
    }
    return true;
  }

  bool AsTuple(Handle h, Tuple* out) {
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


  bool AsInt(Handle h, int64_t* out) {
    const Cell& cell = cells_[h];
    if (cell.tag != TAG_INT) {
      return false;
    }
    *out = cell.i;
    return true;
  }

  // TODO: How do we bounds check?
  Code AsCode(Handle h) {
    log("tag = %d", cells_[h].tag);
    assert(cells_[h].tag == TAG_CODE);
    return Code(this, cells_ + h);
  }

  // Returns whether the value is truthy, according to Python's rules.
  bool Truthy(Handle h) {
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

  // TODO: append to cells_.
  // Zero out the 16 bytes first, and then set cell.i?
  Handle NewInt(int64_t i) {
    //Cell* cell = new
    return 0;
  }
  // TODO: Determine if its big or small.
  Handle NewStr0(const char* s) {
    return 0;
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
  Cell* cells_;
};

//
// Code implementation.  Must come after OHeap declaration.
//

inline int64_t Code::FieldAsInt(int field_index) const {
  int32_t* slab = reinterpret_cast<int32_t*>(self_->ptr);
  Handle h = slab[field_index];

  int64_t i;
  assert(heap_->AsInt(h, &i));  // invalid bytecode not handled
  return i;
}

inline Str Code::FieldAsStr(int field_index) const {
  int32_t* slab = reinterpret_cast<int32_t*>(self_->ptr);
  Handle h = slab[field_index];

  Str s;
  assert(heap_->AsStr(h, &s));  // invalid bytecode not handled
  return s;
}

inline Tuple Code::FieldAsTuple(int field_index) const {
  int32_t* slab = reinterpret_cast<int32_t*>(self_->ptr);
  Handle h = slab[field_index];

  Tuple t;
  assert(heap_->AsTuple(h, &t));  // invalid bytecode not handled
  return t;
}


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

enum class BlockType {
  Loop,
  Except,
  Finally,
  With,
};

// Like PyTryBlock in frameobject.h
struct Block {
  BlockType type;
  int level;  // stack level
  int handler;  // jump address.  TODO: Rename?
};

// Implement hash and equality functors for unordered_set.
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


// Is there a simple implementation for char* ?
typedef unordered_map<const char*, Handle, NameHash, NameEq> NameLookup;

class Frame {
 public:
  // TODO: Reserve the right size for these stacks?
  // from co.stacksize
  Frame(const Code& co, const OHeap& heap) 
      : co_(co),
        heap_(heap),
        value_stack_(),
        block_stack_(),
        locals_(),
        last_i_(0) {
  }
  // Take the handle of a string, and return a handle of a value.
  Handle LoadName(const char* name) {
    log("-- Looking up %s", name);

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
  void JumpTo(int dest) {
    last_i_ = dest;
  }
  void JumpForward(int offset) {
    last_i_ += offset;  // Is this correct?
  }
  void PushBlock(BlockType type) {
  };
  void PopBlock() {
  };

  const Code& co_;  // public for now
  vector<Handle> value_stack_;
  vector<Block> block_stack_;
 private:
  // TODO: We might not need this?
  const OHeap& heap_;

  // How do we use the default hash?
  // TODO: if we de-dupe all the names in OHeap, and there's no runtime code
  // generaetion, each variable name string will have exactly one address.  So
  // then can we use pointer comparison for equality / hashing?  Would be nice.
  NameLookup locals_;
  int last_i_;
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

  // See PyThreadState for other stuff that goes here.
  // Exception info, profiling, tracing, counters, etc.

  // PyInterpreterState: modules, sysdict, builtins, module reloading
  // OVM won't have overridable builtins.
};

void VM::DebugHandleArray(const vector<Handle>& handles) {
  printf("(%d) [ ", handles.size());
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

Why VM::RunFrame(Frame* frame) {
  const Code& co = frame->co_;

  vector<Handle>& value_stack = frame->value_stack_;
  // TODO: Cache other locals here too

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
  Tuple names = co.names();
  Tuple varnames = co.varnames();
  Tuple consts = co.consts();

  log("len(consts) = %d", consts.len);

  log("consts {");
  for (int i = 0; i < consts.len; ++i) {
    heap_->DebugString(consts.handles[i]);
  }
  log("}");

  Why why = Why::Not;

  int num_bytes = co.code().len;
  const char* bytecode = co.code().data;

  int i = 0;
  int n = 0;

  while (i < num_bytes) {
    uint8_t op = bytecode[i];
    int oparg;
    i++;
    printf("%20s", kOpcodeNames[op]);

    if (op >= HAVE_ARGUMENT) {
      oparg = bytecode[i] + bytecode[i+1]*256;
      printf(" %5d", oparg);
      i += 2;
    }
    printf("\n");

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
      int num_kwargs = (oparg >> 8) & 0xff;  // copied from CPython
      log("num_args %d", num_args);

      log("value stack on CALL_FUNCTION");
      DebugHandleArray(value_stack);

      vector<Handle> args;
      args.reserve(num_args);  // reserve the right size

      // Pop num_args off.  TODO: Could print() builtin do this itself to avoid
      // copying?
      for (int i = 0; i < num_args; ++i ) {
        args.push_back(value_stack.back());
        value_stack.pop_back();
      }
      log("Popped args:");
      DebugHandleArray(args);

      log("Value stack after popping args:");
      DebugHandleArray(value_stack);

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
      int64_t a, b, result;
      if (heap_->AsInt(w, &a) && heap_->AsInt(v, &b))  {
        switch (oparg) {
        case CompareOp::LT: result = a <  b; break;
        case CompareOp::LE: result = a <= b; break;
        case CompareOp::EQ: result = a == b; break;
        case CompareOp::NE: result = a != b; break;
        case CompareOp::GT: result = a >  b; break;
        case CompareOp::GE: result = a >= b; break;
        //case CompareOp::IS: result = v == w; break;
        //case CompareOp::IS_NOT: result = v != w; break;
        }
        // TODO: Avoid stack movement by SET_TOP().

        // TODO: Turn result into Py_True or Py_False.
        // Do those have canonical handles?  Maybe -1 and -2?
        value_stack.push_back(0);
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
        assert(0);
      }

      Handle result_h = heap_->NewInt(result);
      value_stack.push_back(result_h);
      break;
    }

    // 
    // Jumps
    //
    case JUMP_ABSOLUTE:
      frame->JumpTo(oparg);
      break;

    case JUMP_FORWARD:
      frame->JumpForward(oparg);
      break;

    case POP_JUMP_IF_FALSE: {
      Handle w = value_stack.back();
      value_stack.pop_back();

      // TODO: Special case for Py_True / Py_False like CPython
      if (!heap_->Truthy(w)) {
        frame->JumpTo(oparg);
      }
      break;
    }

    //
    // Control Flow
    //

    case SETUP_LOOP:
      frame->PushBlock(BlockType::Loop);
      break;

    case POP_BLOCK:
      frame->PopBlock();
      break;

    case RETURN_VALUE:
      // TODO: Set return value here.  It's just a Handle I guess.
      why = Why::Return;
      break;

    }
    n++;
  }

  printf("Read %d instructions\n", n);
  return why;
}

Why VM::RunMain() {
  Code co = heap_->AsCode(heap_->Last());

  Frame* frame = new Frame(co, *heap_);
  call_stack_.push_back(frame);

  log("co = %p", co);

  return RunFrame(frame);
}

// Need a VM to be able to convert args to Cell?
Why func_print(const OHeap& heap, const Args& args, Rets* rets) {
  Str s;
  if (!heap.AsStr(args[0], &s)) {
    // TODO: Set TypeError
    // I guess you need the VM argument here.
    return Why::Exception;
  }

  //printf("PRINTING\n");
  fwrite(s.data, sizeof(char), s.len, stdout);  // make sure to write NUL bytes!
  puts("\n");

  // This is like Py_RETURN_NONE?
  rets->push_back(0);
  return Why::Not;
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

  log("cell = %d", sizeof(Cell));
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
