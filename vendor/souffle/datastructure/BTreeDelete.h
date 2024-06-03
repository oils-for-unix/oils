/*
 * Souffle - A Datalog Compiler
 * Copyright (c) 2013, 2015, Oracle and/or its affiliates. All rights reserved
 * Licensed under the Universal Permissive License v 1.0 as shown at:
 * - https://opensource.org/licenses/UPL
 * - <souffle root>/licenses/SOUFFLE-UPL.txt
 */

/************************************************************************
 *
 * @file BTreeDelete.h
 *
 * An implementation of a generic B-tree data structure including
 * interfaces for utilizing instances as set or multiset containers
 * and deletion.
 *
 ***********************************************************************/

#pragma once

#include "souffle/datastructure/BTreeUtil.h"
#include "souffle/utility/CacheUtil.h"
#include "souffle/utility/ContainerUtil.h"
#include "souffle/utility/MiscUtil.h"
#include "souffle/utility/ParallelUtil.h"
#include <algorithm>
#include <cassert>
#include <cstddef>
#include <cstdint>
#include <iostream>
#include <iterator>
#include <string>
#include <tuple>
#include <type_traits>
#include <typeinfo>
#include <vector>

namespace souffle {

namespace detail {

/**
 * The actual implementation of a b-tree data structure.
 *
 * @tparam Key             .. the element type to be stored in this tree
 * @tparam Comparator     .. a class defining an order on the stored elements
 * @tparam Allocator     .. utilized for allocating memory for required nodes
 * @tparam blockSize    .. determines the number of bytes/block utilized by leaf nodes
 * @tparam SearchStrategy .. enables switching between linear, binary or any other search strategy
 * @tparam isSet        .. true = set, false = multiset
 */
template <typename Key, typename Comparator,
        typename Allocator,  // is ignored so far - TODO: add support
        unsigned blockSize, typename SearchStrategy, bool isSet, typename WeakComparator = Comparator,
        typename Updater = detail::updater<Key>>
class btree_delete {
public:
    class iterator;
    using const_iterator = iterator;

    using key_type = Key;
    using element_type = Key;
    using chunk = range<iterator>;

protected:
    /* ------------- static utilities ----------------- */

    const static SearchStrategy search;

    /* ---------- comparison utilities ---------------- */

    mutable Comparator comp;

    bool less(const Key& a, const Key& b) const {
        return comp.less(a, b);
    }

    bool equal(const Key& a, const Key& b) const {
        return comp.equal(a, b);
    }

    mutable WeakComparator weak_comp;

    bool weak_less(const Key& a, const Key& b) const {
        return weak_comp.less(a, b);
    }

    bool weak_equal(const Key& a, const Key& b) const {
        return weak_comp.equal(a, b);
    }

    /* -------------- updater utilities ------------- */

    mutable Updater upd;
    bool update(Key& old_k, const Key& new_k) {
        return upd.update(old_k, new_k);
    }

    /* -------------- the node type ----------------- */

    using size_type = std::size_t;
    using field_index_type = uint8_t;
    using lock_type = OptimisticReadWriteLock;

    struct node;

    /**
     * The base type of all node types containing essential
     * book-keeping information.
     */
    struct base {
#ifdef IS_PARALLEL

        // the parent node
        node* volatile parent;

        // a lock for synchronizing parallel operations on this node
        lock_type lock;

        // the number of keys in this node
        volatile size_type numElements;

        // the position in the parent node
        volatile field_index_type position;
#else
        // the parent node
        node* parent;

        // the number of keys in this node
        size_type numElements;

        // the position in the parent node
        field_index_type position;
#endif

        // a flag indicating whether this is a inner node or not
        const bool inner;

        /**
         * A simple constructor for nodes
         */
        base(bool inner) : parent(nullptr), numElements(0), position(0), inner(inner) {}

        bool isLeaf() const {
            return !inner;
        }

        bool isInner() const {
            return inner;
        }

        node* getParent() const {
            return parent;
        }

        field_index_type getPositionInParent() const {
            return position;
        }

        size_type getNumElements() const {
            return numElements;
        }
    };

    struct inner_node;

    /**
     * The actual, generic node implementation covering the operations
     * for both, inner and leaf nodes.
     */
    struct node : public base {
        /**
         * The number of keys/node desired by the user.
         */
        static constexpr std::size_t desiredNumKeys =
                ((blockSize > sizeof(base)) ? blockSize - sizeof(base) : 0) / sizeof(Key);

        /**
         * The actual number of keys/node corrected by functional requirements.
         */
        static constexpr std::size_t maxKeys = (desiredNumKeys > 3) ? desiredNumKeys : 3;
        static constexpr std::size_t split_point = std::min(3 * maxKeys / 4, maxKeys - 2);
        static constexpr std::size_t minKeys = std::min(maxKeys - (split_point + 1), split_point + 1);

        // the keys stored in this node
        Key keys[maxKeys];

        // a simple constructor
        node(bool inner) : base(inner) {}

        /**
         * A deep-copy operation creating a clone of this node.
         */
        node* clone() const {
            // create a clone of this node
            node* res = (this->isInner()) ? static_cast<node*>(new inner_node())
                                          : static_cast<node*>(new leaf_node());

            // copy basic fields
            res->position = this->position;
            res->numElements = this->numElements;

            for (size_type i = 0; i < this->numElements; ++i) {
                res->keys[i] = this->keys[i];
            }

            // if this is a leaf we are done
            if (this->isLeaf()) {
                return res;
            }

            // copy child nodes recursively
            auto* ires = (inner_node*)res;
            for (size_type i = 0; i <= this->numElements; ++i) {
                ires->children[i] = this->getChild(i)->clone();
                ires->children[i]->parent = res;
            }

            // that's it
            return res;
        }

        /**
         * A utility function providing a reference to this node as
         * an inner node.
         */
        inner_node& asInnerNode() {
            assert(this->inner && "Invalid cast!");
            return *static_cast<inner_node*>(this);
        }

        /**
         * A utility function providing a reference to this node as
         * a const inner node.
         */
        const inner_node& asInnerNode() const {
            assert(this->inner && "Invalid cast!");
            return *static_cast<const inner_node*>(this);
        }

        /**
         * Computes the number of nested levels of the tree rooted
         * by this node.
         */
        size_type getDepth() const {
            if (this->isLeaf()) {
                return 1;
            }
            return getChild(0)->getDepth() + 1;
        }

        /**
         * Counts the number of nodes contained in the sub-tree rooted
         * by this node.
         */
        size_type countNodes() const {
            if (this->isLeaf()) {
                return 1;
            }
            size_type sum = 1;
            for (unsigned i = 0; i <= this->numElements; ++i) {
                sum += getChild(i)->countNodes();
            }
            return sum;
        }

        /**
         * Counts the number of entries contained in the sub-tree rooted
         * by this node.
         */
        size_type countEntries() const {
            if (this->isLeaf()) {
                return this->numElements;
            }
            size_type sum = this->numElements;
            for (unsigned i = 0; i <= this->numElements; ++i) {
                sum += getChild(i)->countEntries();
            }
            return sum;
        }

        /**
         * Determines the amount of memory used by the sub-tree rooted
         * by this node.
         */
        size_type getMemoryUsage() const {
            if (this->isLeaf()) {
                return sizeof(leaf_node);
            }
            size_type res = sizeof(inner_node);
            for (unsigned i = 0; i <= this->numElements; ++i) {
                res += getChild(i)->getMemoryUsage();
            }
            return res;
        }

        /**
         * Obtains a pointer to the array of child-pointers
         * of this node -- if it is an inner node.
         */
        node** getChildren() {
            return asInnerNode().children;
        }

        /**
         * Obtains a pointer to the array of const child-pointers
         * of this node -- if it is an inner node.
         */
        node* const* getChildren() const {
            return asInnerNode().children;
        }

        /**
         * Obtains a reference to the child of the given index.
         */
        node* getChild(size_type s) const {
            return asInnerNode().children[s];
        }

        /**
         * Checks whether this node is empty -- can happen due to biased insertion.
         */
        bool isEmpty() const {
            return this->numElements == 0;
        }

        /**
         * Checks whether this node is full.
         */
        bool isFull() const {
            return this->numElements == maxKeys;
        }

        /**
         * Obtains the point at which full nodes should be split.
         * Conventional b-trees always split in half. However, in cases
         * where in-order insertions are frequent, a split assigning
         * larger portions to the right fragment provide higher performance
         * and a better node-filling rate.
         */
        int getSplitPoint(int /*unused*/) {
            return static_cast<int>(split_point);
        }

        /**
         * Splits this node.
         *
         * @param root .. a pointer to the root-pointer of the enclosing b-tree
         *                 (might have to be updated if the root-node needs to be split)
         * @param idx  .. the position of the insert causing the split
         */
#ifdef IS_PARALLEL
        void split(node** root, lock_type& root_lock, int idx, std::vector<node*>& locked_nodes) {
            assert(this->lock.is_write_locked());
            assert(!this->parent || this->parent->lock.is_write_locked());
            assert((this->parent != nullptr) || root_lock.is_write_locked());
            assert(this->isLeaf() || souffle::contains(locked_nodes, this));
            assert(!this->parent || souffle::contains(locked_nodes, const_cast<node*>(this->parent)));
#else
        void split(node** root, lock_type& root_lock, int idx) {
#endif
            assert(this->numElements == maxKeys);

            // get middle element
            int split_point = getSplitPoint(idx);

            // create a new sibling node
            node* sibling = (this->inner) ? static_cast<node*>(new inner_node())
                                          : static_cast<node*>(new leaf_node());

#ifdef IS_PARALLEL
            // lock sibling
            sibling->lock.start_write();
            locked_nodes.push_back(sibling);
#endif

            // move data over to the new node
            for (unsigned i = split_point + 1, j = 0; i < maxKeys; ++i, ++j) {
                sibling->keys[j] = keys[i];
            }

            // move child pointers
            if (this->inner) {
                // move pointers to sibling
                auto* other = static_cast<inner_node*>(sibling);
                for (unsigned i = split_point + 1, j = 0; i <= maxKeys; ++i, ++j) {
                    other->children[j] = getChildren()[i];
                    other->children[j]->parent = other;
                    other->children[j]->position = static_cast<field_index_type>(j);
                }
            }

            // update number of elements
            this->numElements = split_point;
            sibling->numElements = maxKeys - split_point - 1;

            // update parent
#ifdef IS_PARALLEL
            grow_parent(root, root_lock, sibling, locked_nodes);
#else
            grow_parent(root, root_lock, sibling);
#endif
        }

        /**
         * Moves keys from this node to one of its siblings or splits
         * this node to make some space for the insertion of an element at
         * position idx.
         *
         * Returns the number of elements moved to the left side, 0 in case
         * of a split. The number of moved elements will be <= the given idx.
         *
         * @param root .. the root node of the b-tree being part of
         * @param idx  .. the position of the insert triggering this operation
         */
        // TODO: remove root_lock ... no longer needed
#ifdef IS_PARALLEL
        int rebalance_or_split(node** root, lock_type& root_lock, int idx, std::vector<node*>& locked_nodes) {
            assert(this->lock.is_write_locked());
            assert(!this->parent || this->parent->lock.is_write_locked());
            assert((this->parent != nullptr) || root_lock.is_write_locked());
            assert(this->isLeaf() || souffle::contains(locked_nodes, this));
            assert(!this->parent || souffle::contains(locked_nodes, const_cast<node*>(this->parent)));
#else
        int rebalance_or_split(node** root, lock_type& root_lock, int idx) {
#endif

            // this node is full ... and needs some space
            assert(this->numElements == maxKeys);

            // get snap-shot of parent
            auto parent = this->parent;
            auto pos = this->position;

            // Option A) re-balance data
            if (parent && pos > 0) {
                node* left = parent->getChild(pos - 1);

#ifdef IS_PARALLEL
                // lock access to left sibling
                if (!left->lock.try_start_write()) {
                    // left node is currently updated => skip balancing and split
                    split(root, root_lock, idx, locked_nodes);
                    return 0;
                }
#endif

                // compute number of elements to be movable to left
                //    space available in left vs. insertion index
                size_type num = static_cast<size_type>(
                        std::min<int>(static_cast<int>(maxKeys - left->numElements), idx));

                // if there are elements to move ..
                if (num > 0) {
                    Key* splitter = &(parent->keys[this->position - 1]);

                    // .. move keys to left node
                    left->keys[left->numElements] = *splitter;
                    for (size_type i = 0; i < num - 1; ++i) {
                        left->keys[left->numElements + 1 + i] = keys[i];
                    }
                    *splitter = keys[num - 1];

                    // shift keys in this node to the left
                    for (size_type i = 0; i < this->numElements - num; ++i) {
                        keys[i] = keys[i + num];
                    }

                    // .. and children if necessary
                    if (this->isInner()) {
                        auto* ileft = static_cast<inner_node*>(left);
                        auto* iright = static_cast<inner_node*>(this);

                        // move children
                        for (field_index_type i = 0; i < num; ++i) {
                            ileft->children[left->numElements + i + 1] = iright->children[i];
                        }

                        // update moved children
                        for (size_type i = 0; i < num; ++i) {
                            iright->children[i]->parent = ileft;
                            iright->children[i]->position =
                                    static_cast<field_index_type>(left->numElements + i) + 1;
                        }

                        // shift child-pointer to the left
                        for (size_type i = 0; i < this->numElements - num + 1; ++i) {
                            iright->children[i] = iright->children[i + num];
                        }

                        // update position of children
                        for (size_type i = 0; i < this->numElements - num + 1; ++i) {
                            iright->children[i]->position = static_cast<field_index_type>(i);
                        }
                    }

                    // update node sizes
                    left->numElements += num;
                    this->numElements -= num;

#ifdef IS_PARALLEL
                    left->lock.end_write();
#endif

                    // done
                    return static_cast<int>(num);
                }

#ifdef IS_PARALLEL
                left->lock.abort_write();
#endif
            }

            // Option B) split node
#ifdef IS_PARALLEL
            split(root, root_lock, idx, locked_nodes);
#else
            split(root, root_lock, idx);
#endif
            return 0;  // = no re-balancing
        }

    private:
        /**
         * Inserts a new sibling into the parent of this node utilizing
         * the last key of this node as a separation key. (for internal
         * use only)
         *
         * @param root .. a pointer to the root-pointer of the containing tree
         * @param sibling .. the new right-sibling to be add to the parent node
         */
#ifdef IS_PARALLEL
        void grow_parent(node** root, lock_type& root_lock, node* sibling, std::vector<node*>& locked_nodes) {
            assert(this->lock.is_write_locked());
            assert(!this->parent || this->parent->lock.is_write_locked());
            assert((this->parent != nullptr) || root_lock.is_write_locked());
            assert(this->isLeaf() || souffle::contains(locked_nodes, this));
            assert(!this->parent || souffle::contains(locked_nodes, const_cast<node*>(this->parent)));
#else
        void grow_parent(node** root, lock_type& root_lock, node* sibling) {
#endif

            if (this->parent == nullptr) {
                assert(*root == this);

                // create a new root node
                auto* new_root = new inner_node();
                new_root->numElements = 1;
                new_root->keys[0] = keys[this->numElements];

                new_root->children[0] = this;
                new_root->children[1] = sibling;

                // link this and the sibling node to new root
                this->parent = new_root;
                sibling->parent = new_root;
                sibling->position = 1;

                // switch root node
                *root = new_root;

            } else {
                // insert new element in parent element
                auto parent = this->parent;
                auto pos = this->position;

#ifdef IS_PARALLEL
                parent->insert_inner(
                        root, root_lock, pos, this, keys[this->numElements], sibling, locked_nodes);
#else
                parent->insert_inner(root, root_lock, pos, this, keys[this->numElements], sibling);
#endif
            }
        }

        /**
         * Inserts a new element into an inner node (for internal use only).
         *
         * @param root .. a pointer to the root-pointer of the containing tree
         * @param pos  .. the position to insert the new key
         * @param key  .. the key to insert
         * @param newNode .. the new right-child of the inserted key
         */
#ifdef IS_PARALLEL
        void insert_inner(node** root, lock_type& root_lock, unsigned pos, node* predecessor, const Key& key,
                node* newNode, std::vector<node*>& locked_nodes) {
            assert(this->lock.is_write_locked());
            assert(souffle::contains(locked_nodes, this));
#else
        void insert_inner(node** root, lock_type& root_lock, unsigned pos, node* predecessor, const Key& key,
                node* newNode) {
#endif

            // check capacity
            if (this->numElements >= maxKeys) {
#ifdef IS_PARALLEL
                assert(!this->parent || this->parent->lock.is_write_locked());
                assert((this->parent) || root_lock.is_write_locked());
                assert(!this->parent || souffle::contains(locked_nodes, const_cast<node*>(this->parent)));
#endif

                // split this node
#ifdef IS_PARALLEL
                pos -= rebalance_or_split(root, root_lock, pos, locked_nodes);
#else
                pos -= rebalance_or_split(root, root_lock, pos);
#endif

                // complete insertion within new sibling if necessary
                if (pos > this->numElements) {
                    // correct position
                    pos = pos - static_cast<unsigned int>(this->numElements) - 1;

                    // get new sibling
                    auto other = this->parent->getChild(this->position + 1);

#ifdef IS_PARALLEL
                    // make sure other side is write locked
                    assert(other->lock.is_write_locked());
                    assert(souffle::contains(locked_nodes, other));

                    // search for new position (since other may have been altered in the meanwhile)
                    size_type i = 0;
                    for (; i <= other->numElements; ++i) {
                        if (other->getChild(i) == predecessor) {
                            break;
                        }
                    }

                    pos = (i > static_cast<unsigned>(other->numElements)) ? 0 : static_cast<unsigned>(i);
                    other->insert_inner(root, root_lock, pos, predecessor, key, newNode, locked_nodes);
#else
                    other->insert_inner(root, root_lock, pos, predecessor, key, newNode);
#endif
                    return;
                }
            }

            // move bigger keys one forward
            for (int i = static_cast<int>(this->numElements) - 1; i >= (int)pos; --i) {
                keys[i + 1] = keys[i];
                getChildren()[i + 2] = getChildren()[i + 1];
                ++getChildren()[i + 2]->position;
            }

            // ensure proper position
            assert(getChild(pos) == predecessor);

            // insert new element
            keys[pos] = key;
            getChildren()[pos + 1] = newNode;
            newNode->parent = this;
            newNode->position = static_cast<field_index_type>(pos) + 1;
            ++this->numElements;
        }

    public:
        /**
         * Prints a textual representation of this tree to the given output stream.
         * This feature is mainly intended for debugging and tuning purposes.
         *
         * @see btree::printTree
         */
        void printTree(std::ostream& out, const std::string& prefix) const {
            // print the header
            out << prefix << "@" << this << "[" << ((int)(this->position)) << "] - "
                << (this->inner ? "i" : "") << "node : " << this->numElements << "/" << maxKeys << " [";

            // print the keys
            for (unsigned i = 0; i < this->numElements; i++) {
                out << keys[i];
                if (i != this->numElements - 1) {
                    out << ",";
                }
            }
            out << "]";

            // print references to children
            if (this->inner) {
                out << " - [";
                for (unsigned i = 0; i <= this->numElements; i++) {
                    out << getChildren()[i];
                    if (i != this->numElements) {
                        out << ",";
                    }
                }
                out << "]";
            }

#ifdef IS_PARALLEL
            // print the lock state
            if (this->lock.is_write_locked()) {
                std::cout << " locked";
            }
#endif

            out << "\n";

            // print the children recursively
            if (this->inner) {
                for (unsigned i = 0; i < this->numElements + 1; ++i) {
                    static_cast<const inner_node*>(this)->children[i]->printTree(out, prefix + "    ");
                }
            }
        }

        /**
         * A function decomposing the sub-tree rooted by this node into approximately equally
         * sized chunks. To minimize computational overhead, no strict load balance nor limit
         * on the number of actual chunks is given.
         *
         * @see btree::getChunks()
         *
         * @param res   .. the list of chunks to be extended
         * @param num   .. the number of chunks to be produced
         * @param begin .. the iterator to start the first chunk with
         * @param end   .. the iterator to end the last chunk with
         * @return the handed in list of chunks extended by generated chunks
         */
        std::vector<chunk>& collectChunks(
                std::vector<chunk>& res, size_type num, const iterator& begin, const iterator& end) const {
            assert(num > 0);

            // special case: this node is empty
            if (isEmpty()) {
                if (begin != end) {
                    res.push_back(chunk(begin, end));
                }
                return res;
            }

            // special case: a single chunk is requested
            if (num == 1) {
                res.push_back(chunk(begin, end));
                return res;
            }

            // cut-off
            if (this->isLeaf() || num < (this->numElements + 1)) {
                auto step = this->numElements / num;
                if (step == 0) {
                    step = 1;
                }

                size_type i = 0;

                // the first chunk starts at the begin
                res.push_back(chunk(begin, iterator(this, static_cast<field_index_type>(step) - 1)));

                // split up the main part
                for (i = step - 1; i < this->numElements - step; i += step) {
                    res.push_back(chunk(iterator(this, static_cast<field_index_type>(i)),
                            iterator(this, static_cast<field_index_type>(i + step))));
                }

                // the last chunk runs to the end
                res.push_back(chunk(iterator(this, static_cast<field_index_type>(i)), end));

                // done
                return res;
            }

            // else: collect chunks of sub-set elements

            auto part = num / (this->numElements + 1);
            assert(part > 0);
            getChild(0)->collectChunks(res, part, begin, iterator(this, 0));
            for (size_type i = 1; i < this->numElements; i++) {
                getChild(i)->collectChunks(res, part, iterator(this, static_cast<field_index_type>(i - 1)),
                        iterator(this, static_cast<field_index_type>(i)));
            }
            getChild(this->numElements)
                    ->collectChunks(res, num - (part * this->numElements),
                            iterator(this, static_cast<field_index_type>(this->numElements) - 1), end);

            // done
            return res;
        }

        /**
         * A function to verify the consistency of this node.
         *
         * @param root ... a reference to the root of the enclosing tree.
         * @return true if valid, false otherwise
         */
        template <typename Comp>
        bool check(Comp& comp, const node* root) const {
            bool valid = true;

            // check fill-state
            if (this->numElements > maxKeys || (this->parent != nullptr && this->numElements < minKeys)) {
                std::cout << "Node with " << this->numElements << "/" << maxKeys << " encountered!\n";
                valid = false;
            }

            // check root state
            if (root == this) {
                if (this->parent != nullptr) {
                    std::cout << "Root not properly linked!\n";
                    valid = false;
                }
            } else {
                // check parent relation
                if (!this->parent) {
                    std::cout << "Invalid null-parent!\n";
                    valid = false;
                } else {
                    if (this->parent->getChildren()[this->position] != this) {
                        std::cout << "Parent reference invalid!\n";
                        std::cout << "   Node:     " << this << "\n";
                        std::cout << "   Parent:   " << this->parent << "\n";
                        std::cout << "   Position: " << ((int)this->position) << "\n";
                        valid = false;
                    }

                    // check parent key
                    if (valid && this->position != 0 &&
                            !(comp(this->parent->keys[this->position - 1], keys[0]) < ((isSet) ? 0 : 1))) {
                        std::cout << "Left parent key not lower bound!\n";
                        std::cout << "   Node:     " << this << "\n";
                        std::cout << "   Parent:   " << this->parent << "\n";
                        std::cout << "   Position: " << ((int)this->position) << "\n";
                        std::cout << "   Key:   " << (this->parent->keys[this->position]) << "\n";
                        std::cout << "   Lower: " << (keys[0]) << "\n";
                        valid = false;
                    }

                    // check parent key
                    if (valid && this->position != this->parent->numElements &&
                            !(comp(keys[this->numElements - 1], this->parent->keys[this->position]) <
                                    ((isSet) ? 0 : 1))) {
                        std::cout << "Right parent key not lower bound!\n";
                        std::cout << "   Node:     " << this << "\n";
                        std::cout << "   Parent:   " << this->parent << "\n";
                        std::cout << "   Position: " << ((int)this->position) << "\n";
                        std::cout << "   Key:   " << (this->parent->keys[this->position]) << "\n";
                        std::cout << "   Upper: " << (keys[0]) << "\n";
                        valid = false;
                    }
                }
            }

            // check element order
            if (this->numElements > 0) {
                for (unsigned i = 0; i < this->numElements - 1; i++) {
                    if (valid && !(comp(keys[i], keys[i + 1]) < ((isSet) ? 0 : 1))) {
                        std::cout << "Element order invalid!\n";
                        std::cout << " @" << this << " key " << i << " is " << keys[i] << " vs "
                                  << keys[i + 1] << "\n";
                        valid = false;
                    }
                }
            }

            // check state of sub-nodes
            if (this->inner) {
                for (unsigned i = 0; i <= this->numElements; i++) {
                    valid &= getChildren()[i]->check(comp, root);
                }
            }

            return valid;
        }
    };  // namespace detail

    /**
     * The data type representing inner nodes of the b-tree. It extends
     * the generic implementation of a node by the storage locations
     * of child pointers.
     */
    struct inner_node : public node {
        // references to child nodes owned by this node
        node* children[node::maxKeys + 1];

        // a simple default constructor initializing member fields
        inner_node() : node(true) {}

        // clear up child nodes recursively
        ~inner_node() {
            for (unsigned i = 0; i <= this->numElements; ++i) {
                if (children[i] != nullptr) {
                    if (children[i]->isLeaf()) {
                        delete static_cast<leaf_node*>(children[i]);
                    } else {
                        delete static_cast<inner_node*>(children[i]);
                    }
                }
            }
        }
    };

    /**
     * The data type representing leaf nodes of the b-tree. It does not
     * add any capabilities to the generic node type.
     */
    struct leaf_node : public node {
        // a simple default constructor initializing member fields
        leaf_node() : node(false) {}
    };

    // ------------------- iterators ------------------------

public:
    /**
     * The iterator type to be utilized for scanning through btree instances.
     */
    class iterator {
        friend class souffle::detail::btree_delete<Key, Comparator, Allocator, blockSize, SearchStrategy,
                true, WeakComparator, Updater>;

        // a pointer to the node currently referred to
        // node const* cur;
        node* cur;

        // the index of the element currently addressed within the referenced node
        field_index_type pos = 0;

    public:
        using iterator_category = std::forward_iterator_tag;
        using value_type = Key;
        using difference_type = ptrdiff_t;
        using pointer = value_type*;
        using reference = value_type&;

        // default constructor -- creating an end-iterator
        iterator() : cur(nullptr) {}

        // creates an iterator referencing a specific element within a given node
        // iterator(node const* cur, field_index_type pos) : cur(cur), pos(pos) {}
        // iterator(node* cur, field_index_type pos) : cur(cur), pos(pos) {}
        iterator(node const* cur, field_index_type pos) : cur(const_cast<node*>(cur)), pos(pos) {}

        // a copy constructor
        iterator(const iterator& other) : cur(other.cur), pos(other.pos) {}

        // an assignment operator
        iterator& operator=(const iterator& other) {
            cur = other.cur;
            pos = other.pos;
            return *this;
        }

        // the equality operator as required by the iterator concept
        bool operator==(const iterator& other) const {
            return cur == other.cur && pos == other.pos;
        }

        // the not-equality operator as required by the iterator concept
        bool operator!=(const iterator& other) const {
            return !(*this == other);
        }

        // the deref operator as required by the iterator concept
        const Key& operator*() const {
            return cur->keys[pos];
        }

        // Resolve an ambiguous position at the end of a leaf by moving forward.
        // Must be called from the end of a leaf or behaviour is undefined.
        void resolvePosition() {
            // Save current node in case we are at the end of the tree
            auto temp = cur;

            // While we are at the end of node, move up to parent
            do {
                pos = cur->getPositionInParent();
                cur = cur->getParent();
            } while (cur && pos == cur->getNumElements());

            // Check if we were at the end of the tree.
            // If so, reset iterator
            if (!cur) {
                cur = temp;
                pos = static_cast<field_index_type>(cur->getNumElements());
            }
        }

        // the increment operator as required by the iterator concept
        iterator& operator++() {
            if (cur) {
                if (cur->isInner()) {
                    // Currently in an inner node so move forward one place
                    cur = cur->getChild(pos + 1);
                    while (cur->isInner()) {
                        cur = cur->getChild(0);
                    }
                    pos = 0;
                } else {
                    // In a leaf so just increment the position
                    ++pos;
                    // If we have reached the end of the leaf walk up to an inner node
                    if (pos == cur->getNumElements()) {
                        resolvePosition();
                    }
                }
            }
            return *this;
        }

        // the decrement operator as required by the iterator concept
        iterator& operator--() {
            if (cur) {
                if (cur->isInner()) {
                    // Currently in an inner node so move back one place
                    cur = cur->getChild(pos);
                    while (cur->isInner()) {
                        cur = cur->getChild(cur->getNumElements());
                    }
                    pos = static_cast<field_index_type>(cur->getNumElements()) - 1;
                } else {
                    // In a leaf so decrement the position
                    // Check if pos > 0 to avoid unsigned wrap-around issues
                    if (pos > 0) {
                        --pos;
                    } else {
                        // Save the current node in case we are at the beginning
                        auto temp = cur;

                        // Walk back up the tree.
                        do {
                            pos = cur->getPositionInParent();
                            cur = cur->getParent();
                        } while (cur && pos == 0);

                        // If we were at the beginning of the tree, reset the iterator
                        if (!cur) {
                            cur = temp;
                        }
                    }
                }
            }
            return *this;
        }

        // prints a textual representation of this iterator to the given stream (mainly for debugging)
        void print(std::ostream& out = std::cout) const {
            out << cur << "[" << (int)pos << "]";
        }
    };

    /**
     * A collection of operation hints speeding up some of the involved operations
     * by exploiting temporal locality.
     */
    template <unsigned size = 1>
    struct btree_operation_hints {
        using node_cache = LRUCache<node*, size>;

        // the node where the last insertion terminated
        node_cache last_insert;

        // the node where the last find-operation terminated
        node_cache last_find_end;

        // the node where the last lower-bound operation terminated
        node_cache last_lower_bound_end;

        // the node where the last upper-bound operation terminated
        node_cache last_upper_bound_end;

        // default constructor
        btree_operation_hints() = default;

        // resets all hints (to be triggered e.g. when deleting nodes)
        void clear() {
            last_insert.clear(nullptr);
            last_find_end.clear(nullptr);
            last_lower_bound_end.clear(nullptr);
            last_upper_bound_end.clear(nullptr);
        }
    };

    using operation_hints = btree_operation_hints<1>;

protected:
#ifdef IS_PARALLEL
    // a pointer to the root node of this tree
    node* volatile root;

    // a lock to synchronize update operations on the root pointer
    lock_type root_lock;
#else
    // a pointer to the root node of this tree
    node* root;

    // required to not duplicate too much code
    lock_type root_lock;
#endif

    // a pointer to the left-most node of this tree (initial note for iteration)
    leaf_node* leftmost;

    /* -------------- operator hint statistics ----------------- */

    // an aggregation of statistical values of the hint utilization
    struct hint_statistics {
        // the counter for insertion operations
        CacheAccessCounter inserts;

        // the counter for contains operations
        CacheAccessCounter contains;

        // the counter for lower_bound operations
        CacheAccessCounter lower_bound;

        // the counter for upper_bound operations
        CacheAccessCounter upper_bound;
    };

    // the hint statistic of this b-tree instance
    mutable hint_statistics hint_stats;

public:
    // the maximum number of keys stored per node
    static constexpr std::size_t max_keys_per_node = node::maxKeys;

    // -- ctors / dtors --

    // the default constructor creating an empty tree
    btree_delete(Comparator comp = Comparator(), WeakComparator weak_comp = WeakComparator())
            : comp(std::move(comp)), weak_comp(std::move(weak_comp)), root(nullptr), leftmost(nullptr) {}

    // a constructor creating a tree from the given iterator range
    template <typename Iter>
    btree_delete(const Iter& a, const Iter& b) : root(nullptr), leftmost(nullptr) {
        insert(a, b);
    }

    // a move constructor
    btree_delete(btree_delete&& other)
            : comp(other.comp), weak_comp(other.weak_comp), root(other.root), leftmost(other.leftmost) {
        other.root = nullptr;
        other.leftmost = nullptr;
    }

    // a copy constructor
    btree_delete(const btree_delete& set)
            : comp(set.comp), weak_comp(set.weak_comp), root(nullptr), leftmost(nullptr) {
        // use assignment operator for a deep copy
        *this = set;
    }

protected:
    /**
     * An internal constructor enabling the specific creation of a tree
     * based on internal parameters.
     */
    btree_delete(size_type /* size */, node* root, leaf_node* leftmost) : root(root), leftmost(leftmost) {}

public:
    // the destructor freeing all contained nodes
    ~btree_delete() {
        clear();
    }

    // -- mutators and observers --

    // emptiness check
    bool empty() const {
        return root == nullptr;
    }

    // determines the number of elements in this tree
    size_type size() const {
        return (root) ? root->countEntries() : 0;
    }

    /**
     * Inserts the given key into this tree.
     */
    bool insert(const Key& k) {
        operation_hints hints;
        return insert(k, hints);
    }

    /**
     * Inserts the given key into this tree.
     */
    bool insert(const Key& k, operation_hints& hints) {
#ifdef IS_PARALLEL

        // special handling for inserting first element
        while (root == nullptr) {
            // try obtaining root-lock
            if (!root_lock.try_start_write()) {
                // somebody else was faster => re-check
                continue;
            }

            // check loop condition again
            if (root != nullptr) {
                // somebody else was faster => normal insert
                root_lock.end_write();
                break;
            }

            // create new node
            leftmost = new leaf_node();
            leftmost->numElements = 1;
            leftmost->keys[0] = k;
            root = leftmost;

            // operation complete => we can release the root lock
            root_lock.end_write();

            hints.last_insert.access(leftmost);

            return true;
        }

        // insert using iterative implementation

        node* cur = nullptr;

        // test last insert hints
        lock_type::Lease cur_lease;

        auto checkHint = [&](node* last_insert) {
            // ignore null pointer
            if (!last_insert) return false;
            // get a read lease on indicated node
            auto hint_lease = last_insert->lock.start_read();
            // check whether it covers the key
            if (!weak_covers(last_insert, k)) return false;
            // and if there was no concurrent modification
            if (!last_insert->lock.validate(hint_lease)) return false;
            // use hinted location
            cur = last_insert;
            // and keep lease
            cur_lease = hint_lease;
            // we found a hit
            return true;
        };

        if (hints.last_insert.any(checkHint)) {
            // register this as a hit
            hint_stats.inserts.addHit();
        } else {
            // register this as a miss
            hint_stats.inserts.addMiss();
        }

        // if there is no valid hint ..
        if (!cur) {
            do {
                // get root - access lock
                auto root_lease = root_lock.start_read();

                // start with root
                cur = root;

                // get lease of the next node to be accessed
                cur_lease = cur->lock.start_read();

                // check validity of root pointer
                if (root_lock.end_read(root_lease)) {
                    break;
                }

            } while (true);
        }

        while (true) {
            // handle inner nodes
            if (cur->inner) {
                auto a = &(cur->keys[0]);
                auto b = &(cur->keys[cur->numElements]);

                auto pos = search.lower_bound(k, a, b, weak_comp);
                auto idx = pos - a;

                // early exit for sets
                if (isSet && pos != b && weak_equal(*pos, k)) {
                    // validate results
                    if (!cur->lock.validate(cur_lease)) {
                        // start over again
                        return insert(k, hints);
                    }

                    // update provenance information
                    if (typeid(Comparator) != typeid(WeakComparator)) {
                        if (!cur->lock.try_upgrade_to_write(cur_lease)) {
                            // start again
                            return insert(k, hints);
                        }
                        bool updated = update(*pos, k);
                        cur->lock.end_write();
                        return updated;
                    }

                    // we found the element => no check of lock necessary
                    return false;
                }

                // get next pointer
                auto next = cur->getChild(idx);

                // get lease on next level
                auto next_lease = next->lock.start_read();

                // check whether there was a write
                if (!cur->lock.end_read(cur_lease)) {
                    // start over
                    return insert(k, hints);
                }

                // go to next
                cur = next;

                // move on lease
                cur_lease = next_lease;

                continue;
            }

            // the rest is for leaf nodes
            assert(!cur->inner);

            // -- insert node in leaf node --

            auto a = &(cur->keys[0]);
            auto b = &(cur->keys[cur->numElements]);

            auto pos = search.upper_bound(k, a, b, weak_comp);
            auto idx = pos - a;

            // early exit for sets
            if (isSet && pos != a && weak_equal(*(pos - 1), k)) {
                // validate result
                if (!cur->lock.validate(cur_lease)) {
                    // start over again
                    return insert(k, hints);
                }

                // update provenance information
                if (typeid(Comparator) != typeid(WeakComparator)) {
                    if (!cur->lock.try_upgrade_to_write(cur_lease)) {
                        // start again
                        return insert(k, hints);
                    }
                    bool updated = update(*(pos - 1), k);
                    cur->lock.end_write();
                    return updated;
                }

                // we found the element => done
                return false;
            }

            // upgrade to write-permission
            if (!cur->lock.try_upgrade_to_write(cur_lease)) {
                // something has changed => restart
                hints.last_insert.access(cur);
                return insert(k, hints);
            }

            if (cur->numElements >= node::maxKeys) {
                // -- lock parents --
                auto priv = cur;
                auto parent = priv->parent;
                std::vector<node*> parents;
                do {
                    if (parent) {
                        parent->lock.start_write();
                        while (true) {
                            // check whether parent is correct
                            if (parent == priv->parent) {
                                break;
                            }
                            // switch parent
                            parent->lock.abort_write();
                            parent = priv->parent;
                            parent->lock.start_write();
                        }
                    } else {
                        // lock root lock => since cur is root
                        root_lock.start_write();
                    }

                    // record locked node
                    parents.push_back(parent);

                    // stop at "sphere of influence"
                    if (!parent || !parent->isFull()) {
                        break;
                    }

                    // go one step higher
                    priv = parent;
                    parent = parent->parent;

                } while (true);

                // split this node
                auto old_root = root;
                idx -= cur->rebalance_or_split(
                        const_cast<node**>(&root), root_lock, static_cast<int>(idx), parents);

                // release parent lock
                for (auto it = parents.rbegin(); it != parents.rend(); ++it) {
                    auto parent = *it;

                    // release this lock
                    if (parent) {
                        parent->lock.end_write();
                    } else {
                        if (old_root != root) {
                            root_lock.end_write();
                        } else {
                            root_lock.abort_write();
                        }
                    }
                }

                // insert element in right fragment
                if (((size_type)idx) > cur->numElements) {
                    // release current lock
                    cur->lock.end_write();

                    // insert in sibling
                    return insert(k, hints);
                }
            }

            // ok - no split necessary
            assert(cur->numElements < node::maxKeys && "Split required!");

            // move keys
            for (int j = static_cast<int>(cur->numElements); j > static_cast<int>(idx); --j) {
                cur->keys[j] = cur->keys[j - 1];
            }

            // insert new element
            cur->keys[idx] = k;
            cur->numElements++;

            // release lock on current node
            cur->lock.end_write();

            // remember last insertion position
            hints.last_insert.access(cur);
            return true;
        }

#else
        // special handling for inserting first element
        if (empty()) {
            // create new node
            leftmost = new leaf_node();
            leftmost->numElements = 1;
            leftmost->keys[0] = k;
            root = leftmost;

            hints.last_insert.access(leftmost);

            return true;
        }

        // insert using iterative implementation
        node* cur = root;

        auto checkHints = [&](node* last_insert) {
            if (!last_insert) return false;
            if (!weak_covers(last_insert, k)) return false;
            cur = last_insert;
            return true;
        };

        // test last insert
        if (hints.last_insert.any(checkHints)) {
            hint_stats.inserts.addHit();
        } else {
            hint_stats.inserts.addMiss();
        }

        while (true) {
            // handle inner nodes
            if (cur->inner) {
                auto a = &(cur->keys[0]);
                auto b = &(cur->keys[cur->numElements]);

                auto pos = search.lower_bound(k, a, b, weak_comp);
                auto idx = pos - a;

                // early exit for sets
                if (isSet && pos != b && weak_equal(*pos, k)) {
                    // update provenance information
                    if (typeid(Comparator) != typeid(WeakComparator)) {
                        return update(*pos, k);
                    }

                    return false;
                }

                cur = cur->getChild(idx);
                continue;
            }

            // the rest is for leaf nodes
            assert(!cur->inner);

            // -- insert node in leaf node --

            auto a = &(cur->keys[0]);
            auto b = &(cur->keys[cur->numElements]);

            auto pos = search.upper_bound(k, a, b, weak_comp);
            auto idx = pos - a;

            // early exit for sets
            if (isSet && pos != a && weak_equal(*(pos - 1), k)) {
                // update provenance information
                if (typeid(Comparator) != typeid(WeakComparator)) {
                    return update(*(pos - 1), k);
                }

                return false;
            }

            if (cur->numElements >= node::maxKeys) {
                // split this node
                idx -= cur->rebalance_or_split(&root, root_lock, static_cast<int>(idx));

                // insert element in right fragment
                if (((size_type)idx) > cur->numElements) {
                    idx -= cur->numElements + 1;
                    cur = cur->parent->getChild(cur->position + 1);
                }
            }

            // ok - no split necessary
            assert(cur->numElements < node::maxKeys && "Split required!");

            // move keys
            for (int j = static_cast<int>(cur->numElements); j > idx; --j) {
                cur->keys[j] = cur->keys[j - 1];
            }

            // insert new element
            cur->keys[idx] = k;
            cur->numElements++;

            // remember last insertion position
            hints.last_insert.access(cur);

            return true;
        }
#endif
    }

    /**
     * Inserts the given range of elements into this tree.
     */
    template <typename Iter>
    void insert(const Iter& a, const Iter& b) {
        // TODO: improve this beyond a naive insert
        operation_hints hints;
        // a naive insert so far .. seems to work fine
        for (auto it = a; it != b; ++it) {
            // use insert with hint
            insert(*it, hints);
        }
    }

    /**
     * Compute the number of instances of a key in the tree
     */
    size_type get_count(const Key& k) const {
        if (empty()) {
            return 0;
        }
        if (isSet) {
            auto iter = internal_find(k);
            if (iter != end()) {
                return 1;
            } else {
                return 0;
            }
        } else {
            auto lower_iter = internal_lower_bound(k);
            if (lower_iter != end() && equal(*lower_iter, k)) {
                return std::distance(lower_iter, internal_upper_bound(k));
            } else {
                return 0;
            }
        }
    }

    /**
     * Erase the given key from the tree.
     * Return the number of erased keys.
     */
    size_type erase(const Key& k) {
        if (empty()) {
            return 0;
        }
        if (isSet) {
            iterator iter = internal_find(k);
            if (iter == end()) {
                // Key not found
                return 0;
            } else {
                erase(iter);
                return 1;
            }
        } else {
            iterator lower_iter = internal_lower_bound(k);
            if (lower_iter != end() && equal(*lower_iter, k)) {
                size_type count = std::distance(lower_iter, internal_upper_bound(k));
                for (size_type i = 0; i < count; i++) {
                    erase(lower_iter);
                }
                return count;
            } else {
                return 0;
            }
        }
    }

    /**
     * Erase the key pointed to by the iterator.
     * Advance the iterator to the next position.
     */
    void erase(iterator& iter) {
        bool internal_delete = false;
        // @julienhenry
        // iter.cur->lock.start_write();
        if (iter.cur->isInner()) {
            // In an inner node so swap key with previous key
            iterator temp_iter(iter);
            --iter;
            Key temp_key = temp_iter.cur->keys[temp_iter.pos];
            temp_iter.cur->keys[temp_iter.pos] = iter.cur->keys[iter.pos];
            iter.cur->keys[iter.pos] = temp_key;
            internal_delete = true;
        }
        // Now on a leaf node
        assert(iter.cur->isLeaf());

        // Delete the key, move other keys backwards and update size
        iter.cur->keys[iter.pos].~Key();
        for (size_type i = iter.pos + 1; i < iter.cur->getNumElements(); ++i) {
            iter.cur->keys[i - 1] = iter.cur->keys[i];
        }
        iter.cur->numElements--;

        // Next, ensure nodes have not become too small
        iterator res(iter);
        while (true) {
            auto parent = iter.cur->parent;
            if (!parent) {
                // cur is root
                if (iter.cur->getNumElements() == 0) {
                    // Root has become empty
                    if (iter.cur->isLeaf()) {
                        // Whole tree has become empty
                        root = nullptr;
                        leftmost = nullptr;
                        res.cur = nullptr;
                        res.pos = 0;
                        delete static_cast<leaf_node*>(iter.cur);
                    } else {
                        // Whole tree now contained in child at position 0
                        root = iter.cur->getChild(0);
                        root->parent = nullptr;
                        for (unsigned i = 0; i <= iter.cur->asInnerNode().numElements; ++i) {
                            iter.cur->asInnerNode().children[i] = nullptr;
                        }
                        delete static_cast<inner_node*>(iter.cur);
                    }
                }
                break;
            }
            if (iter.cur->getNumElements() >= node::minKeys) {
                break;
            }
            bool merged = merge_or_rebalance(iter);
            if (iter.cur->isLeaf()) {
                res = iter;
            }
            if (!merged) {
                break;
            }
            iter.cur = iter.cur->getParent();
        }
        iter = res;

        // Finally, check the iterator points to the right position
        if (iter.cur) {
            // Tree hasn't become empty
            // If iterator is at end of node, resolve the position
            if (iter.pos == iter.cur->getNumElements()) {
                iter.resolvePosition();
            }

            // If we deleted internally, increment the iterator
            if (internal_delete) {
                ++iter;
            }
        }
        // iter.cur->lock.end_write(); //@julienhenry
    }

private:
    /**
     * Find the given key in a non-empty tree.
     * If found, return an iterator pointing to the key.
     * Otherwise, return end()
     */
    iterator internal_find(const Key& k) const {
        auto iter = iterator(root, 0);
        while (true) {
            auto a = &(iter.cur->keys[0]);
            auto b = &(iter.cur->keys[iter.cur->numElements]);

            auto pos = search(k, a, b, comp);
            iter.pos = static_cast<field_index_type>(pos - a);

            if (pos < b && equal(*pos, k)) {
                return iter;
            }

            if (!iter.cur->inner) {
                return end();
            }

            // continue search in child node
            iter.cur = iter.cur->getChild(iter.pos);
        }
    }

    /**
     * Find the first key in the tree greater or equal to the given key.
     * If found, return an iterator pointing to the key.
     * Otherwise, return end().
     */
    iterator internal_lower_bound(const Key& k) const {
        iterator iter = iterator(root, 0);
        iterator res;
        while (true) {
            auto a = &(iter.cur->keys[0]);
            auto b = &(iter.cur->keys[iter.cur->numElements]);

            auto pos = search.lower_bound(k, a, b, comp);
            iter.pos = static_cast<field_index_type>(pos - a);

            if (pos < b) {
                res = iter;
                if (isSet && equal(*pos, k)) {
                    // Early exit for sets
                    break;
                }
            }

            if (!iter.cur->inner) {
                break;
            }

            iter.cur = iter.cur->getChild(iter.pos);
        }
        if (!res.cur) {
            res = iter;
        }
        return res;
    }

    /**
     * Find the first key in the tree strictly greater than the given key.
     * If found, return an iterator pointing to the key.
     * Otherwise, return end().
     */
    iterator internal_upper_bound(const Key& k) const {
        iterator iter = iterator(root, 0);
        iterator res;
        while (true) {
            auto a = &(iter.cur->keys[0]);
            auto b = &(iter.cur->keys[iter.cur->numElements]);

            auto pos = search.upper_bound(k, a, b, comp);

            iter.pos = static_cast<field_index_type>(pos - a);

            if (pos < b) {
                res = iter;
            }

            if (!iter.cur->inner) {
                break;
            }

            iter.cur = iter.cur->getChild(iter.pos);
        }
        if (!res.cur) {
            res = iter;
        }
        return res;
    }

    /**
     * Merge or rebalance the current node of the iterator.
     * Update the iterator to point to its new position.
     * Return true if a merge occured, else false.
     */
    bool merge_or_rebalance(iterator& iter) {
        // Only called when the current node is too small
        assert(iter.cur->getNumElements() < node::minKeys);

        auto parent = iter.cur->getParent();
        auto siblings = parent->getChildren();
        auto pos = iter.cur->getPositionInParent();
        if (pos < parent->getNumElements()) {
            // Has right sibling
            auto right = siblings[pos + 1];
            if (iter.cur->getNumElements() + right->getNumElements() + 1 <= node::maxKeys) {
                // Merge with right sibling
                merge_with_right_sibling(iter, right);
                return true;
            } else if (pos > 0) {
                // Has a left sibling
                auto left = siblings[pos - 1];
                if (left->getNumElements() + iter.cur->getNumElements() + 1 <= node::maxKeys) {
                    // Merge into left sibling
                    merge_into_left_sibling(left, iter);
                    return true;
                } else {
                    // Rebalance from left sibling
                    rebalance_from_left_sibling(left, iter);
                    return false;
                }
            } else {
                // Can't merge with right and no left sibling so must rebalance from right
                rebalance_from_right_sibling(iter, right);
                return false;
            }
        } else {
            // No right sibling, so must have a left sibling
            assert(pos > 0);
            auto left = siblings[pos - 1];
            if (left->getNumElements() + iter.cur->getNumElements() + 1 <= node::maxKeys) {
                // Merge into left sibling
                merge_into_left_sibling(left, iter);
                return true;
            } else {
                // Rebalance from left sibling
                rebalance_from_left_sibling(left, iter);
                return false;
            }
        }
    }

    /**
     * Merge an iterator with its right sibling, updating the position of the iterator
     */
    void merge_with_right_sibling(iterator& iter, node* right) {
        merge(iter.cur, right);
    }

    /**
     * Merge an iterator into its left sibling, updating the position of the iterator
     */
    void merge_into_left_sibling(node* left, iterator& iter) {
        auto left_size = left->getNumElements();
        merge(left, iter.cur);
        iter.cur = left;
        iter.pos += static_cast<field_index_type>(left_size) + 1;
    }

    /**
     * Merge nodes, destroying the sibling on the right.
     */
    void merge(node* left, node* right) {
        auto parent = left->getParent();
        // Left must have a parent
        assert(parent);
        auto siblings = parent->getChildren();

        auto pos = left->getPositionInParent();
        // Node isn't the right-most node in its parent
        assert(pos < parent->getNumElements());

        // Update the parent node by:
        // 1. Moving dividing key to left node
        left->keys[left->getNumElements()] = parent->keys[pos];
        // 2. Moving keys and siblings found to the right of the
        // dividing key back one place
        for (size_type i = pos + 1; i < parent->getNumElements(); ++i) {
            parent->keys[i - 1] = parent->keys[i];
            auto sibling = siblings[i + 1];
            sibling->position--;
            siblings[i] = sibling;
        }
        // 3. Decrementing its size
        parent->numElements--;

        // Move keys from right node to left
        for (size_type i = left->getNumElements() + 1, j = 0; j < right->getNumElements(); ++i, ++j) {
            left->keys[i] = right->keys[j];
        }

        // If left is an inner node, move children from right to left
        if (left->isInner()) {
            // Right must also be an inner node
            assert(right->isInner());
            auto left_children = left->getChildren();
            auto right_children = right->getChildren();
            for (size_type i = left->getNumElements() + 1, j = 0; j <= right->getNumElements(); ++i, ++j) {
                auto child = right_children[j];
                child->parent = left;
                child->position = static_cast<field_index_type>(i);
                left_children[i] = child;
            }
        }

        // Update the number of elements in the left
        left->numElements += right->getNumElements() + 1;

        // Delete the right node
        if (right->isLeaf()) {
            delete static_cast<leaf_node*>(right);
        } else {
            for (unsigned i = 0; i <= right->asInnerNode().numElements; ++i) {
                right->asInnerNode().children[i] = nullptr;
            }
            delete static_cast<inner_node*>(right);
        }
    }

    /**
     * Rebalance the given iterator node by moving keys from the right.
     * Update the iterator position.
     */
    void rebalance_from_right_sibling(iterator& iter, node* right) {
        auto left = iter.cur;
        auto parent = left->getParent();
        // Left must have a parent
        assert(parent);

        auto pos = left->getPositionInParent();
        // Node isn't the right-most node in its parent
        assert(pos < parent->getNumElements());

        // Number of keys to move
        size_type to_move = (right->getNumElements() - node::minKeys) / 2 + 1;

        // Move down dividing key from parent
        left->keys[left->getNumElements()] = parent->keys[pos];

        // Move keys from right sibling
        for (size_type i = left->getNumElements() + 1, j = 0; j < to_move - 1; ++i, ++j) {
            left->keys[i] = right->keys[j];
        }

        // Move key up to dividing position
        parent->keys[pos] = right->keys[to_move - 1];

        // Move remaining keys in right node back
        for (size_type i = to_move; i < right->getNumElements(); ++i) {
            right->keys[i - to_move] = right->keys[i];
        }

        // If left is an inner node, move children
        if (left->isInner()) {
            // Right must also be an inner node
            assert(right->isInner());
            auto left_children = left->getChildren();
            auto right_children = right->getChildren();

            // Move children from right node to left
            for (size_type i = left->getNumElements() + 1, j = 0; j < to_move; ++i, ++j) {
                auto child = right_children[j];
                child->parent = left;
                child->position = static_cast<field_index_type>(i);
                left_children[i] = child;
            }

            // Move right children back
            for (size_type i = to_move; i <= right->getNumElements(); ++i) {
                auto child = right_children[i];
                child->position = static_cast<field_index_type>(i - to_move);
                right_children[i - to_move] = child;
            }
        }

        // Update sizes
        left->numElements += to_move;
        right->numElements -= to_move;
    }

    /**
     * Rebalance the given iterator node by moving keys from the left sibling.
     * Update the iterator to its new position.
     */
    void rebalance_from_left_sibling(node* left, iterator& iter) {
        auto right = iter.cur;
        auto parent = right->getParent();
        // Left must have a parent
        assert(parent);

        auto pos = right->getPositionInParent();
        // Node isn't the left-most node in its parent
        assert(pos > 0);

        // Number of keys to move
        size_type to_move = (left->getNumElements() - node::minKeys) / 2 + 1;

        // Move keys in right node along
        for (size_type i = right->getNumElements() + to_move - 1; i >= to_move; --i) {
            right->keys[i] = right->keys[i - to_move];
        }

        // Move down dividing key from parent
        right->keys[to_move - 1] = parent->keys[pos - 1];

        // Move keys from left sibling
        for (size_type i = left->getNumElements() - to_move + 1, j = 0; j < to_move - 1; ++i, ++j) {
            right->keys[j] = left->keys[i];
        }

        // Move key up to dividing position
        parent->keys[pos - 1] = left->keys[left->getNumElements() - to_move];

        // If right is an inner node, move children
        if (right->isInner()) {
            // Left must also be an inner node
            assert(left->isInner());
            auto left_children = left->getChildren();
            auto right_children = right->getChildren();

            // Move right children along
            for (size_type i = right->getNumElements() + to_move; i >= to_move; --i) {
                auto child = right_children[i - to_move];
                child->position = static_cast<field_index_type>(i);
                right_children[i] = child;
            }

            // Move children from left node to right
            for (size_type i = left->getNumElements() - to_move + 1, j = 0; j < to_move; ++i, ++j) {
                auto child = left_children[i];
                child->parent = right;
                child->position = static_cast<field_index_type>(j);
                right_children[j] = child;
            }
        }

        // Update iterator position
        iter.pos += static_cast<field_index_type>(to_move);

        // Update sizes
        left->numElements -= to_move;
        right->numElements += to_move;
    }

public:
    /**
     * Return the rightmost node in the tree.
     * Currently inefficient as tree contains no reference to rightmost.
     */
    node* rightmost() const {
        auto rightmost = root;
        if (rightmost) {
            while (rightmost->isInner()) {
                rightmost = rightmost->getChild(rightmost->getNumElements());
            }
        }
        return rightmost;
    }

    // Obtains an iterator referencing the first element of the tree.
    iterator begin() const {
        return iterator(leftmost, 0);
    }

    // Obtains an iterator referencing the position after the last element of the tree.
    iterator end() const {
        node* rightmost = this->rightmost();
        if (rightmost) {
            return iterator(rightmost, static_cast<field_index_type>(rightmost->getNumElements()));
        } else {
            return iterator();
        }
    }

    /**
     * Partitions the full range of this set into up to a given number of chunks.
     * The chunks will cover approximately the same number of elements. Also, the
     * number of chunks will only approximate the desired number of chunks.
     *
     * @param num .. the number of chunks requested
     * @return a list of chunks partitioning this tree
     */
    std::vector<chunk> partition(size_type num) const {
        return getChunks(num);
    }

    std::vector<chunk> getChunks(size_type num) const {
        std::vector<chunk> res;
        if (empty()) {
            return res;
        }
        return root->collectChunks(res, num, begin(), end());
    }

    /**
     * Determines whether the given element is a member of this tree.
     */
    bool contains(const Key& k) const {
        operation_hints hints;
        return contains(k, hints);
    }

    /**
     * Determines whether the given element is a member of this tree.
     */
    bool contains(const Key& k, operation_hints& hints) const {
        return find(k, hints) != end();
    }

    /**
     * Locates the given key within this tree and returns an iterator
     * referencing its position. If not found, an end-iterator will be returned.
     */
    iterator find(const Key& k) const {
        operation_hints hints;
        return find(k, hints);
    }

    /**
     * Locates the given key within this tree and returns an iterator
     * referencing its position. If not found, an end-iterator will be returned.
     */
    iterator find(const Key& k, operation_hints& hints) const {
        if (empty()) {
            return end();
        }

        node* cur = root;

        auto checkHints = [&](node* last_find_end) {
            if (!last_find_end) return false;
            if (!covers(last_find_end, k)) return false;
            cur = last_find_end;
            return true;
        };

        // test last location searched (temporal locality)
        if (hints.last_find_end.any(checkHints)) {
            // register it as a hit
            hint_stats.contains.addHit();
        } else {
            // register it as a miss
            hint_stats.contains.addMiss();
        }

        // an iterative implementation (since 2/7 faster than recursive)

        while (true) {
            auto a = &(cur->keys[0]);
            auto b = &(cur->keys[cur->numElements]);

            auto pos = search(k, a, b, comp);

            if (pos < b && equal(*pos, k)) {
                hints.last_find_end.access(cur);
                return iterator(cur, static_cast<field_index_type>(pos - a));
            }

            if (!cur->inner) {
                hints.last_find_end.access(cur);
                return end();
            }

            // continue search in child node
            cur = cur->getChild(pos - a);
        }
    }

    /**
     * Obtains a lower boundary for the given key -- hence an iterator referencing
     * the smallest value that is not less the given key. If there is no such element,
     * an end-iterator will be returned.
     */
    iterator lower_bound(const Key& k) const {
        operation_hints hints;
        return lower_bound(k, hints);
    }

    /**
     * Obtains a lower boundary for the given key -- hence an iterator referencing
     * the smallest value that is not less the given key. If there is no such element,
     * an end-iterator will be returned.
     */
    iterator lower_bound(const Key& k, operation_hints& hints) const {
        if (empty()) {
            return end();
        }

        node* cur = root;

        auto checkHints = [&](node* last_lower_bound_end) {
            if (!last_lower_bound_end) return false;
            if (!covers(last_lower_bound_end, k)) return false;
            cur = last_lower_bound_end;
            return true;
        };

        // test last searched node
        if (hints.last_lower_bound_end.any(checkHints)) {
            hint_stats.lower_bound.addHit();
        } else {
            hint_stats.lower_bound.addMiss();
        }

        iterator res = end();
        while (true) {
            auto a = &(cur->keys[0]);
            auto b = &(cur->keys[cur->numElements]);

            auto pos = search.lower_bound(k, a, b, comp);
            auto idx = static_cast<field_index_type>(pos - a);

            if (!cur->inner) {
                hints.last_lower_bound_end.access(cur);
                return (pos != b) ? iterator(cur, idx) : res;
            }

            if (isSet && pos != b && equal(*pos, k)) {
                return iterator(cur, idx);
            }

            if (pos != b) {
                res = iterator(cur, idx);
            }

            cur = cur->getChild(idx);
        }
    }

    /**
     * Obtains an upper boundary for the given key -- hence an iterator referencing
     * the first element that the given key is less than the referenced value. If
     * there is no such element, an end-iterator will be returned.
     */
    iterator upper_bound(const Key& k) const {
        operation_hints hints;
        return upper_bound(k, hints);
    }

    /**
     * Obtains an upper boundary for the given key -- hence an iterator referencing
     * the first element that the given key is less than the referenced value. If
     * there is no such element, an end-iterator will be returned.
     */
    iterator upper_bound(const Key& k, operation_hints& hints) const {
        if (empty()) {
            return end();
        }

        node* cur = root;

        auto checkHints = [&](node* last_upper_bound_end) {
            if (!last_upper_bound_end) return false;
            if (!coversUpperBound(last_upper_bound_end, k)) return false;
            cur = last_upper_bound_end;
            return true;
        };

        // test last search node
        if (hints.last_upper_bound_end.any(checkHints)) {
            hint_stats.upper_bound.addHit();
        } else {
            hint_stats.upper_bound.addMiss();
        }

        iterator res = end();
        while (true) {
            auto a = &(cur->keys[0]);
            auto b = &(cur->keys[cur->numElements]);

            auto pos = search.upper_bound(k, a, b, comp);
            auto idx = static_cast<field_index_type>(pos - a);

            if (!cur->inner) {
                hints.last_upper_bound_end.access(cur);
                return (pos != b) ? iterator(cur, idx) : res;
            }

            if (pos != b) {
                res = iterator(cur, idx);
            }

            cur = cur->getChild(idx);
        }
    }

    /**
     * Clears this tree.
     */
    void clear() {
        if (root != nullptr) {
            if (root->isLeaf()) {
                delete static_cast<leaf_node*>(root);
            } else {
                delete static_cast<inner_node*>(root);
            }
        }
        root = nullptr;
        leftmost = nullptr;
    }

    /**
     * Swaps the content of this tree with the given tree. This
     * is a much more efficient operation than creating a copy and
     * realizing the swap utilizing assignment operations.
     */
    void swap(btree_delete& other) {
        // swap the content
        std::swap(root, other.root);
        std::swap(leftmost, other.leftmost);
    }

    // Implementation of the assignment operation for trees.
    btree_delete& operator=(const btree_delete& other) {
        // check identity
        if (this == &other) {
            return *this;
        }

        // create a deep-copy of the content of the other tree
        // shortcut for empty sets
        if (other.empty()) {
            return *this;
        }

        // clone content (deep copy)
        root = other.root->clone();

        // update leftmost reference
        auto tmp = root;
        while (!tmp->isLeaf()) {
            tmp = tmp->getChild(0);
        }
        leftmost = static_cast<leaf_node*>(tmp);

        // done
        return *this;
    }

    // Implementation of an equality operation for trees.
    bool operator==(const btree_delete& other) const {
        // check identity
        if (this == &other) {
            return true;
        }

        // check size
        if (size() != other.size()) {
            return false;
        }
        if (size() < other.size()) {
            return other == *this;
        }

        // check content
        for (const auto& key : other) {
            if (!contains(key)) {
                return false;
            }
        }
        return true;
    }

    // Implementation of an inequality operation for trees.
    bool operator!=(const btree_delete& other) const {
        return !(*this == other);
    }

    // -- for debugging --

    // Determines the number of levels contained in this tree.
    size_type getDepth() const {
        return (empty()) ? 0 : root->getDepth();
    }

    // Determines the number of nodes contained in this tree.
    size_type getNumNodes() const {
        return (empty()) ? 0 : root->countNodes();
    }

    // Determines the amount of memory used by this data structure
    size_type getMemoryUsage() const {
        return sizeof(*this) + (empty() ? 0 : root->getMemoryUsage());
    }

    /*
     * Prints a textual representation of this tree to the given
     * output stream (mostly for debugging and tuning).
     */
    void printTree(std::ostream& out = std::cout) const {
        out << "B-Tree with " << size() << " elements:\n";
        if (empty()) {
            out << " - empty - \n";
        } else {
            root->printTree(out, "");
        }
    }

    /**
     * Prints a textual summary of statistical properties of this
     * tree to the given output stream (for debugging and tuning).
     */
    void printStats(std::ostream& out = std::cout) const {
        auto nodes = getNumNodes();
        out << " ---------------------------------\n";
        out << "  Elements: " << size() << "\n";
        out << "  Depth:    " << (empty() ? 0 : root->getDepth()) << "\n";
        out << "  Nodes:    " << nodes << "\n";
        out << " ---------------------------------\n";
        out << "  Size of inner node: " << sizeof(inner_node) << "\n";
        out << "  Size of leaf node:  " << sizeof(leaf_node) << "\n";
        out << "  Size of Key:        " << sizeof(Key) << "\n";
        out << "  max keys / node:  " << node::maxKeys << "\n";
        out << "  avg keys / node:  " << (size() / (double)nodes) << "\n";
        out << "  avg filling rate: " << ((size() / (double)nodes) / node::maxKeys) << "\n";
        out << " ---------------------------------\n";
        out << "  insert-hint (hits/misses/total): " << hint_stats.inserts.getHits() << "/"
            << hint_stats.inserts.getMisses() << "/" << hint_stats.inserts.getAccesses() << "\n";
        out << "  contains-hint(hits/misses/total):" << hint_stats.contains.getHits() << "/"
            << hint_stats.contains.getMisses() << "/" << hint_stats.contains.getAccesses() << "\n";
        out << "  lower-bound-hint (hits/misses/total):" << hint_stats.lower_bound.getHits() << "/"
            << hint_stats.lower_bound.getMisses() << "/" << hint_stats.lower_bound.getAccesses() << "\n";
        out << "  upper-bound-hint (hits/misses/total):" << hint_stats.upper_bound.getHits() << "/"
            << hint_stats.upper_bound.getMisses() << "/" << hint_stats.upper_bound.getAccesses() << "\n";
        out << " ---------------------------------\n";
    }

    /**
     * Checks the consistency of this tree.
     */
    bool check() {
        auto ok = empty() || root->check(comp, root);
        if (!ok) {
            printTree();
        }
        return ok;
    }

    /**
     * A static member enabling the bulk-load of ordered data into an empty
     * tree. This function is much more efficient in creating a index over
     * an ordered set of elements than an iterative insertion of values.
     *
     * @tparam Iter .. the type of iterator specifying the range
     *                     it must be a random-access iterator
     */
    template <typename R, typename Iter>
    static typename std::enable_if<std::is_same<typename std::iterator_traits<Iter>::iterator_category,
                                           std::random_access_iterator_tag>::value,
            R>::type
    load(const Iter& a, const Iter& b) {
        // quick exit - empty range
        if (a == b) {
            return R();
        }

        // resolve tree recursively
        auto root = buildSubTree(a, b - 1);

        // find leftmost node
        node* leftmost = root;
        while (!leftmost->isLeaf()) {
            leftmost = leftmost->getChild(0);
        }

        // build result
        return R(b - a, root, static_cast<leaf_node*>(leftmost));
    }

protected:
    /**
     * Determines whether the range covered by the given node is also
     * covering the given key value.
     */
    bool covers(const node* node, const Key& k) const {
        if (isSet) {
            // in sets we can include the ends as covered elements
            return !node->isEmpty() && !less(k, node->keys[0]) && !less(node->keys[node->numElements - 1], k);
        }
        // in multi-sets the ends may not be completely covered
        return !node->isEmpty() && less(node->keys[0], k) && less(k, node->keys[node->numElements - 1]);
    }

    /**
     * Determines whether the range covered by the given node is also
     * covering the given key value.
     */
    bool weak_covers(const node* node, const Key& k) const {
        if (isSet) {
            // in sets we can include the ends as covered elements
            return !node->isEmpty() && !weak_less(k, node->keys[0]) &&
                   !weak_less(node->keys[node->numElements - 1], k);
        }
        // in multi-sets the ends may not be completely covered
        return !node->isEmpty() && weak_less(node->keys[0], k) &&
               weak_less(k, node->keys[node->numElements - 1]);
    }

private:
    /**
     * Determines whether the range covered by this node covers
     * the upper bound of the given key.
     */
    bool coversUpperBound(const node* node, const Key& k) const {
        // ignore edges
        return !node->isEmpty() && !less(k, node->keys[0]) && less(k, node->keys[node->numElements - 1]);
    }

    // Utility function for the load operation above.
    template <typename Iter>
    static node* buildSubTree(const Iter& a, const Iter& b) {
        const int N = node::maxKeys;

        // divide range in N+1 sub-ranges
        int length = (b - a) + 1;

        // terminal case: length is less then maxKeys
        if (length <= N) {
            // create a leaf node
            node* res = new leaf_node();
            res->numElements = length;

            for (int i = 0; i < length; ++i) {
                res->keys[i] = a[i];
            }

            return res;
        }

        // recursive case - compute step size
        int numKeys = N;
        int step = ((length - numKeys) / (numKeys + 1));

        while (numKeys > 1 && (step < N / 2)) {
            numKeys--;
            step = ((length - numKeys) / (numKeys + 1));
        }

        // create inner node
        node* res = new inner_node();
        res->numElements = numKeys;

        Iter c = a;
        for (int i = 0; i < numKeys; i++) {
            // get dividing key
            res->keys[i] = c[step];

            // get sub-tree
            auto child = buildSubTree(c, c + (step - 1));
            child->parent = res;
            child->position = i;
            res->getChildren()[i] = child;

            c = c + (step + 1);
        }

        // and the remaining part
        auto child = buildSubTree(c, b);
        child->parent = res;
        child->position = numKeys;
        res->getChildren()[numKeys] = child;

        // done
        return res;
    }
};  // namespace souffle

// Instantiation of static member search.
template <typename Key, typename Comparator, typename Allocator, unsigned blockSize, typename SearchStrategy,
        bool isSet, typename WeakComparator, typename Updater>
const SearchStrategy btree_delete<Key, Comparator, Allocator, blockSize, SearchStrategy, isSet,
        WeakComparator, Updater>::search;

}  // end namespace detail

/**
 * A b-tree based set implementation.
 *
 * @tparam Key             .. the element type to be stored in this set
 * @tparam Comparator     .. a class defining an order on the stored elements
 * @tparam Allocator     .. utilized for allocating memory for required nodes
 * @tparam blockSize    .. determines the number of bytes/block utilized by leaf nodes
 * @tparam SearchStrategy .. enables switching between linear, binary or any other search strategy
 */
template <typename Key, typename Comparator = detail::comparator<Key>,
        typename Allocator = std::allocator<Key>,  // is ignored so far
        unsigned blockSize = 256,
        typename SearchStrategy = typename souffle::detail::default_strategy<Key>::type,
        typename WeakComparator = Comparator, typename Updater = souffle::detail::updater<Key>>
class btree_delete_set : public souffle::detail::btree_delete<Key, Comparator, Allocator, blockSize,
                                 SearchStrategy, true, WeakComparator, Updater> {
    using super = souffle::detail::btree_delete<Key, Comparator, Allocator, blockSize, SearchStrategy, true,
            WeakComparator, Updater>;

    friend class souffle::detail::btree_delete<Key, Comparator, Allocator, blockSize, SearchStrategy, true,
            WeakComparator, Updater>;

public:
    /**
     * A default constructor creating an empty set.
     */
    btree_delete_set(
            const Comparator& comp = Comparator(), const WeakComparator& weak_comp = WeakComparator())
            : super(comp, weak_comp) {}

    /**
     * A constructor creating a set based on the given range.
     */
    template <typename Iter>
    btree_delete_set(const Iter& a, const Iter& b) {
        this->insert(a, b);
    }

    // A copy constructor.
    btree_delete_set(const btree_delete_set& other) : super(other) {}

    // A move constructor.
    btree_delete_set(btree_delete_set&& other) : super(std::move(other)) {}

private:
    // A constructor required by the bulk-load facility.
    template <typename s, typename n, typename l>
    btree_delete_set(s size, n* root, l* leftmost) : super(size, root, leftmost) {}

public:
    // Support for the assignment operator.
    btree_delete_set& operator=(const btree_delete_set& other) {
        super::operator=(other);
        return *this;
    }

    // Support for the bulk-load operator.
    template <typename Iter>
    static btree_delete_set load(const Iter& a, const Iter& b) {
        return super::template load<btree_delete_set>(a, b);
    }
};

/**
 * A b-tree based multi-set implementation.
 *
 * @tparam Key             .. the element type to be stored in this set
 * @tparam Comparator     .. a class defining an order on the stored elements
 * @tparam Allocator     .. utilized for allocating memory for required nodes
 * @tparam blockSize    .. determines the number of bytes/block utilized by leaf nodes
 * @tparam SearchStrategy .. enables switching between linear, binary or any other search strategy
 */
template <typename Key, typename Comparator = detail::comparator<Key>,
        typename Allocator = std::allocator<Key>,  // is ignored so far
        unsigned blockSize = 256,
        typename SearchStrategy = typename souffle::detail::default_strategy<Key>::type,
        typename WeakComparator = Comparator, typename Updater = souffle::detail::updater<Key>>
class btree_delete_multiset : public souffle::detail::btree_delete<Key, Comparator, Allocator, blockSize,
                                      SearchStrategy, false, WeakComparator, Updater> {
    using super = souffle::detail::btree_delete<Key, Comparator, Allocator, blockSize, SearchStrategy, false,
            WeakComparator, Updater>;

    friend class souffle::detail::btree_delete<Key, Comparator, Allocator, blockSize, SearchStrategy, false,
            WeakComparator, Updater>;

public:
    /**
     * A default constructor creating an empty set.
     */
    btree_delete_multiset(
            const Comparator& comp = Comparator(), const WeakComparator& weak_comp = WeakComparator())
            : super(comp, weak_comp) {}

    /**
     * A constructor creating a set based on the given range.
     */
    template <typename Iter>
    btree_delete_multiset(const Iter& a, const Iter& b) {
        this->insert(a, b);
    }

    // A copy constructor.
    btree_delete_multiset(const btree_delete_multiset& other) : super(other) {}

    // A move constructor.
    btree_delete_multiset(btree_delete_multiset&& other) : super(std::move(other)) {}

private:
    // A constructor required by the bulk-load facility.
    template <typename s, typename n, typename l>
    btree_delete_multiset(s size, n* root, l* leftmost) : super(size, root, leftmost) {}

public:
    // Support for the assignment operator.
    btree_delete_multiset& operator=(const btree_delete_multiset& other) {
        super::operator=(other);
        return *this;
    }

    // Support for the bulk-load operator.
    template <typename Iter>
    static btree_delete_multiset load(const Iter& a, const Iter& b) {
        return super::template load<btree_delete_multiset>(a, b);
    }
};

}  // end of namespace souffle
