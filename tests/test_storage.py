"""
GraphStorage contract tests.

Updated 2026-10-23 for the add/get split: GraphStorage only owns the write
path plus raw neighbor lookup (_add_node, _add_edge, _neighbors) — all
underscore-prefixed, meant to be called by GraphIndex, not used directly.
Read-friendly getters (get_node, has_node, find_nodes_by_name, get_edge)
live on GraphIndex instead, which is not rewritten yet (still the old
CSR-era self.buf.hash.* code) — those behaviors will come back as
tests/test_index.py once that happens.

These tests access GraphStorage's "private" dicts directly (_nodes,
_name_idx, _succ) where needed — acceptable here because this file is
testing the internal class in isolation, not through its intended caller.

Underlying structure under test:
    _nodes: dict[UUID, Node]
    _succ:  dict[UUID, dict[UUID, dict[str, Edge]]]   # src -> dst -> relation_type -> Edge
    _name_idx: dict[str, list[UUID]]
"""
import pytest

from src.graph.storage import GraphStorage
from src.graph.schemas import Node, Edge


@pytest.fixture
def storage():
    return GraphStorage()


@pytest.fixture
def alice():
    return Node(name="Alice", label="Person", props={"age": 30})


@pytest.fixture
def bob():
    return Node(name="Bob", label="Person", props={"age": 25})


class TestAddNode:
    def test_add_registers_node(self, storage, alice):
        storage._add_node(alice)
        assert storage._nodes[alice.id] == alice

    def test_add_registers_name_index(self, storage, alice):
        storage._add_node(alice)
        assert alice.id in storage._name_idx["Alice"]

    def test_add_initializes_empty_succ_entry(self, storage, alice):
        storage._add_node(alice)
        assert storage._succ[alice.id] == {}

    def test_duplicate_name_creates_two_distinct_nodes(self, storage):
        alice1 = Node(name="Alice", label="Person")
        alice2 = Node(name="Alice", label="Person")
        storage._add_node(alice1)
        storage._add_node(alice2)

        assert alice1.id != alice2.id
        assert set(storage._name_idx["Alice"]) == {alice1.id, alice2.id}

    def test_readding_same_node_id_raises(self, storage, alice):
        storage._add_node(alice)
        with pytest.raises(ValueError):
            storage._add_node(alice)


class TestAddEdge:
    def test_add_edge_requires_existing_src(self, storage, alice, bob):
        storage._add_node(bob)
        edge = Edge(src_id=alice.id, dst_id=bob.id, relation_type="follows")
        with pytest.raises(KeyError):
            storage._add_edge(edge)

    def test_add_edge_requires_existing_dst(self, storage, alice, bob):
        storage._add_node(alice)
        edge = Edge(src_id=alice.id, dst_id=bob.id, relation_type="follows")
        with pytest.raises(KeyError):
            storage._add_edge(edge)

    def test_add_edge_then_neighbors_round_trips(self, storage, alice, bob):
        storage._add_node(alice)
        storage._add_node(bob)
        edge = Edge(src_id=alice.id, dst_id=bob.id, relation_type="follows", props={"since": 2020})
        storage._add_edge(edge)

        fetched = storage._neighbors(alice.id)[bob.id]["follows"]
        assert fetched.relation_type == "follows"
        assert fetched.props == {"since": 2020}

    def test_readding_same_triple_merges_props(self, storage, alice, bob):
        storage._add_node(alice)
        storage._add_node(bob)
        storage._add_edge(Edge(src_id=alice.id, dst_id=bob.id, relation_type="follows", props={"since": 2020}))
        storage._add_edge(Edge(src_id=alice.id, dst_id=bob.id, relation_type="follows", props={"weight": 5}))

        fetched = storage._neighbors(alice.id)[bob.id]["follows"]
        assert fetched.props == {"since": 2020, "weight": 5}

    def test_readding_same_triple_new_props_win_on_conflict(self, storage, alice, bob):
        storage._add_node(alice)
        storage._add_node(bob)
        storage._add_edge(Edge(src_id=alice.id, dst_id=bob.id, relation_type="follows", props={"weight": 1}))
        storage._add_edge(Edge(src_id=alice.id, dst_id=bob.id, relation_type="follows", props={"weight": 2}))

        assert storage._neighbors(alice.id)[bob.id]["follows"].props == {"weight": 2}

    def test_multiple_relation_types_between_same_pair_coexist(self, storage, alice, bob):
        storage._add_node(alice)
        storage._add_node(bob)
        storage._add_edge(Edge(src_id=alice.id, dst_id=bob.id, relation_type="follows"))
        storage._add_edge(Edge(src_id=alice.id, dst_id=bob.id, relation_type="blocked_by"))

        edges = storage._neighbors(alice.id)[bob.id]
        assert set(edges.keys()) == {"follows", "blocked_by"}
        assert edges["follows"].id != edges["blocked_by"].id

    def test_edge_is_directed(self, storage, alice, bob):
        storage._add_node(alice)
        storage._add_node(bob)
        storage._add_edge(Edge(src_id=alice.id, dst_id=bob.id, relation_type="follows"))

        assert storage._neighbors(bob.id) == {}


class TestNeighbors:
    def test_neighbors_empty_for_isolated_node(self, storage, alice):
        storage._add_node(alice)
        assert storage._neighbors(alice.id) == {}

    def test_neighbors_empty_for_unknown_node(self, storage):
        from uuid import uuid4
        assert storage._neighbors(uuid4()) == {}

    def test_neighbors_groups_by_dst_then_relation_type(self, storage, alice, bob):
        storage._add_node(alice)
        storage._add_node(bob)
        storage._add_edge(Edge(src_id=alice.id, dst_id=bob.id, relation_type="follows"))
        storage._add_edge(Edge(src_id=alice.id, dst_id=bob.id, relation_type="blocked_by"))

        neighbors = storage._neighbors(alice.id)
        assert set(neighbors.keys()) == {bob.id}
        assert set(neighbors[bob.id].keys()) == {"follows", "blocked_by"}

    def test_neighbors_does_not_include_incoming_edges(self, storage, alice, bob):
        storage._add_node(alice)
        storage._add_node(bob)
        storage._add_edge(Edge(src_id=alice.id, dst_id=bob.id, relation_type="follows"))

        assert storage._neighbors(bob.id) == {}


class TestEdgeIdentity:
    def test_edge_id_is_deterministic_on_endpoints_and_relation(self, alice, bob):
        e1 = Edge(src_id=alice.id, dst_id=bob.id, relation_type="follows")
        e2 = Edge(src_id=alice.id, dst_id=bob.id, relation_type="follows")
        assert e1.id == e2.id

    def test_edge_id_differs_by_relation_type(self, alice, bob):
        e1 = Edge(src_id=alice.id, dst_id=bob.id, relation_type="follows")
        e2 = Edge(src_id=alice.id, dst_id=bob.id, relation_type="blocked_by")
        assert e1.id != e2.id

    def test_two_distinct_same_named_nodes_do_not_collide_edge_ids(self, bob):
        """Regression test for the bug caught in the 2026-10-01 vault fix: hashing
        src_name/dst_name instead of src_id/dst_id would make two different
        same-named nodes produce the same edge id when connected to a common node."""
        alice1 = Node(name="Alice", label="Person")
        alice2 = Node(name="Alice", label="Person")
        e1 = Edge(src_id=alice1.id, dst_id=bob.id, relation_type="follows")
        e2 = Edge(src_id=alice2.id, dst_id=bob.id, relation_type="follows")
        assert e1.id != e2.id
