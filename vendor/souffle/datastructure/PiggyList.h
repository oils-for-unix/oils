#pragma once

#include "souffle/utility/ParallelUtil.h"
#include <array>
#include <atomic>
#include <cassert>
#include <cstring>
#include <iostream>
#include <iterator>

#ifdef _WIN32
#include <intrin.h>
/**
 * Some versions of MSVC do not provide a builtin for counting leading zeroes
 * like gcc, so we have to implement it ourselves.
 */
#if defined(_MSC_VER)
int __inline __builtin_clzll(unsigned long long value) {
#if _WIN64
    return static_cast<int>(__lzcnt64(value));
#else
    return static_cast<int>(__lzcnt(value));
#endif
}
#endif  // _MSC_VER
#endif  // _WIN32

using std::size_t;
namespace souffle {

/**
 * A PiggyList that allows insertAt functionality.
 * This means we can't append, as we don't know the next available element.
 * insertAt is dangerous. You must be careful not to call it for the same index twice!
 */
template <class T>
class RandomInsertPiggyList {
public:
    RandomInsertPiggyList() = default;
    // an instance where the initial size is not 65k, and instead is user settable (to a power of
    // initialbitsize)
    RandomInsertPiggyList(std::size_t initialbitsize) : BLOCKBITS(initialbitsize) {}

    /** copy constructor */
    RandomInsertPiggyList(const RandomInsertPiggyList& other) : BLOCKBITS(other.BLOCKBITS) {
        this->numElements.store(other.numElements.load());

        // copy blocks from the old lookup table to this one
        for (std::size_t i = 0; i < maxContainers; ++i) {
            if (other.blockLookupTable[i].load() != nullptr) {
                // calculate the size of that block
                const std::size_t blockSize = INITIALBLOCKSIZE << i;

                // allocate that in the new container
                this->blockLookupTable[i].store(new T[blockSize]);

                // then copy the stuff over
                std::memcpy(this->blockLookupTable[i].load(), other.blockLookupTable[i].load(),
                        blockSize * sizeof(T));
            }
        }
    }

    // move ctr
    RandomInsertPiggyList(RandomInsertPiggyList&& other) = delete;
    // copy assign ctor
    RandomInsertPiggyList& operator=(RandomInsertPiggyList& other) = delete;
    // move assign ctor
    RandomInsertPiggyList& operator=(RandomInsertPiggyList&& other) = delete;

    ~RandomInsertPiggyList() {
        freeList();
    }

    inline std::size_t size() const {
        return numElements.load();
    }

    inline T* getBlock(std::size_t blockNum) const {
        return blockLookupTable[blockNum];
    }

    inline T& get(std::size_t index) const {
        std::size_t nindex = index + INITIALBLOCKSIZE;
        std::size_t blockNum = (63 - __builtin_clzll(nindex));
        std::size_t blockInd = (nindex) & ((1 << blockNum) - 1);
        return this->getBlock(blockNum - BLOCKBITS)[blockInd];
    }

    void insertAt(std::size_t index, T value) {
        // starting with an initial blocksize requires some shifting to transform into a nice powers of two
        // series
        std::size_t blockNum = (63 - __builtin_clzll(index + INITIALBLOCKSIZE)) - BLOCKBITS;

        // allocate the block if not allocated
        if (blockLookupTable[blockNum].load() == nullptr) {
            slock.lock();
            if (blockLookupTable[blockNum].load() == nullptr) {
                blockLookupTable[blockNum].store(new T[INITIALBLOCKSIZE << blockNum]);
            }
            slock.unlock();
        }

        this->get(index) = value;
        // we ALWAYS increment size, even if there was something there before (its impossible to tell!)
        // the onus is up to the user to not call this for an index twice
        ++numElements;
    }

    void clear() {
        freeList();
        numElements.store(0);
    }
    const std::size_t BLOCKBITS = 16ul;
    const std::size_t INITIALBLOCKSIZE = (((std::size_t)1ul) << BLOCKBITS);

    // number of elements currently stored within
    std::atomic<std::size_t> numElements{0};

    // 2^64 - 1 elements can be stored (default initialised to nullptrs)
    static constexpr std::size_t maxContainers = 64;
    std::array<std::atomic<T*>, maxContainers> blockLookupTable = {};

    // for parallel node insertions
    mutable SpinLock slock;

    /**
     * Free the arrays allocated within the linked list nodes
     */
    void freeList() {
        slock.lock();
        // delete all - deleting a nullptr is a no-op
        for (std::size_t i = 0; i < maxContainers; ++i) {
            delete[] blockLookupTable[i].load();
            // reset the container within to be empty.
            blockLookupTable[i].store(nullptr);
        }
        slock.unlock();
    }
};

template <class T>
class PiggyList {
public:
    PiggyList() : num_containers(0), container_size(0), m_size(0) {}
    PiggyList(std::size_t initialbitsize)
            : BLOCKBITS(initialbitsize), num_containers(0), container_size(0), m_size(0) {}

    /** copy constructor */
    PiggyList(const PiggyList& other) : BLOCKBITS(other.BLOCKBITS) {
        num_containers.store(other.num_containers.load());
        container_size.store(other.container_size.load());
        m_size.store(other.m_size.load());
        // copy each chunk from other into this
        // the size of the next container to allocate
        std::size_t cSize = BLOCKSIZE;
        for (std::size_t i = 0; i < other.num_containers; ++i) {
            this->blockLookupTable[i] = new T[cSize];
            std::memcpy(this->blockLookupTable[i], other.blockLookupTable[i], cSize * sizeof(T));
            cSize <<= 1;
        }
        // if this isn't the case, uhh
        assert((cSize >> 1) == container_size.load());
    }

    /** move constructor */
    PiggyList(PiggyList&& other) = delete;
    /** copy assign ctor **/
    PiggyList& operator=(const PiggyList& other) = delete;

    ~PiggyList() {
        freeList();
    }

    /**
     * Well, returns the number of nodes exist within the list + number of nodes queued to be inserted
     *  The reason for this, is that there may be many nodes queued up
     *  that haven't had time to had containers created and updated
     * @return the number of nodes exist within the list + number of nodes queued to be inserted
     */
    inline std::size_t size() const {
        return m_size.load();
    };

    inline T* getBlock(std::size_t blocknum) const {
        return this->blockLookupTable[blocknum];
    }

    std::size_t append(T element) {
        std::size_t new_index = m_size.fetch_add(1, std::memory_order_acquire);

        // will this not fit?
        if (container_size < new_index + 1) {
            sl.lock();
            // check and add as many containers as required
            while (container_size < new_index + 1) {
                blockLookupTable[num_containers] = new T[allocsize];
                num_containers += 1;
                container_size += allocsize;
                // double the number elements that will be allocated next time
                allocsize <<= 1;
            }
            sl.unlock();
        }

        this->get(new_index) = element;
        return new_index;
    }

    std::size_t createNode() {
        std::size_t new_index = m_size.fetch_add(1, std::memory_order_acquire);

        // will this not fit?
        if (container_size < new_index + 1) {
            sl.lock();
            // check and add as many containers as required
            while (container_size < new_index + 1) {
                blockLookupTable[num_containers] = new T[allocsize];
                num_containers += 1;
                container_size += allocsize;
                // double the number elements that will be allocated next time
                allocsize <<= 1;
            }
            sl.unlock();
        }

        return new_index;
    }

    /**
     * Retrieve a reference to the stored value at index
     * @param index position to search
     * @return the value at index
     */
    inline T& get(std::size_t index) const {
        // supa fast 2^16 size first block
        std::size_t nindex = index + BLOCKSIZE;
        std::size_t blockNum = (63 - __builtin_clzll(nindex));
        std::size_t blockInd = (nindex) & ((1 << blockNum) - 1);
        return this->getBlock(blockNum - BLOCKBITS)[blockInd];
    }

    /**
     * Clear all elements from the PiggyList
     */
    void clear() {
        freeList();
        m_size = 0;
        num_containers = 0;

        allocsize = BLOCKSIZE;
        container_size = 0;
    }

    class iterator {
        std::size_t cIndex = 0;
        PiggyList* bl;

    public:
        using iterator_category = std::forward_iterator_tag;
        using value_type = T;
        using difference_type = void;
        using pointer = T*;
        using reference = T&;

        // default ctor, to silence
        iterator() = default;

        /* begin iterator for iterating over all elements */
        iterator(PiggyList* bl) : bl(bl){};
        /* ender iterator for marking the end of the iteration */
        iterator(PiggyList* bl, std::size_t beginInd) : cIndex(beginInd), bl(bl){};

        T operator*() {
            return bl->get(cIndex);
        };
        const T operator*() const {
            return bl->get(cIndex);
        };

        iterator& operator++(int) {
            ++cIndex;
            return *this;
        };

        iterator operator++() {
            iterator ret(*this);
            ++cIndex;
            return ret;
        };

        bool operator==(const iterator& x) const {
            return x.cIndex == this->cIndex && x.bl == this->bl;
        };

        bool operator!=(const iterator& x) const {
            return !(x == *this);
        };
    };

    iterator begin() {
        return iterator(this);
    }
    iterator end() {
        return iterator(this, size());
    }
    const std::size_t BLOCKBITS = 16ul;
    const std::size_t BLOCKSIZE = (((std::size_t)1ul) << BLOCKBITS);

    // number of inserted
    std::atomic<std::size_t> num_containers = 0;
    std::size_t allocsize = BLOCKSIZE;
    std::atomic<std::size_t> container_size = 0;
    std::atomic<std::size_t> m_size = 0;

    // > 2^64 elements can be stored (default initialise to nullptrs)
    static constexpr std::size_t max_conts = 64;
    std::array<T*, max_conts> blockLookupTable = {};

    // for parallel node insertions
    mutable SpinLock sl;

    /**
     * Free the arrays allocated within the linked list nodes
     */
    void freeList() {
        sl.lock();
        // we don't know which ones are taken up!
        for (std::size_t i = 0; i < num_containers; ++i) {
            delete[] blockLookupTable[i];
        }
        sl.unlock();
    }
};

}  // namespace souffle
