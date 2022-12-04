#ifndef MARKSWEEP_HEAP_H
#define MARKSWEEP_HEAP_H

#include <unordered_set>
#include <vector>

class MarkSweepHeap;  // forward decl for circular dep

// The set of objects where the mark and sweep algorithm starts.  Terminology:
// to "root" an object means "add it to the root set".
class RootSet {
 public:
  // start with 1 live frame and e.g. 32 reserved ones
  explicit RootSet(int num_reserved) : num_frames_(1) {
    assert(num_reserved > 1);
    stack_.reserve(num_reserved);
    for (int i = 0; i < num_reserved; ++i) {
      stack_.emplace_back();      // Construct std::vector frame IN PLACE.
      stack_.back().reserve(16);  // Reserve 16 rooted variables per frame.
    }
  }

  // Called on function entry
  void PushFrame() {
    // Construct more std::vector frames if necessary.  We reuse vectors to
    // avoid constructing one on every function call.
    int num_constructed = stack_.size();
    if (num_frames_ >= num_constructed) {
      stack_.emplace_back();
      stack_.back().reserve(16);
#if 0
      num_constructed = roots_.size();
      log("num_frames_ %d, num_constructed %d", num_frames_, num_constructed);
      assert(num_frames_ + 1 == num_constructed);
#endif
    }

    num_frames_++;
    // log("PushFrame -> %d", num_frames_);
  }

  // Called on function exit
  void PopFrame() {
    // Remove all roots owned by the top frame.  We're REUSING frames, so not
    // calling vector<>::pop().
    stack_[num_frames_ - 1].clear();
    num_frames_--;
    // log("PopFrame -> %d", num_frames_);
  }

  // Called when returning a value (except in trivial passthrough case)
  void RootOnReturn(Obj* root) {
    // log("RootOnReturn %p %d", root, num_frames_);

    if (root == nullptr) {  // No reason to add it
      return;
    }
    // We should have 2 frames because we start with 1 for main(), and main()
    // itself can't return GC objects.
    assert(num_frames_ > 1);

    // Owned by the frame BELOW
    stack_[num_frames_ - 2].push_back(root);
  }

  // Called in 2 situations:
  // - the "leaf" Allocate(), which does not have a RootsFrame
  // - when catching exceptions:
  //   catch (IOError e) { gHeap.RootInCurrentFrame(e); }
  void RootInCurrentFrame(Obj* root) {
    if (root == nullptr) {  // No reason to add it
      return;
    }
    assert(num_frames_ > 0);
    stack_[num_frames_ - 1].push_back(root);
  }

  void RootGlobalVar(Obj* root) {
    if (root == nullptr) {  // No reason to add it
      return;
    }
    assert(num_frames_ > 0);
    stack_[0].push_back(root);
  }

  // For testing
  int NumFrames() {
    return num_frames_;
  }

  // Calculate size of root set, for unit tests only.
  int NumRoots() {
    int result = 0;
    for (int i = 0; i < num_frames_; ++i) {
      result += stack_[i].size();
    }
    return result;
  }

  void MarkRoots(MarkSweepHeap* heap);

  // A stack of frames that's updated in parallel the call stack.
  // This representation is appropriate since multiple stack frames are "in
  // play" at once.  That is, RootOnReturn() may mutate root_set_[1] while
  // root_set_[2] is being pushed/popped/modified.
  std::vector<std::vector<Obj*>> stack_;
  int num_frames_ = 0;  // frames 0 to N-1 are valid
};

class MarkSweepHeap {
 public:
  // reserve 32 frames to start
  MarkSweepHeap() : root_set_(32) {
  }

  void Init();  // use default threshold
  void Init(int gc_threshold);

  //
  // OLD Local Var Rooting
  //

  void PushRoot(Obj** p) {
    roots_.push_back(p);
  }

  void PopRoot() {
    roots_.pop_back();
  }

  //
  // NEW Return Value Rooting
  //

  void RootOnReturn(Obj* root) {
    root_set_.RootOnReturn(root);
  }

  void RootInCurrentFrame(Obj* root) {
    root_set_.RootInCurrentFrame(root);
  }

  void RootGlobalVar(Obj* root) {
    root_set_.RootGlobalVar(root);
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

  // OLD rooting
  std::vector<Obj**> roots_;

  // NEW rooting
  RootSet root_set_;

  std::vector<void*> live_objs_;
  std::unordered_set<void*> marked_;

 private:
  void DoProcessExit(bool fast_exit);

  DISALLOW_COPY_AND_ASSIGN(MarkSweepHeap);
};

#ifndef BUMP_LEAK
extern MarkSweepHeap gHeap;
#endif

class RootsFrame {
  // Create an instance of this in every function.  This lets the GC now when
  // functions return, so it can remove values from the root set.
  //
  // Example:
  //
  //   RootsFrame _r{FUNC_NAME};
  //   RootsFrame _r{LOOP};
  //
  // You must use braced initialization!
  //
  //   RootsFrame _r(FUNC_NAME);  // WRONG because it sometimes expands to:
  //   RootsFrame _r();           // MOST VEXING PARSE: a function prototype,
  //                              // not a variable

 public:
#ifdef COLLECT_COVERAGE
  explicit RootsFrame(const char* description) {
    log(">>> %s", description);
  #ifndef BUMP_LEAK
    gHeap.root_set_.PushFrame();
  #endif
  }
#endif

  RootsFrame() {
#ifndef BUMP_LEAK
    gHeap.root_set_.PushFrame();
#endif
  }
  ~RootsFrame() {
#ifndef BUMP_LEAK
    gHeap.root_set_.PopFrame();
#endif
  }
};

// Explicit annotation for "skipped frame" optimization, and the like

#define NO_ROOTS_FRAME(description)

#ifdef COLLECT_COVERAGE
  #define FUNC_NAME __PRETTY_FUNCTION__
  // TODO: create a different string for loops
  #define LOOP __PRETTY_FUNCTION__
#else
  #define FUNC_NAME
  #define LOOP
#endif

// Variadic templates:
// https://eli.thegreenplace.net/2014/variadic-templates-in-c/
template <typename T, typename... Args>
T* Alloc(Args&&... args) {
  NO_ROOTS_FRAME(FUNC_NAME);

  assert(gHeap.is_initialized_);
  void* place = gHeap.Allocate(sizeof(T));
  assert(place != nullptr);
  // placement new
  return new (place) T(std::forward<Args>(args)...);
}

class StackRoots {
 public:
  StackRoots(std::initializer_list<void*> roots) {
    n_ = roots.size();
    for (auto root : roots) {  // can't use roots[i]
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
