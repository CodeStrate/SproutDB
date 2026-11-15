import pytest
from uuid import uuid4

from src.graph.storage import GraphStorage
from src.graph.index import GraphIndex
from src.graph.schemas import Node, Edge


@pytest.fixture
def storage():
    return GraphStorage()


@pytest.fixture
def index(storage):
    return GraphIndex(storage)


@pytest.fixture
def alice():
    return Node(name="Alice", label="Person", props={"age": 30})


@pytest.fixture
def bob():
    return Node(name="Bob", label="Person", props={"age": 25})


@pytest.fixture
def carol():
    return Node(name="Carol", label="Robot")


class TestAddNode:
    def test_add_node_delegates_to_storage(self, index, storage, alice):
        index.add_node(alice)
        assert storage._nodes[alice.id] == alice

    def test_add_node_populates_label_to_node_index(self, index, alice, bob):
        index.add_node(alice)
        index.add_node(bob)
        assert set(index.get_nodes_by_label("Person")) == {alice.id, bob.id}

    def test_add_node_populates_node_to_label_index(self, index, alice):
        index.add_node(alice)
        assert index.get_node_label(alice.id) == "Person"

    def test_different_labels_do_not_mix(self, index, alice, carol):
        index.add_node(alice)
        index.add_node(carol)
        assert index.get_nodes_by_label("Person") == [alice.id]
        assert index.get_nodes_by_label("Robot") == [carol.id]

    def test_duplicate_name_both_appear_under_label_index(self, index):
        alice1 = Node(name="Alice", label="Person")
        alice2 = Node(name="Alice", label="Person")
        index.add_node(alice1)
        index.add_node(alice2)
        assert set(index.get_nodes_by_label("Person")) == {alice1.id, alice2.id}

    def test_readding_same_node_id_raises_and_does_not_corrupt_label_index(self, index, alice):
        index.add_node(alice)
        with pytest.raises(ValueError):
            index.add_node(alice)
        # still exactly one entry, not two, after the failed re-add
        assert index.get_nodes_by_label("Person") == [alice.id]


class TestAddEdge:
    def test_add_edge_requires_existing_endpoints(self, index, alice, bob):
        index.add_node(bob)
        edge = Edge(src_id=alice.id, dst_id=bob.id, relation_type="follows")
        with pytest.raises(KeyError):
            index.add_edge(edge)

    def test_add_edge_does_not_corrupt_relation_index_on_failure(self, index, alice, bob):
        index.add_node(bob)
        edge = Edge(src_id=alice.id, dst_id=bob.id, relation_type="follows")
        with pytest.raises(KeyError):
            index.add_edge(edge)
        # the whole point of validating in storage first: a failed add leaves no trace
        assert index.get_neighbors_by_relation_type(alice.id, "follows") == []

    def test_add_edge_populates_relation_index(self, index, alice, bob):
        index.add_node(alice)
        index.add_node(bob)
        index.add_edge(Edge(src_id=alice.id, dst_id=bob.id, relation_type="follows"))

        assert index.get_neighbors_by_relation_type(alice.id, "follows") == [bob.id]

    def test_relation_index_dedups_on_repeated_add(self, index, alice, bob):
        index.add_node(alice)
        index.add_node(bob)
        index.add_edge(Edge(src_id=alice.id, dst_id=bob.id, relation_type="follows", props={"a": 1}))
        index.add_edge(Edge(src_id=alice.id, dst_id=bob.id, relation_type="follows", props={"b": 2}))

        assert index.get_neighbors_by_relation_type(alice.id, "follows") == [bob.id]

    def test_different_relation_types_coexist_in_relation_index(self, index, alice, bob):
        index.add_node(alice)
        index.add_node(bob)
        index.add_edge(Edge(src_id=alice.id, dst_id=bob.id, relation_type="follows"))
        index.add_edge(Edge(src_id=alice.id, dst_id=bob.id, relation_type="blocked_by"))

        assert index.get_neighbors_by_relation_type(alice.id, "follows") == [bob.id]
        assert index.get_neighbors_by_relation_type(alice.id, "blocked_by") == [bob.id]

    def test_relation_index_is_directed(self, index, alice, bob):
        index.add_node(alice)
        index.add_node(bob)
        index.add_edge(Edge(src_id=alice.id, dst_id=bob.id, relation_type="follows"))

        assert index.get_neighbors_by_relation_type(bob.id, "follows") == []

    def test_unknown_relation_type_returns_empty_not_keyerror(self, index, alice):
        index.add_node(alice)
        assert index.get_neighbors_by_relation_type(alice.id, "nonexistent") == []

    def test_unknown_relation_type_does_not_pollute_relation_index(self, index, alice):
        index.add_node(alice)
        index.get_neighbors_by_relation_type(alice.id, "nonexistent")
        # querying an unknown relation type must not plant a phantom entry
        assert "nonexistent" not in index.relation_index


class TestGetEdge:
    def test_get_edge_round_trips(self, index, alice, bob):
        index.add_node(alice)
        index.add_node(bob)
        index.add_edge(Edge(src_id=alice.id, dst_id=bob.id, relation_type="follows", props={"since": 2020}))

        edge = index.get_edge((alice.id, "follows", bob.id))
        assert edge.props == {"since": 2020}

    def test_get_edge_missing_relation_raises(self, index, alice, bob):
        index.add_node(alice)
        index.add_node(bob)
        with pytest.raises(KeyError):
            index.get_edge((alice.id, "follows", bob.id))

    def test_get_edge_missing_dst_raises(self, index, alice, bob, carol):
        index.add_node(alice)
        index.add_node(bob)
        index.add_node(carol)
        index.add_edge(Edge(src_id=alice.id, dst_id=carol.id, relation_type="follows"))
        with pytest.raises(KeyError):
            index.get_edge((alice.id, "follows", bob.id))

    def test_get_edge_unknown_src_raises(self, index, bob):
        index.add_node(bob)
        with pytest.raises(KeyError):
            index.get_edge((uuid4(), "follows", bob.id))

    def test_get_edge_does_not_pollute_storage_on_miss(self, index, storage, alice, bob):
        index.add_node(alice)
        index.add_node(bob)
        with pytest.raises(KeyError):
            index.get_edge((alice.id, "follows", bob.id))
        # a missed lookup must not plant a phantom entry back into real storage
        assert storage._neighbors(alice.id) == {}


class TestGetNeighbors:
    def test_get_neighbors_delegates_to_storage(self, index, storage, alice, bob):
        index.add_node(alice)
        index.add_node(bob)
        index.add_edge(Edge(src_id=alice.id, dst_id=bob.id, relation_type="follows"))

        assert index.get_neighbors(alice.id) == storage._neighbors(alice.id)


class TestLabelIndexConsistency:
    def test_every_label_entry_matches_reverse_entry(self, index, alice, bob, carol):
        index.add_node(alice)
        index.add_node(bob)
        index.add_node(carol)

        for label in ("Person", "Robot"):
            for node_id in index.get_nodes_by_label(label):
                assert index.get_node_label(node_id) == label

    def test_get_nodes_by_label_empty_for_unknown_label(self, index):
        assert index.get_nodes_by_label("Nonexistent") == []

    def test_get_nodes_by_label_unknown_does_not_pollute_index(self, index):
        index.get_nodes_by_label("Nonexistent")
        assert "Nonexistent" not in index.label_to_node_index


class TestGetNeighborEdgesByRelationType:
    def test_returns_edges_keyed_by_neighbor(self, index, alice, bob, carol):
        index.add_node(alice)
        index.add_node(bob)
        index.add_node(carol)
        index.add_edge(Edge(src_id=alice.id, dst_id=bob.id, relation_type="follows", props={"x": 1}))
        index.add_edge(Edge(src_id=alice.id, dst_id=carol.id, relation_type="follows", props={"x": 2}))
        index.add_edge(Edge(src_id=alice.id, dst_id=bob.id, relation_type="blocked_by"))

        result = index.get_neighbor_edges_by_relation_type(alice.id, "follows")
        assert set(result.keys()) == {bob.id, carol.id}
        assert result[bob.id].props == {"x": 1}
        assert result[carol.id].props == {"x": 2}

    def test_empty_dict_for_unknown_relation_type(self, index, alice):
        index.add_node(alice)
        assert index.get_neighbor_edges_by_relation_type(alice.id, "nonexistent") == {}

    def test_does_not_recurse_infinitely(self, index, alice, bob):
        """Regression test: this method was briefly calling itself instead of
        get_neighbors_by_relation_type, causing a RecursionError on any call."""
        index.add_node(alice)
        index.add_node(bob)
        index.add_edge(Edge(src_id=alice.id, dst_id=bob.id, relation_type="follows"))
        # if this hangs or raises RecursionError, the bug is back
        result = index.get_neighbor_edges_by_relation_type(alice.id, "follows")
        assert bob.id in result


class TestEdgeIdentity:
    def test_edge_id_is_deterministic_on_endpoints_and_relation(self, alice, bob):
        e1 = Edge(src_id=alice.id, dst_id=bob.id, relation_type="follows")
        e2 = Edge(src_id=alice.id, dst_id=bob.id, relation_type="follows")
        assert e1.id == e2.id

    def test_edge_id_differs_by_relation_type(self, alice, bob):
        e1 = Edge(src_id=alice.id, dst_id=bob.id, relation_type="follows")
        e2 = Edge(src_id=alice.id, dst_id=bob.id, relation_type="blocked_by")
        assert e1.id != e2.id
