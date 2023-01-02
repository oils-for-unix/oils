#ifndef MARKSWEEP_HEAP_H
#define MARKSWEEP_HEAP_H

#include <unordered_set>
#include <vector>

class MarkSet {
 public:
  MarkSet() : bits_() {
  }

  // ReInit() must be called at the start of MarkObjects().  Allocate() should
  // keep track of the maximum object ID.
  void ReInit(int max_obj_id) {
    // TODO: exit with a good error message, and TEST it!  Another thing we
    // could is disable collection if there are too many objects?  The process
    // MIGHT finish, and the OS will clean up.
    CHECK(max_obj_id <= kMaxObjId);

    // https://stackoverflow.com/questions/8848575/fastest-way-to-reset-every-value-of-stdvectorint-to-0
    std::fill(bits_.begin(), bits_.end(), 0);
    int max_byte_index = (max_obj_id >> 3) + 1;  // round up
    // log("ReInit max_byte_index %d", max_byte_index);
    bits_.resize(max_byte_index);
  }

  // Called by MarkObjects()
  void Mark(int obj_id) {
    int byte_index = obj_id >> 3;  // 8 bits per byte
    int bit_index = obj_id & 0b111;
    // log("byte_index %d %d", byte_index, bit_index);
    bits_[byte_index] |= (1 << bit_index);
  }

  // Called by Sweep()
  bool IsMarked(int obj_id) {
    int byte_index = obj_id >> 3;
    int bit_index = obj_id & 0b111;
    return bits_[byte_index] & (1 << bit_index);
  }

  // Allocate() will call this when we implement recycling of object IDs
  int NextObjectId() {
    FAIL(kNotImplemented);
  }

  void Debug() {
    int n = bits_.size();
    for (int i = 0; i < n; ++i) {
      printf("%x ", bits_[i]);
    }
    printf("\n");
  }

  std::vector<uint8_t> bits_;  // bit vector indexed by obj_id
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

  void* Allocate(size_t num_bytes);
  void* Reallocate(void* p, size_t num_bytes);
  int MaybeCollect();
  int Collect();
  void MarkObjects(RawObject* obj);
  void Sweep();

  void PrintStats(int fd);  // public for testing

  void CleanProcessExit();  // do one last GC so ASAN passes
  void FastProcessExit();   // let the OS clean up

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

  std::vector<RawObject**> roots_;
  std::vector<RawObject*> global_roots_;

  std::vector<void*> live_objs_;
  std::unordered_set<void*> marked_;

  MarkSet mark_set_;

  int current_obj_id_ = 0;

 private:
  void DoProcessExit(bool fast_exit);

  DISALLOW_COPY_AND_ASSIGN(MarkSweepHeap);
};

#ifndef BUMP_LEAK
extern MarkSweepHeap gHeap;
#endif

// Note:
// - This function causes code bloat due to template expansion on hundreds of
//   types.  Could switch to a GC_NEW() macro
// - GCC generates slightly larger code if you factor out void* place and new
//   (place) T()
//
// Variadic templates:
// https://eli.thegreenplace.net/2014/variadic-templates-in-c/
template <typename T, typename... Args>
T* Alloc(Args&&... args) {
  DCHECK(gHeap.is_initialized_);
  return new (gHeap.Allocate(sizeof(T))) T(std::forward<Args>(args)...);
}

#define VALIDATE_ROOTS 0

class StackRoots {
 public:
  // Note: void** seems logical, because these are pointers to pointers, but
  // the C++ compiler doesn't like it.
  StackRoots(std::initializer_list<void*> roots) {
    n_ = roots.size();

#if VALIDATE_ROOTS
    int i = 0;
#endif

    for (auto root : roots) {  // can't use roots[i]

#if VALIDATE_ROOTS
      RawObject* obj = *(reinterpret_cast<RawObject**>(root));
      if (obj) {
        RawObject* header = FindObjHeader(obj);
        log("obj %p header %p", obj, header);

        switch (header->heap_tag) {
        case HeapTag::Global:
        case HeapTag::Opaque:
        case HeapTag::Scanned:
        case HeapTag::FixedSize:
          break;

        default:
          log("root %d heap %d type %d mask %d len %d", i, header->heap_tag,
              header->type_tag, header->field_mask, header->obj_len);

          assert(0);
          break;
        }
      }
      i++;
#endif

      gHeap.PushRoot(reinterpret_cast<RawObject**>(root));
    }
  }

  ~StackRoots() {
    for (int i = 0; i < n_; ++i) {
      gHeap.PopRoot();
    }
  }

 private:
  int n_;
};

#endif  // MARKSWEEP_HEAP_H
