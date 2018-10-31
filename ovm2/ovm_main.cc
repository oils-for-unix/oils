#include <assert.h>
#include <stdarg.h>  // va_list, etc.
#include <stdio.h>
#include <stdint.h>
#include <stdlib.h>
#include <string.h>  // memcmp
#include <vector>

#include "opcode.h"

using std::vector;

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

typedef int32_t Handle;

// 16 bytes
struct Cell {
  int16_t tag;
  uint8_t is_slab;
  uint8_t small_len;  // end first 4 bytes

  union {
    uint8_t small_val[1];  // following TWELVE bytes, for small string, tuple, etc.
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
  const uint8_t* data;  // NUL-terminated, but can also contain NUL.
                        // should not be mutated.
};

struct Tuple {
  int32_t len;
  const Handle* handles;
};

class Code {
 public:
  Code(Cell* cells, Handle self) 
      : cells_(cells),
        self_(cells + self) {
  }
  inline int64_t AsInt(int field_index) const {
    int32_t* slab = reinterpret_cast<int32_t*>(self_->ptr);
    Handle h = slab[field_index];
    assert(cells_[h].tag == TAG_INT);
    // TODO: small or big
    return cells_[h].i;
  }

  inline Str AsStr(int field_index) const {
    int32_t* slab = reinterpret_cast<int32_t*>(self_->ptr);
    Handle h = slab[field_index];
    assert(cells_[h].tag == TAG_STR);
    const Cell& cell = cells_[h];
    Str s;
    if (cells_[h].is_slab) {
      int32_t* str_slab = reinterpret_cast<int32_t*>(cell.ptr);
      s.len = *str_slab;
      s.data = reinterpret_cast<uint8_t*>(str_slab + 1);  // everything after len
    } else {
      s.len = cell.small_len;  // in bytes
      s.data = reinterpret_cast<const uint8_t*>(&cell.small_val);
    }
    return s;
  }

  inline Tuple AsTuple(int field_index) const {
    int32_t* slab = reinterpret_cast<int32_t*>(self_->ptr);
    Handle h = slab[field_index];
    assert(cells_[h].tag == TAG_TUPLE);
    const Cell& cell = cells_[h];
    Tuple t;
    if (cells_[h].is_slab) {
      int32_t* tuple_slab = reinterpret_cast<int32_t*>(cell.ptr);
      t.len = *tuple_slab;
      // everything after len
      t.handles = reinterpret_cast<const Handle*>(tuple_slab + 1);
    } else {
      t.len = cell.small_len;  // in entries
      t.handles = reinterpret_cast<const Handle*>(&cell.small_val);
    }
    return t;
  };

  // Assume the pointers are patched below
  int64_t argcount() const {
    return AsInt(1);
  }
  int64_t nlocals() const {
    return AsInt(2);
  }
  int64_t stacksize() const {
    return AsInt(3);
  }
  int64_t flags() const {
    return AsInt(4);
  }
  int64_t firstlineno() const {
    return AsInt(5);
  }
  Str name() const {
    return AsStr(6);
  }
  Str filename() const {
    return AsStr(7);
  }
  Str code() const {
    return AsStr(8);
  }
  Tuple names() const {
    return AsTuple(9);
  }
  Tuple varnames() const {
    return AsTuple(10);
  }
  Tuple consts() const {
    return AsTuple(11);
  }
 private:
  Cell* cells_;
  Cell* self_;
};

class OHeap {
 public:
  bool Init(uint8_t* slabs, int num_cells, Cell* cells) {
    slabs_ = slabs;
    num_cells_ = num_cells;
    cells_ = cells;
    return true;
  }
  // TODO: How do we bounds check?
  Code AsCode(Handle h) {
    log("tag = %d", cells_[h].tag);
    assert(cells_[h].tag == TAG_CODE);
    return Code(cells_, h);
  }
  int Last() {
    return num_cells_ - 1;
  }
  // TODO: Should these be allocated in the class for symmetry?
  ~OHeap() {
    free(slabs_);
    free(cells_);
  }
 private:
  uint8_t* slabs_;  // so we can free it, not used directly
  int num_cells_;
  Cell* cells_;
};

const char* kHeader = "OHP2";
const int kHeaderLen = 4;

bool ReadHeader(FILE* f) {
  char buf[kHeaderLen];
  if (fread(buf, kHeaderLen, 1, f) != 1) {
    log("Error reading magic number");
    return false;
  }
  if (memcmp(buf, kHeader, kHeaderLen) != 0) {
    log("Error: expected '%s'", kHeader);
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
  uint8_t* slabs = static_cast<uint8_t*>(malloc(total_slab_size));
  num_read = fread(slabs, 1, total_slab_size, f);
  if (num_read != total_slab_size) {
    log("Error reading slabs");
    return false;
  }

  size_t pos = ftell(f);
  log("pos after reading slabs = %d", pos);

  Cell* cells = static_cast<Cell*>(malloc(sizeof(Cell) * num_cells));
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

  heap->Init(slabs, num_cells, cells);
  return true;
}

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

class Frame {
 public:
  // TODO: Reserve the right size for these stacks?
  // from co.stacksize
  Frame(const Code& co) 
      : co_(co),
        value_stack_(),
        block_stack_() {
  }
  // Take the handle of a string, and return a handle of a value.
  Handle LoadName(Handle n) {
    return 0;
  }
  const Code& co_;  // public for now
  vector<Handle> value_stack_;
  vector<Block> block_stack_;
 private:
};


class VM {
 public:
  VM(OHeap* heap) 
      : heap_(heap) {
  }
  ~VM() {
    for (auto* f : call_stack_) {
      delete f;
    }
  }

  // Like PyEval_EvalFrameEx.  It has to be on the VM object in order to create
  Why RunFrame(Frame* frame);

  // Treat the last object on the heap as a code object to run.
  Why RunMain();

 private:
  OHeap* heap_;
  vector<Frame*> call_stack_;  // call stack

  // See PyThreadState for other stuff that goes here.
  // Exception info, profiling, tracing, counters, etc.

  // PyInterpreterState: modules, sysdict, builtins, module reloading
  // OVM won't have overridable builtins.
};

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
  log("len(consts) = %d", co.consts().len);

  Tuple names = co.names();
  Tuple varnames = co.varnames();
  Tuple consts = co.consts();

  Why why = Why::Not;

  int num_bytes = co.code().len;
  const uint8_t* bytecode = co.code().data;

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
      //log("load_name handle = %d", names.handles[oparg]);
      Handle h = frame->LoadName(names.handles[oparg]);
      value_stack.push_back(h);
      break;
    }
    case POP_TOP:
      value_stack.pop_back();
      break;
    case CALL_FUNCTION:
      // TODO: pop number of args.  Create a new frame, etc.
      break;
    case RETURN_VALUE:
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

  Frame* frame = new Frame(co);
  call_stack_.push_back(frame);

  log("co = %p", co);

  return RunFrame(frame);
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
    log("Error loading OHeap", argv[1]);
    return false;
  }

  VM vm(&heap);
  vm.RunMain();
  return 0;
}
