#ifndef MARKSWEEP_HEAP_H
#define MARKSWEEP_HEAP_H

#include <stdlib.h>

#include <vector>

#include "mycpp/common.h"
#include "mycpp/gc_obj.h"

class MarkSet {
 public:
  MarkSet() : bits_() {
  }

  // ReInit() must be called at the start of MarkObjects().  Allocate() should
  // keep track of the maximum object ID.
  void ReInit(int max_obj_id) {
    // https://stackoverflow.com/questions/8848575/fastest-way-to-reset-every-value-of-stdvectorint-to-0
    std::fill(bits_.begin(), bits_.end(), 0);
    int max_byte_index = (max_obj_id >> 3) + 1;  // round up
    // log("ReInit max_byte_index %d", max_byte_index);
    bits_.resize(max_byte_index);
  }

  // Called by MarkObjects()
  void Mark(int obj_id) {
    DCHECK(obj_id >= 0);
    // log("obj id %d", obj_id);
    DCHECK(!IsMarked(obj_id));
    int byte_index = obj_id >> 3;  // 8 bits per byte
    int bit_index = obj_id & 0b111;
    // log("byte_index %d %d", byte_index, bit_index);
    bits_[byte_index] |= (1 << bit_index);
  }

  // Called by Sweep()
  bool IsMarked(int obj_id) {
    DCHECK(obj_id >= 0);
    int byte_index = obj_id >> 3;
    int bit_index = obj_id & 0b111;
    return bits_[byte_index] & (1 << bit_index);
  }

  void Debug() {
    int n = bits_.size();
    dprintf(2, "[ ");
    for (int i = 0; i < n; ++i) {
      dprintf(2, "%02x ", bits_[i]);
    }
    dprintf(2, "] (%d bytes) \n", n);
    dprintf(2, "[ ");
    int num_bits = 0;
    for (int i = 0; i < n; ++i) {
      for (int j = 0; j < 8; ++j) {
        int bit = (bits_[i] & (1 << j)) != 0;
        dprintf(2, "%d", bit);
        num_bits += bit;
      }
    }
    dprintf(2, " ] (%d bits set)\n", num_bits);
  }

  std::vector<uint8_t> bits_;  // bit vector indexed by obj_id
};

// A simple Pool allocator for allocating small objects. It maintains an ever
// growing number of Blocks each consisting of a number of fixed size Cells.
// Memory is handed out one Cell at a time.
// Note: within the context of the Pool allocator we refer to object IDs as cell
// IDs because in addition to identifying an object they're also used to index
// into the Cell storage.
template <int CellsPerBlock, size_t CellSize>
class Pool {
 public:
  static constexpr size_t kMaxObjSize = CellSize;
  static constexpr int kBlockSize = CellSize * CellsPerBlock;

  Pool() = default;

  void* Allocate(int* obj_id) {
    num_allocated_++;

    if (!free_list_) {
      // Allocate a new Block and add every new Cell to the free list.
      Block* block = static_cast<Block*>(malloc(sizeof(Block)));
      blocks_.push_back(block);
      bytes_allocated_ += kBlockSize;
      num_free_ += CellsPerBlock;

      // The starting cell_id for Cells in this block.
      int cell_id = (blocks_.size() - 1) * CellsPerBlock;
      for (Cell& cell : block->cells) {
        FreeCell* free_cell = reinterpret_cast<FreeCell*>(cell);
        free_cell->id = cell_id++;
        free_cell->next = free_list_;
        free_list_ = free_cell;
      }
    }

    FreeCell* cell = free_list_;
    free_list_ = free_list_->next;
    num_free_--;
    *obj_id = cell->id;
    return cell;
  }

  void PrepareForGc() {
    DCHECK(!gc_underway_);
    gc_underway_ = true;
    mark_set_.ReInit(blocks_.size() * CellsPerBlock);
  }

  bool IsMarked(int cell_id) {
    DCHECK(gc_underway_);
    return mark_set_.IsMarked(cell_id);
  }

  void Mark(int cell_id) {
    DCHECK(gc_underway_);
    mark_set_.Mark(cell_id);
  }

  void Sweep() {
    DCHECK(gc_underway_);
    // Iterate over every Cell linking the free ones into a new free list.
    num_free_ = 0;
    free_list_ = nullptr;
    int cell_id = 0;
    for (Block* block : blocks_) {
      for (Cell& cell : block->cells) {
        if (!mark_set_.IsMarked(cell_id)) {
          num_free_++;
          FreeCell* free_cell = reinterpret_cast<FreeCell*>(cell);
          free_cell->id = cell_id;
          free_cell->next = free_list_;
          free_list_ = free_cell;
        }
        cell_id++;
      }
    }
    gc_underway_ = false;
  }

  void Free() {
    for (Block* block : blocks_) {
      free(block);
    }
    blocks_.clear();
  }

  int num_allocated() {
    return num_allocated_;
  }

  int64_t bytes_allocated() {
    return bytes_allocated_;
  }

  int num_live() {
    return blocks_.size() * CellsPerBlock - num_free_;
  }

 private:
  using Cell = uint8_t[CellSize];

  struct Block {
    Cell cells[CellsPerBlock];
  };

  // Unused/free cells are tracked via a linked list of FreeCells. The FreeCells
  // are stored in the unused Cells, so it takes no extra memory to track them.
  struct FreeCell {
    int id;
    FreeCell* next;
  };
  static_assert(CellSize >= sizeof(FreeCell), "CellSize is too small");

  // Whether a GC is underway, for asserting that calls are in order.
  bool gc_underway_ = false;

  FreeCell* free_list_ = nullptr;
  int num_free_ = 0;
  int num_allocated_ = 0;
  int64_t bytes_allocated_ = 0;
  std::vector<Block*> blocks_;
  MarkSet mark_set_;

  DISALLOW_COPY_AND_ASSIGN(Pool<CellsPerBlock COMMA CellSize>);
};

class MarkSweepHeap {
 public:
  // reserve 32 frames to start
  MarkSweepHeap() {
  }

  void Init();  // use default threshold
  void Init(int gc_threshold);

  void PushRoot(RawObject** p) {
    roots_.push_back(p);
  }

  void PopRoot() {
    roots_.pop_back();
  }

  void RootGlobalVar(void* root) {
    global_roots_.push_back(reinterpret_cast<RawObject*>(root));
  }

  void* Allocate(size_t num_bytes, int* obj_id, int* pool_id);

#if 0
  void* Reallocate(void* p, size_t num_bytes);
#endif
  int MaybeCollect();
  int Collect();

  void MaybeMarkAndPush(RawObject* obj);
  void TraceChildren();

  void Sweep();

  void PrintStats(int fd);  // public for testing

  void CleanProcessExit();  // do one last GC, used in unit tests
  void ProcessExit();       // main() lets OS clean up, except ASAN variant

  int num_live() {
    return num_live_
#ifndef NO_POOL_ALLOC
           + pool1_.num_live() + pool2_.num_live()
#endif
        ;
  }

  bool is_initialized_ = true;  // mark/sweep doesn't need to be initialized

  // Runtime params

  // Threshold is a number of live objects, since we aren't keeping track of
  // total bytes
  int gc_threshold_;

  // Show debug logging
  bool gc_verbose_ = false;

  // Current stats
  int num_live_ = 0;
  // Should we keep track of sizes?
  // int64_t bytes_live_ = 0;

  // Cumulative stats
  int max_survived_ = 0;  // max # live after a collection
  int num_allocated_ = 0;
  int64_t bytes_allocated_ = 0;  // avoid overflow
  int num_gc_points_ = 0;        // manual collection points
  int num_collections_ = 0;
  int num_growths_;
  double max_gc_millis_ = 0.0;
  double total_gc_millis_ = 0.0;

#ifndef NO_POOL_ALLOC
  // 16,384 / 24 bytes = 682 cells (rounded), 16,368 bytes
  // 16,384 / 48 bytes = 341 cells (rounded), 16,368 bytes
  // Conveniently, the glibc malloc header is 16 bytes, giving exactly 16 Ki
  // differences
  Pool<682, 24> pool1_;
  Pool<341, 48> pool2_;
#endif

  std::vector<RawObject**> roots_;
  std::vector<RawObject*> global_roots_;

  // Allocate() appends live objects, and Sweep() compacts it
  std::vector<ObjHeader*> live_objs_;
  // Allocate lazily frees these, and Sweep() replenishes it
  std::vector<ObjHeader*> to_free_;

  std::vector<ObjHeader*> gray_stack_;
  MarkSet mark_set_;

  int greatest_obj_id_ = 0;

 private:
  void FreeEverything();
  void MaybePrintStats();

  DISALLOW_COPY_AND_ASSIGN(MarkSweepHeap);
};

#endif  // MARKSWEEP_HEAP_H
