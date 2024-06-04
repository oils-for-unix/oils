/*
 * Souffle - A Datalog Compiler
 * Copyright (c) 2022, The Souffle Developers. All rights reserved
 * Licensed under the Universal Permissive License v 1.0 as shown at:
 * - https://opensource.org/licenses/UPL
 * - <souffle root>/licenses/SOUFFLE-UPL.txt
 */

/**
 * @file RecordTableImpl.h
 *
 * RecordTable definition
 */

#pragma once

#include "souffle/RamTypes.h"
#include "souffle/RecordTable.h"
#include "souffle/datastructure/ConcurrentFlyweight.h"
#include "souffle/utility/span.h"

#include <cassert>
#include <cstddef>
#include <limits>
#include <memory>
#include <utility>
#include <vector>

namespace souffle {

namespace details {

// Helper to unroll for loop
template <auto Start, auto End, auto Inc, class F>
constexpr void constexpr_for(F&& f) {
    if constexpr (Start < End) {
        f(std::integral_constant<decltype(Start), Start>());
        constexpr_for<Start + Inc, End, Inc>(f);
    }
}

/// @brief The data-type of RamDomain records of any size.
using GenericRecord = std::vector<RamDomain>;

/// @brief The data-type of RamDomain records of specialized size.
template <std::size_t Arity>
using SpecializedRecord = std::array<RamDomain, Arity>;

/// @brief A view in a sequence of RamDomain value.
// TODO: use a `span`.
struct GenericRecordView {
    explicit GenericRecordView(const RamDomain* Data, const std::size_t Arity) : Data(Data), Arity(Arity) {}
    GenericRecordView(const GenericRecordView& Other) : Data(Other.Data), Arity(Other.Arity) {}
    GenericRecordView(GenericRecordView&& Other) : Data(Other.Data), Arity(Other.Arity) {}

    const RamDomain* const Data;
    const std::size_t Arity;

    const RamDomain* data() const {
        return Data;
    }

    const RamDomain& operator[](int I) const {
        assert(I >= 0 && static_cast<std::size_t>(I) < Arity);
        return Data[I];
    }
};

template <std::size_t Arity>
struct SpecializedRecordView {
    explicit SpecializedRecordView(const RamDomain* Data) : Data(Data) {}
    SpecializedRecordView(const SpecializedRecordView& Other) : Data(Other.Data) {}
    SpecializedRecordView(SpecializedRecordView&& Other) : Data(Other.Data) {}

    const RamDomain* const Data;

    const RamDomain* data() const {
        return Data;
    }

    const RamDomain& operator[](int I) const {
        assert(I >= 0 && static_cast<std::size_t>(I) < Arity);
        return Data[I];
    }
};

/// @brief Hash function object for a RamDomain record.
struct GenericRecordHash {
    explicit GenericRecordHash(const std::size_t Arity) : Arity(Arity) {}
    GenericRecordHash(const GenericRecordHash& Other) : Arity(Other.Arity) {}
    GenericRecordHash(GenericRecordHash&& Other) : Arity(Other.Arity) {}

    const std::size_t Arity;
    std::hash<RamDomain> domainHash;

    template <typename T>
    std::size_t operator()(const T& Record) const {
        std::size_t Seed = 0;
        for (std::size_t I = 0; I < Arity; ++I) {
            Seed ^= domainHash(Record[(int)I]) + 0x9e3779b9U + (Seed << 6U) + (Seed >> 2U);
        }
        return Seed;
    }
};

template <std::size_t Arity>
struct SpecializedRecordHash {
    explicit SpecializedRecordHash() {}
    SpecializedRecordHash(const SpecializedRecordHash& Other) : DomainHash(Other.DomainHash) {}
    SpecializedRecordHash(SpecializedRecordHash&& Other) : DomainHash(Other.DomainHash) {}

    std::hash<RamDomain> DomainHash;

    template <typename T>
    std::size_t operator()(const T& Record) const {
        std::size_t Seed = 0;
        constexpr_for<0, Arity, 1>([&](auto I) {
            Seed ^= DomainHash(Record[(int)I]) + 0x9e3779b9U + (Seed << 6U) + (Seed >> 2U);
        });
        return Seed;
    }
};

template <>
struct SpecializedRecordHash<0> {
    explicit SpecializedRecordHash() {}
    SpecializedRecordHash(const SpecializedRecordHash&) {}
    SpecializedRecordHash(SpecializedRecordHash&&) {}

    template <typename T>
    std::size_t operator()(const T&) const {
        return 0;
    }
};

/// @brief Equality function object for RamDomain records.
struct GenericRecordEqual {
    explicit GenericRecordEqual(const std::size_t Arity) : Arity(Arity) {}
    GenericRecordEqual(const GenericRecordEqual& Other) : Arity(Other.Arity) {}
    GenericRecordEqual(GenericRecordEqual&& Other) : Arity(Other.Arity) {}

    const std::size_t Arity;

    template <typename T, typename U>
    bool operator()(const T& A, const U& B) const {
        return (std::memcmp(A.data(), B.data(), Arity * sizeof(RamDomain)) == 0);
    }
};

template <std::size_t Arity>
struct SpecializedRecordEqual {
    explicit SpecializedRecordEqual() {}
    SpecializedRecordEqual(const SpecializedRecordEqual&) {}
    SpecializedRecordEqual(SpecializedRecordEqual&&) {}

    template <typename T, typename U>
    bool operator()(const T& A, const U& B) const {
        constexpr std::size_t Len = Arity * sizeof(RamDomain);
        return (std::memcmp(A.data(), B.data(), Len) == 0);
    }
};

template <>
struct SpecializedRecordEqual<0> {
    explicit SpecializedRecordEqual() {}
    SpecializedRecordEqual(const SpecializedRecordEqual&) {}
    SpecializedRecordEqual(SpecializedRecordEqual&&) {}

    template <typename T, typename U>
    bool operator()(const T&, const U&) const {
        return true;
    }
};

/// @brief Less function object for RamDomain records.
struct GenericRecordLess {
    explicit GenericRecordLess(const std::size_t Arity) : Arity(Arity) {}
    GenericRecordLess(const GenericRecordLess& Other) : Arity(Other.Arity) {}
    GenericRecordLess(GenericRecordLess&& Other) : Arity(Other.Arity) {}

    const std::size_t Arity;

    template <typename T, typename U>
    bool operator()(const T& A, const U& B) const {
        return (std::memcmp(A.data(), B.data(), Arity * sizeof(RamDomain)) < 0);
    }
};

template <std::size_t Arity>
struct SpecializedRecordLess {
    explicit SpecializedRecordLess() {}
    SpecializedRecordLess(const SpecializedRecordLess&) {}
    SpecializedRecordLess(SpecializedRecordLess&&) {}

    template <typename T, typename U>
    bool operator()(const T& A, const U& B) const {
        constexpr std::size_t Len = Arity * sizeof(RamDomain);
        return (std::memcmp(A.data(), B.data(), Len) < 0);
    }
};

template <>
struct SpecializedRecordLess<0> {
    explicit SpecializedRecordLess() {}
    SpecializedRecordLess(const SpecializedRecordLess&) {}
    SpecializedRecordLess(SpecializedRecordLess&&) {}

    template <typename T, typename U>
    bool operator()(const T&, const U&) const {
        return false;
    }
};

/// @brief Compare function object for RamDomain records.
struct GenericRecordCmp {
    explicit GenericRecordCmp(const std::size_t Arity) : Arity(Arity) {}
    GenericRecordCmp(const GenericRecordCmp& Other) : Arity(Other.Arity) {}
    GenericRecordCmp(GenericRecordCmp&& Other) : Arity(Other.Arity) {}

    const std::size_t Arity;

    template <typename T, typename U>
    int operator()(const T& A, const U& B) const {
        return std::memcmp(A.data(), B.data(), Arity * sizeof(RamDomain));
    }
};

template <std::size_t Arity>
struct SpecializedRecordCmp {
    explicit SpecializedRecordCmp() {}
    SpecializedRecordCmp(const SpecializedRecordCmp&) {}
    SpecializedRecordCmp(SpecializedRecordCmp&&) {}

    template <typename T, typename U>
    bool operator()(const T& A, const U& B) const {
        constexpr std::size_t Len = Arity * sizeof(RamDomain);
        return std::memcmp(A.data(), B.data(), Len);
    }
};

template <>
struct SpecializedRecordCmp<0> {
    explicit SpecializedRecordCmp() {}
    SpecializedRecordCmp(const SpecializedRecordCmp&) {}
    SpecializedRecordCmp(SpecializedRecordCmp&&) {}

    template <typename T, typename U>
    bool operator()(const T&, const U&) const {
        return 0;
    }
};

/// @brief Factory of RamDomain record.
struct GenericRecordFactory {
    using value_type = GenericRecord;
    using pointer = GenericRecord*;
    using reference = GenericRecord&;

    explicit GenericRecordFactory(const std::size_t Arity) : Arity(Arity) {}
    GenericRecordFactory(const GenericRecordFactory& Other) : Arity(Other.Arity) {}
    GenericRecordFactory(GenericRecordFactory&& Other) : Arity(Other.Arity) {}

    const std::size_t Arity;

    reference replace(reference Place, const std::vector<RamDomain>& V) {
        assert(V.size() == Arity);
        Place = V;
        return Place;
    }

    reference replace(reference Place, const GenericRecordView& V) {
        Place.clear();
        Place.insert(Place.begin(), V.data(), V.data() + Arity);
        return Place;
    }

    reference replace(reference Place, const RamDomain* V) {
        Place.clear();
        Place.insert(Place.begin(), V, V + Arity);
        return Place;
    }
};

template <std::size_t Arity>
struct SpecializedRecordFactory {
    using value_type = SpecializedRecord<Arity>;
    using pointer = SpecializedRecord<Arity>*;
    using reference = SpecializedRecord<Arity>&;

    explicit SpecializedRecordFactory() {}
    SpecializedRecordFactory(const SpecializedRecordFactory&) {}
    SpecializedRecordFactory(SpecializedRecordFactory&&) {}

    reference replace(reference Place, const SpecializedRecord<Arity>& V) {
        assert(V.size() == Arity);
        Place = V;
        return Place;
    }

    reference replace(reference Place, const SpecializedRecordView<Arity>& V) {
        constexpr std::size_t Len = Arity * sizeof(RamDomain);
        std::memcpy(Place.data(), V.data(), Len);
        return Place;
    }

    reference replace(reference Place, const RamDomain* V) {
        constexpr std::size_t Len = Arity * sizeof(RamDomain);
        std::memcpy(Place.data(), V, Len);
        return Place;
    }
};

template <>
struct SpecializedRecordFactory<0> {
    using value_type = SpecializedRecord<0>;
    using pointer = SpecializedRecord<0>*;
    using reference = SpecializedRecord<0>&;

    explicit SpecializedRecordFactory() {}
    SpecializedRecordFactory(const SpecializedRecordFactory&) {}
    SpecializedRecordFactory(SpecializedRecordFactory&&) {}

    reference replace(reference Place, const SpecializedRecord<0>&) {
        return Place;
    }

    reference replace(reference Place, const SpecializedRecordView<0>&) {
        return Place;
    }

    reference replace(reference Place, const RamDomain*) {
        return Place;
    }
};

}  // namespace details

/** @brief Interface of bidirectional mappping between records and record references. */
class RecordMap {
public:
    virtual ~RecordMap() {}
    virtual void setNumLanes(const std::size_t NumLanes) = 0;
    virtual RamDomain pack(const std::vector<RamDomain>& Vector) = 0;
    virtual RamDomain pack(const RamDomain* Tuple) = 0;
    virtual RamDomain pack(const std::initializer_list<RamDomain>& List) = 0;
    virtual const RamDomain* unpack(RamDomain index) const = 0;
};

/** @brief Bidirectional mappping between records and record references, for any record arity. */
class GenericRecordMap : public RecordMap,
                         protected FlyweightImpl<details::GenericRecord, details::GenericRecordHash,
                                 details::GenericRecordEqual, details::GenericRecordFactory> {
    using Base = FlyweightImpl<details::GenericRecord, details::GenericRecordHash,
            details::GenericRecordEqual, details::GenericRecordFactory>;

    const std::size_t Arity;

public:
    explicit GenericRecordMap(const std::size_t lane_count, const std::size_t arity)
            : Base(lane_count, 8, true, details::GenericRecordHash(arity), details::GenericRecordEqual(arity),
                      details::GenericRecordFactory(arity)),
              Arity(arity) {}

    virtual ~GenericRecordMap() {}

    void setNumLanes(const std::size_t NumLanes) override {
        Base::setNumLanes(NumLanes);
    }

    /** @brief converts record to a record reference */
    RamDomain pack(const std::vector<RamDomain>& Vector) override {
        return findOrInsert(Vector).first;
    };

    /** @brief converts record to a record reference */
    RamDomain pack(const RamDomain* Tuple) override {
        details::GenericRecordView View{Tuple, Arity};
        return findOrInsert(View).first;
    }

    /** @brief converts record to a record reference */
    RamDomain pack(const std::initializer_list<RamDomain>& List) override {
        details::GenericRecordView View{std::data(List), Arity};
        return findOrInsert(View).first;
    }

    /** @brief convert record reference to a record pointer */
    const RamDomain* unpack(RamDomain Index) const override {
        return fetch(Index).data();
    }
};

/** @brief Bidirectional mappping between records and record references, specialized for a record arity. */
template <std::size_t Arity>
class SpecializedRecordMap
        : public RecordMap,
          protected FlyweightImpl<details::SpecializedRecord<Arity>, details::SpecializedRecordHash<Arity>,
                  details::SpecializedRecordEqual<Arity>, details::SpecializedRecordFactory<Arity>> {
    using Record = details::SpecializedRecord<Arity>;
    using RecordView = details::SpecializedRecordView<Arity>;
    using RecordHash = details::SpecializedRecordHash<Arity>;
    using RecordEqual = details::SpecializedRecordEqual<Arity>;
    using RecordFactory = details::SpecializedRecordFactory<Arity>;
    using Base = FlyweightImpl<Record, RecordHash, RecordEqual, RecordFactory>;

public:
    SpecializedRecordMap(const std::size_t LaneCount)
            : Base(LaneCount, 8, true, RecordHash(), RecordEqual(), RecordFactory()) {}

    virtual ~SpecializedRecordMap() {}

    void setNumLanes(const std::size_t NumLanes) override {
        Base::setNumLanes(NumLanes);
    }

    /** @brief converts record to a record reference */
    RamDomain pack(const std::vector<RamDomain>& Vector) override {
        assert(Vector.size() == Arity);
        RecordView View{Vector.data()};
        return Base::findOrInsert(View).first;
    };

    /** @brief converts record to a record reference */
    RamDomain pack(const RamDomain* Tuple) override {
        RecordView View{Tuple};
        return Base::findOrInsert(View).first;
    }

    /** @brief converts record to a record reference */
    RamDomain pack(const std::initializer_list<RamDomain>& List) override {
        assert(List.size() == Arity);
        RecordView View{std::data(List)};
        return Base::findOrInsert(View).first;
    }

    /** @brief convert record reference to a record pointer */
    const RamDomain* unpack(RamDomain Index) const override {
        return Base::fetch(Index).data();
    }
};

/** Record map specialized for arity 0 */
template <>
class SpecializedRecordMap<0> : public RecordMap {
    // The empty record always at index 1
    // The index 0 of each map is reserved.
    static constexpr RamDomain EmptyRecordIndex = 1;

    // To comply with previous behavior, the empty record
    // has no data:
    const RamDomain* EmptyRecordData = nullptr;

public:
    SpecializedRecordMap(const std::size_t /* LaneCount */) {}

    virtual ~SpecializedRecordMap() {}

    void setNumLanes(const std::size_t) override {}

    /** @brief converts record to a record reference */
    RamDomain pack([[maybe_unused]] const std::vector<RamDomain>& Vector) override {
        assert(Vector.size() == 0);
        return EmptyRecordIndex;
    };

    /** @brief converts record to a record reference */
    RamDomain pack(const RamDomain*) override {
        return EmptyRecordIndex;
    }

    /** @brief converts record to a record reference */
    RamDomain pack([[maybe_unused]] const std::initializer_list<RamDomain>& List) override {
        assert(List.size() == 0);
        return EmptyRecordIndex;
    }

    /** @brief convert record reference to a record pointer */
    const RamDomain* unpack([[maybe_unused]] RamDomain Index) const override {
        assert(Index == EmptyRecordIndex);
        return EmptyRecordData;
    }
};

/** A concurrent Record Table with some specialized record maps. */
template <std::size_t... SpecializedArities>
class SpecializedRecordTable : public RecordTable {
private:
    // The current size of the Maps vector.
    std::size_t Size;

    // The record maps, indexed by arity.
    std::vector<RecordMap*> Maps;

    // The concurrency manager.
    mutable ConcurrentLanes Lanes;

    template <std::size_t Arity, std::size_t... Arities>
    void CreateSpecializedMaps() {
        if (Arity >= Size) {
            Size = Arity + 1;
            Maps.reserve(Size);
            Maps.resize(Size);
        }
        Maps[Arity] = new SpecializedRecordMap<Arity>(Lanes.lanes());
        if constexpr (sizeof...(Arities) > 0) {
            CreateSpecializedMaps<Arities...>();
        }
    }

public:
    /** @brief Construct a record table with the number of concurrent access lanes. */
    SpecializedRecordTable(const std::size_t LaneCount) : Size(0), Lanes(LaneCount) {
        CreateSpecializedMaps<SpecializedArities...>();
    }

    SpecializedRecordTable() : SpecializedRecordTable(1) {}

    virtual ~SpecializedRecordTable() {
        for (auto Map : Maps) {
            delete Map;
        }
    }

    /**
     * @brief set the number of concurrent access lanes.
     * Not thread-safe, use only when the datastructure is not being used.
     */
    virtual void setNumLanes(const std::size_t NumLanes) override {
        Lanes.setNumLanes(NumLanes);
        for (auto& Map : Maps) {
            if (Map) {
                Map->setNumLanes(NumLanes);
            }
        }
    }

    /** @brief convert tuple to record reference */
    virtual RamDomain pack(const RamDomain* Tuple, const std::size_t Arity) override {
        auto Guard = Lanes.guard();
        return lookupMap(Arity).pack(Tuple);
    }

    /** @brief convert tuple to record reference */
    virtual RamDomain pack(const std::initializer_list<RamDomain>& List) override {
        auto Guard = Lanes.guard();
        return lookupMap(List.size()).pack(std::data(List));
    }

    /** @brief convert record reference to a record */
    virtual const RamDomain* unpack(const RamDomain Ref, const std::size_t Arity) const override {
        auto Guard = Lanes.guard();
        return lookupMap(Arity).unpack(Ref);
    }

private:
    /** @brief lookup RecordMap for a given arity; the map for that arity must exist. */
    RecordMap& lookupMap(const std::size_t Arity) const {
        assert(Arity < Size && "Lookup for an arity while there is no record for that arity.");
        auto* Map = Maps[Arity];
        assert(Map != nullptr && "Lookup for an arity while there is no record for that arity.");
        return *Map;
    }

    /** @brief lookup RecordMap for a given arity; if it does not exist, create new RecordMap */
    RecordMap& lookupMap(const std::size_t Arity) {
        if (Arity < Size) {
            auto* Map = Maps[Arity];
            if (Map) {
                return *Map;
            }
        }

        createMap(Arity);
        return *Maps[Arity];
    }

    /** @brief create the RecordMap for the given arity. */
    void createMap(const std::size_t Arity) {
        Lanes.beforeLockAllBut();
        if (Arity < Size && Maps[Arity] != nullptr) {
            // Map of required arity has been created concurrently
            Lanes.beforeUnlockAllBut();
            return;
        }
        Lanes.lockAllBut();

        if (Arity >= Size) {
            Size = Arity + 1;
            Maps.reserve(Size);
            Maps.resize(Size);
        }
        Maps[Arity] = new GenericRecordMap(Lanes.lanes(), Arity);

        Lanes.beforeUnlockAllBut();
        Lanes.unlockAllBut();
    }
};

}  // namespace souffle
