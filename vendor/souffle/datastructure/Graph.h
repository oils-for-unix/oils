/*
 * Souffle - A Datalog Compiler
 * Copyright (c) 2013, 2015, Oracle and/or its affiliates. All rights reserved
 * Licensed under the Universal Permissive License v 1.0 as shown at:
 * - https://opensource.org/licenses/UPL
 * - <souffle root>/licenses/SOUFFLE-UPL.txt
 */

/************************************************************************
 *
 * @file Graph.h
 *
 * A basic digraph with edge labels.
 *
 ***********************************************************************/

#pragma once

#include "souffle/utility/ContainerUtil.h"
#include "souffle/utility/Types.h"
#include <deque>
#include <functional>
#include <map>
#include <ostream>
#include <set>
#include <vector>
#ifndef NDEBUG
#include <algorithm>
#endif

namespace souffle {

namespace detail {

struct GraphUnitEdgeSet {};

}  // namespace detail

/**
 * A simple graph structure for graph-based operations.
 */
template <typename Vertex, typename EdgeLabel = Unit, typename CompareVertex = std::less<Vertex>,
        typename CompareLabel = std::less<EdgeLabel>, bool UnitEdgeLabels = std::is_same_v<Unit, EdgeLabel>>
class GraphLabeled {
    // HACK: helper to avoid pulling in `Util.h` for `souffle::contains`
    template <typename C, typename E = typename C::element_type>
    static bool containsValue(const C& xs, const E& x) {
        return xs.find(x) != xs.end();
    }

public:
    using self_t = GraphLabeled<Vertex, EdgeLabel, CompareVertex, CompareLabel>;
    using VertexSet = std::set<Vertex, CompareVertex>;
    using EdgeLabelSet = std::set<EdgeLabel, CompareLabel>;
    enum class Visit { pre, post };

    /**
     * Adds a new edge from the given vertex to the target vertex.
     */
    template <typename = std::enable_if_t<UnitEdgeLabels>>
    bool insert(const Vertex& from, const Vertex& to) {
        return insert(from, to, EdgeLabelSet{});
    }

    bool insert(const Vertex& from, const Vertex& to, EdgeLabel label) {
        return insert(from, to, EdgeLabelSet{std::move(label)});
    }

    bool insert(const Vertex& from, const Vertex& to, EdgeLabelSet labels) {
        insert(from);
        insert(to);
        bool inserted = _successors[from].insert(to).second;
        _predecessors[to].insert(from);
        if constexpr (!UnitEdgeLabels) {
            auto& labels_store = _labels[{from, to}];  // force creation of entry
            if (labels_store.empty() && !labels.empty()) {
                labels_store = std::move(labels);
                inserted = true;
            } else {
                for (auto&& l : labels)
                    inserted |= labels_store.insert(l).second;
            }
        }
        return inserted;
    }

    /**
     * Adds a vertex.
     */
    bool insert(const Vertex& vertex) {
        return _vertices.insert(vertex).second;
    }

    bool insert(const self_t& g) {
        bool changed = false;
        auto combineSet = [&](auto& dst, auto&& src) {
            for (auto&& x : src)
                changed |= dst.insert(x).second;
        };
        auto combineMap = [&](auto& dst, auto&& src) {
            for (auto&& [v, xs] : src) {
                auto [it, added] = dst.insert({v, {}});
                changed |= added;
                combineSet(it->second, xs);
            }
        };

        combineSet(_vertices, g._vertices);
        combineMap(_successors, g._successors);
        combineMap(_predecessors, g._predecessors);
        if constexpr (!UnitEdgeLabels) {
            combineMap(_labels, g._labels);
        }

        return changed;
    }

    bool remove(const Vertex& vertex) {
        if (_vertices.erase(vertex) == 0) return false;

        if constexpr (!UnitEdgeLabels) {
            for (auto&& m : successors(vertex))
                _labels.erase({vertex, m});
        }

        _successors.erase(vertex);
        _predecessors.erase(vertex);
        return true;
    }

    size_t remove(const Vertex& src, const Vertex& dst) {
        auto it = _successors.find(src);
        if (it == _successors.end()) return 0;
        if (it->second.erase(dst) == 0) return 0;

        if (it->second.empty()) _successors.erase(it);
        removeExistingAdjEdge(_predecessors, dst, src);

        if constexpr (UnitEdgeLabels) {
            return 1;
        } else {
            auto it = _labels.find({src, dst});
            assert(it != _labels.end());
            assert(!it->second.empty());
            auto n = it->second.size();
            _labels.erase(it);
            return n;
        }
    }

    bool remove(const Vertex& src, const Vertex& dst, const EdgeLabel& label) {
        if constexpr (UnitEdgeLabels) {
            return 0 < remove(src, dst);
        } else {
            auto it = _labels.find({src, dst});
            if (it == _labels.end()) return false;
            if (it->second.erase(label) == 0) return false;

            // all edges erased -> remove from succ/pred
            if (it->second.empty()) {
                _labels.erase(it);
                removeExistingAdjEdge(_predecessors, dst, src);
                removeExistingAdjEdge(_successors, src, dst);
            }

            return true;
        }
    }

    size_t removeEdgesPred(const Vertex& node) {
        return removeEdgesIncidentTo(_predecessors, _successors, node,
                [](auto node, auto adj) { return std::make_pair(adj, node); });
    }

    size_t removeEdgesSucc(const Vertex& node) {
        return removeEdgesIncidentTo(_successors, _predecessors, node,
                [](auto node, auto adj) { return std::make_pair(node, adj); });
    }

    /** Obtains a reference to the set of all vertices */
    const VertexSet& vertices() const {
        return _vertices;
    }

    // set of vertices which appear as the source of an edge
    // i.e. { a | (a, b) \in E }
    VertexSet edgeSources() const {
        return keysOfAdjacency(_successors);
    }

    // set of vertices which appear as the target of an edge
    // i.e. { b | (a, b) \in E }
    VertexSet edgeTargets() const {
        return keysOfAdjacency(_predecessors);
    }

    /** Returns the set of vertices the given vertex has edges to */
    const VertexSet& successors(const Vertex& from) const {
        auto it = _successors.find(from);
        return it == _successors.end() ? null : it->second;
    }

    /** Returns the set of vertices the given vertex has edges from */
    const VertexSet& predecessors(const Vertex& to) const {
        auto it = _predecessors.find(to);
        return it == _predecessors.end() ? null : it->second;
    }

    /** Obtains the union of sources and nodes transitively reachable via the sources' successors */
    template <typename C>
    VertexSet reachableFromSucc(C&& sources) const {
        return reachableFrom(std::forward<C>(sources), std::mem_fn(&GraphLabeled::successors));
    }

    /** Obtains the union of sources and nodes transitively reachable via the sources' predecessors */
    template <typename C>
    VertexSet reachableFromPred(C&& sources) const {
        return reachableFrom(std::forward<C>(sources), std::mem_fn(&GraphLabeled::predecessors));
    }

    VertexSet reachableFromSucc(Vertex src) const {
        return reachableFromSucc(VertexSet{std::move(src)});
    }

    VertexSet reachableFromPred(Vertex src) const {
        return reachableFromPred(VertexSet{std::move(src)});
    }

    template <typename Edges>
    VertexSet reachableFrom(Vertex src, Edges&& edges) const {
        return reachableFrom(VertexSet{std::move(src)}, std::forward<Edges>(edges));
    }

    template <typename Edges>
    VertexSet reachableFrom(VertexSet&& sources, Edges&& edges) const {
        std::vector<Vertex> pending{sources.begin(), sources.end()};
        return reachableFrom(std::move(sources), std::move(pending), std::forward<Edges>(edges));
    }

    template <typename C, typename Edges>
    VertexSet reachableFrom(C&& srcs, Edges&& edges) const {
        // nitpick: build `pending` from `srcs` to preserve whatever iteration order is imposed by `srcs`
        std::vector<Vertex> pending{srcs.begin(), srcs.end()};
        return reachableFrom({srcs.begin(), srcs.end()}, std::move(pending), std::forward<Edges>(edges));
    }

    const EdgeLabelSet& labels(const Vertex& from, const Vertex& to) const {
        if constexpr (UnitEdgeLabels) {
            if (contains(from, to)) return _labels.unit;
        } else {
            auto it = _labels.find({from, to});
            if (it != _labels.end()) return it->second;
        }

        return nullLabel;
    }

    /** Determines whether the given vertex is present */
    bool contains(const Vertex& vertex) const {
        return _vertices.find(vertex) != _vertices.end();
    }

    /** Determines whether the given edge is present */
    bool contains(const Vertex& from, const Vertex& to) const {
        auto pos = _successors.find(from);
        if (pos == _successors.end()) {
            return false;
        }
        auto p2 = pos->second.find(to);
        return p2 != pos->second.end();
    }

    bool contains(const Vertex& from, const Vertex& to, const EdgeLabel& label) const {
        if constexpr (UnitEdgeLabels) {
            return contains(from, to);
        } else {
            auto it = _labels.find({from, to});
            return it != _labels.end() && containsValue(it->second, label);
        }
    }

    /** Determines whether there is a directed path between the two vertices */
    bool reaches(const Vertex& from, const Vertex& to) const {
        // quick check
        if (!contains(from) || !contains(to)) {
            return false;
        }

        // conduct a depth-first search starting at from
        bool found = false;
        bool first = true;
        visit(from, [&](const Vertex& cur) {
            found = !first && (found || cur == to);
            first = false;
        });
        return found;
    }

    /** Obtains the set of all vertices in the same clique than the given vertex */
    VertexSet clique(const Vertex& vertex) const {
        VertexSet res;
        res.insert(vertex);
        for (const auto& cur : vertices()) {
            if (reaches(vertex, cur) && reaches(cur, vertex)) {
                res.insert(cur);
            }
        }
        return res;
    }

    template <typename C>
    self_t induced(const C& nodes) const {
        VertexSet xs;
        for (auto&& n : nodes)
            if (containsValue(_vertices, n)) xs.insert(n);

        return inducedImpl(std::move(xs));
    }

    self_t inducedReachableDijkstra(const Vertex& source, const std::set<Vertex>& sinks) const {
        // `sink_depths` seperate from `depths` to handle case where `source \in sinks`,
        // otherwise we'd see a sink as having depth 0 on the backwards pass.
        std::map<Vertex, size_t, CompareVertex> sink_depths;
        std::map<Vertex, size_t, CompareVertex> depths;
        std::deque<Vertex> pending;

        auto update = [&](const Vertex& x, size_t depth) {
            auto it = depths.find(x);
            if (it != depths.end() && it->second <= depth) return false;

            depths[x] = depth;
            pending.push_back(x);
            return true;
        };

        update(source, 0);

        while (!pending.empty() && sink_depths.size() < sinks.size()) {
            auto x = pending.front();
            pending.pop_front();

            auto depth = depths.at(x);
            for (auto&& succ : successors(x)) {
                if (souffle::contains(sinks, succ)) {
                    sink_depths.insert({succ, depth + 1});
                    // Keep walking.
                    // 1) The shortest path 'tween a src-sink pair could pass through a different sink.
                    // 2) We want all shortest paths, not just one shortest path.
                    // e.g. ```
                    //      a --> b --> d -> e
                    //        \-> c -/
                    //      ```
                    //      Source  : `a`
                    //      Sinks   : `{d, e}`
                }

                update(succ, depth + 1);
            }
        }

        self_t induced;
        std::vector<std::pair<Vertex, size_t>> rev_pending(sink_depths.begin(), sink_depths.end());
        while (!rev_pending.empty()) {
            auto [x, depth] = rev_pending.back();
            rev_pending.pop_back();
            assert(1 <= depth && "rev-walk should terminate at source");

            for (auto&& pred : predecessors(x)) {
                auto it = depths.find(pred);
                if (it == depths.end() || depth <= it->second) continue;  // edge not in shortest-paths
                assert(it->second == depth - 1 && "shorter path found on reverse walk?");
                assert(((1 == depth) == (pred == source)) && "depth-1 vertices should only link to `source`");

                // 1) not already in `rev_pending` (implied by `x \in induced`)
                // 2) not the source
                if (!induced.contains(pred) && 1 < depth) {
                    rev_pending.push_back({pred, depth - 1});
                }

                induced.insert(pred, x, labels(pred, x));
            }
        }

        return induced;
    }

    /** A generic utility for depth-first pre-order visits */
    template <typename Lambda>
    void visit(const Vertex& vertex, const Lambda& lambda) const {
        visitDepthFirst(vertex, [&](Visit e, auto&& v) {
            if (e == Visit::pre) lambda(v);
        });
    }

    /** A generic utility for depth-first visits */
    template <typename Lambda>
    void visitDepthFirst(const Vertex& vertex, const Lambda& lambda) const {
        VertexSet visited;
        visitDepthFirst(vertex, lambda, std::mem_fn(&GraphLabeled::successors), visited);
    }

    // if there are multiple sources then pretend there is a pseudo-source node with edge to each
    template <typename Lambda>
    void visitDepthFirstSources(const Lambda& lambda) const {
        // pseudo node can be impl by iterating over each source w/ a shared `visited`
        VertexSet visited;
        for (auto&& v : vertices())
            if (predecessors(v).empty()) {
                visitDepthFirst(v, lambda, std::mem_fn(&GraphLabeled::successors), visited);
            }
    }

    /** Enables graphs to be printed (e.g. for debugging) */
    void print(std::ostream& os) const {
        bool first = true;
        os << "{";
        for (auto&& curr : vertices()) {
            auto&& succs = successors(curr);
            for (auto&& succ : succs) {
                if (!first) os << "\n,";
                first = false;

                os << curr << "->" << succ;
                if constexpr (!UnitEdgeLabels) {
                    os << " [" << join(labels(curr, succ)) << "]";
                }
            }

            // handle case where node is disconnected
            if (succs.empty() && predecessors(curr).empty()) {
                if (!first) os << "\n,";
                first = false;
                os << curr;
            }
        }
        os << "}";
    }

    friend std::ostream& operator<<(std::ostream& out, const self_t& g) {
        g.print(out);
        return out;
    }

    void DBG_sanCheck() const {
#ifndef NDEBUG
        auto checkPeer = [&](auto&& src, auto&& peer) {
            for (auto&& [n, ms] : src) {
                assert(!ms.empty() && "shouldn't store empty sets");
                assert(containsValue(_vertices, n));
                for (auto&& m : ms) {
                    assert(containsValue(_vertices, m));
                    assert(containsValue(peer, m));
                    assert(containsValue(peer.at(m), n));
                }
            }
        };

        checkPeer(_successors, _predecessors);
        checkPeer(_predecessors, _successors);

        if constexpr (!UnitEdgeLabels) {
            for (auto&& [kv, labels] : _labels) {
                auto&& [n, m] = kv;
                assert(!labels.empty() && "shouldn't store an empty label set");
                assert(containsValue(_successors.at(n), m));
            }
        }
#endif
    }

private:
    using Vertex2Peer = std::map<Vertex, VertexSet, CompareVertex>;
    using EdgeVerts = std::pair<Vertex, Vertex>;
    using Edge2Labels =
            std::conditional_t<UnitEdgeLabels, detail::GraphUnitEdgeSet, std::map<EdgeVerts, EdgeLabelSet>>;

    // not a very efficient but simple graph representation
    VertexSet null;             // the empty set
    EdgeLabelSet nullLabel;     // the empty set
    VertexSet _vertices;        // all the vertices in the graph
    Vertex2Peer _successors;    // all edges forward directed
    Vertex2Peer _predecessors;  // all edges backward
    Edge2Labels _labels;

    /** The internal implementation of depth-first visits */
    template <typename Fn, typename Edges>
    void visitDepthFirst(const Vertex& v, const Fn& lambda, const Edges& edges, VertexSet& visited) const {
        lambda(Visit::pre, v);

        for (auto&& next : edges(*this, v))
            if (visited.insert(next).second) {
                visitDepthFirst(next, lambda, edges, visited);
            }

        lambda(Visit::post, v);
    }

    template <typename Edges>
    VertexSet reachableFrom(VertexSet visited, std::vector<Vertex> pending, Edges&& edges) const {
        assert(visited.size() == pending.size());
        assert(all_of(pending, [&](auto&& x) { return souffle::contains(visited, x); }));

        while (!pending.empty()) {
            auto curr = pending.back();
            pending.pop_back();
            for (auto&& next : edges(*this, curr))
                if (visited.insert(next).second) {
                    pending.push_back(next);
                }
        }

        return visited;
    }

    template <typename EdgePair>
    size_t removeEdgesIncidentTo(Vertex2Peer& fwd, Vertex2Peer& rev, const Vertex& node, EdgePair&& edge) {
        auto it = fwd.find(node);
        if (it == fwd.end()) return 0;

        size_t n_edges = 0;
        if constexpr (UnitEdgeLabels) {
            n_edges = it->second.size();
        }

        for (auto&& adj : it->second) {
            removeExistingAdjEdge(rev, adj, node);

            if constexpr (!UnitEdgeLabels) {
                auto it_label = _labels.find(edge(node, adj));
                n_edges += it_label->second.size();
                _labels.erase(it_label);
            }
        }

        fwd.erase(it);
        return n_edges;
    }

    self_t inducedImpl(VertexSet nodes) const {
        DBG_sanCheck();
        assert(std::includes(_vertices.begin(), _vertices.end(), nodes.begin(), nodes.end()) &&
                "`nodes` must be a subset of `_vertices`");

        self_t induced;
        induced._vertices = std::move(nodes);

        for (auto&& n : induced._vertices) {
            auto addEdges = [&](auto&& dst_map, auto&& src) {
                if (src.empty()) return;

                auto&& [it, _] = dst_map.insert({n, {}});
                auto& dst = it->second;
                bool added_anything = false;
                for (auto&& m : src)
                    if (containsValue(induced._vertices, m)) {
                        added_anything = true;
                        dst.insert(m);
                    }

                if (!added_anything) dst_map.erase(it);
            };

            addEdges(induced._successors, successors(n));
            addEdges(induced._predecessors, predecessors(n));

            if constexpr (!UnitEdgeLabels) {
                for (auto&& m : induced.successors(n))
                    induced._labels[{n, m}] = labels(n, m);
            }
        }

        induced.DBG_sanCheck();
        return induced;
    }

    static void removeExistingAdjEdge(Vertex2Peer& adj, const Vertex& a, const Vertex& b) {
        auto it = adj.find(a);
        assert(it != adj.end());
        [[maybe_unused]] auto n = it->second.erase(b);
        assert(n == 1);
        if (it->second.empty()) adj.erase(it);
    }

    static VertexSet keysOfAdjacency(const Vertex2Peer& adj) {
        VertexSet xs;
        for (auto&& [k, _] : adj)
            xs.insert(k);
        return xs;
    }
};

template <typename Vertex, typename Compare = std::less<Vertex>>
using Graph = GraphLabeled<Vertex, Unit, Compare>;

}  // end of namespace souffle
