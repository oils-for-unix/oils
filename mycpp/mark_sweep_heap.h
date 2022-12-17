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

  void PushRoot(Obj** p) {
    roots_.push_back(p);
  }

  void PopRoot() {
    roots_.pop_back();
  }

  // TODO: change to void* to avoid implicit static_cast<>, which changes the
  // address when there's a vtable
  void RootGlobalVar(Obj* root) {
    global_roots_.push_back(root);
  }

  void* Allocate(size_t num_bytes);
  void* Reallocate(void* p, size_t num_bytes);
  int MaybeCollect();
  int Collect();
  void MarkObjects(Obj* obj);
  void Sweep();

  // Cleanup at the end of main() to remain ASAN-safe
  void CleanProcessExit();

  // Faster exit
  void FastProcessExit();

  void Report();

  bool is_initialized_ = true;  // mark/sweep doesn't need to be initialized

  // In number of live objects, since we aren't keeping track of total bytes
  int gc_threshold_;

  // Cumulative stats
  int64_t num_allocated_ = 0;
  int64_t bytes_allocated_ = 0;
  int64_t num_collections_ = 0;
  int max_live_ = 0;  // max # live after a collection

  // current stats
  int num_live_ = 0;
  // Should we keep track of sizes?
  // int64_t bytes_live_ = 0;

  double max_gc_millis_ = 0.0;
  double total_gc_millis_ = 0.0;

  std::vector<Obj**> roots_;
  std::vector<Obj*> global_roots_;

  std::vector<void*> live_objs_;
  std::unordered_set<void*> marked_;

 private:
  void DoProcessExit(bool fast_exit);

  DISALLOW_COPY_AND_ASSIGN(MarkSweepHeap);
};

#ifndef BUMP_LEAK
extern MarkSweepHeap gHeap;
#endif

// Variadic templates:
// https://eli.thegreenplace.net/2014/variadic-templates-in-c/
template <typename T, typename... Args>
T* Alloc(Args&&... args) {
  assert(gHeap.is_initialized_);
  void* place = gHeap.Allocate(sizeof(T));
  assert(place != nullptr);
  // placement new
  return new (place) T(std::forward<Args>(args)...);
}

#define VALIDATE_ROOTS 0

class StackRoots {
 public:
  StackRoots(std::initializer_list<void*> roots) {
    n_ = roots.size();

#if VALIDATE_ROOTS
    int i = 0;
#endif

    for (auto root : roots) {  // can't use roots[i]

#if VALIDATE_ROOTS
      Obj* obj = *(reinterpret_cast<Obj**>(root));
      if (obj) {
        Obj* header = ObjHeader(obj);
        log("obj %p header %p", obj, header);

        switch (header->heap_tag_) {
        case Tag::Global:
        case Tag::Opaque:
        case Tag::Scanned:
        case Tag::FixedSize:
          break;

        default:
          log("root %d heap %d type %d mask %d len %d", i, header->heap_tag_,
              header->type_tag_, header->field_mask_, header->obj_len_);

          assert(0);
          break;
        }
      }
      i++;
#endif

      gHeap.PushRoot(reinterpret_cast<Obj**>(root));
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
