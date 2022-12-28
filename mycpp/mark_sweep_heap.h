#ifndef MARKSWEEP_HEAP_H
#define MARKSWEEP_HEAP_H

#include <unordered_set>
#include <vector>

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
