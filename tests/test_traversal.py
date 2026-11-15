import pytest
from uuid import uuid4

from src import SproutDB


@pytest.fixture
def db():
    return SproutDB()


@pytest.fixture
def linear_graph(db):
    """Alice -> Bob -> Carol -> Dave, all via 'follows'."""
    alice = db.add_node("Alice", "Person")
    bob = db.add_node("Bob", "Person")
    carol = db.add_node("Carol", "Robot")
    dave = db.add_node("Dave", "Person")

    db.add_edge(alice.id, bob.id, "follows")
    db.add_edge(bob.id, carol.id, "follows")
    db.add_edge(carol.id, dave.id, "follows")

    return db, alice, bob, carol, dave


class TestBFS:
    def test_bfs_visits_every_reachable_node_with_depth(self, linear_graph):
        db, alice, bob, carol, dave = linear_graph
        result = db.bfs(alice.id)
        assert result == [(alice.id, 0), (bob.id, 1), (carol.id, 2), (dave.id, 3)]

    def test_bfs_unknown_start_returns_empty(self, db):
        assert db.bfs(uuid4()) == []

    def test_bfs_respects_max_depth(self, linear_graph):
        db, alice, bob, carol, dave = linear_graph
        result = db.bfs(alice.id, max_depth=1)
        assert result == [(alice.id, 0), (bob.id, 1)]

    def test_bfs_label_filter_excludes_from_result_but_still_traverses_through(self, linear_graph):
        db, alice, bob, carol, dave = linear_graph
        result = db.bfs(alice.id, node_label="Person")
        node_ids = [n for n, _ in result]
        assert carol.id not in node_ids  # Robot, filtered out of the result
        assert dave.id in node_ids  # still reached by traversing through Carol

    def test_bfs_relation_type_filter(self, db):
        alice = db.add_node("Alice", "Person")
        bob = db.add_node("Bob", "Person")
        carol = db.add_node("Carol", "Person")
        db.add_edge(alice.id, bob.id, "follows")
        db.add_edge(alice.id, carol.id, "blocked_by")

        result = db.bfs(alice.id, relation_type="follows")
        node_ids = [n for n, _ in result]
        assert bob.id in node_ids
        assert carol.id not in node_ids


class TestShortestPathUnweighted:
    def test_bfs_shortest_path_returns_full_hop_sequence(self, linear_graph):
        db, alice, bob, carol, dave = linear_graph
        path = db.shortest_path(alice.id, dave.id)
        assert path == [alice.id, bob.id, carol.id, dave.id]

    def test_shortest_path_same_start_and_end(self, linear_graph):
        db, alice, *_ = linear_graph
        assert db.shortest_path(alice.id, alice.id) == [alice.id]

    def test_shortest_path_no_path_returns_empty(self, db):
        alice = db.add_node("Alice", "Person")
        bob = db.add_node("Bob", "Person")
        assert db.shortest_path(alice.id, bob.id) == []

    def test_shortest_path_unknown_node_returns_empty(self, db):
        alice = db.add_node("Alice", "Person")
        assert db.shortest_path(alice.id, uuid4()) == []


class TestShortestPathWeighted:
    def test_dijkstra_prefers_lower_weight_parallel_edge(self, db):
        """Regression-shape test: Alice->Dave has two parallel edges of different
        relation types; the multigraph must relax both independently rather than
        collapsing them to one edge per neighbor (see Neo4j/Kuzu parallel-edge
        semantics — each relationship stays its own candidate)."""
        alice = db.add_node("Alice", "Person")
        dave = db.add_node("Dave", "Person")
        db.add_edge(alice.id, dave.id, "shortcut", props={"weight": 1})
        db.add_edge(alice.id, dave.id, "longway", props={"weight": 50})

        path = db.shortest_path(alice.id, dave.id, weight_key="weight")
        assert path == [alice.id, dave.id]

    def test_dijkstra_takes_cheaper_multi_hop_over_pricier_direct_edge(self, db):
        alice = db.add_node("Alice", "Person")
        bob = db.add_node("Bob", "Person")
        dave = db.add_node("Dave", "Person")
        db.add_edge(alice.id, bob.id, "follows", props={"weight": 1})
        db.add_edge(bob.id, dave.id, "follows", props={"weight": 1})
        db.add_edge(alice.id, dave.id, "shortcut", props={"weight": 10})

        path = db.shortest_path(alice.id, dave.id, weight_key="weight")
        assert path == [alice.id, bob.id, dave.id]

    def test_missing_weight_defaults_to_one(self, linear_graph):
        db, alice, bob, carol, dave = linear_graph
        path = db.shortest_path(alice.id, dave.id, weight_key="weight")
        assert path == [alice.id, bob.id, carol.id, dave.id]

    def test_relation_type_filter_ignores_cheaper_edge_of_other_relation(self, db):
        alice = db.add_node("Alice", "Person")
        bob = db.add_node("Bob", "Person")
        carol = db.add_node("Carol", "Person")
        dave = db.add_node("Dave", "Person")
        db.add_edge(alice.id, bob.id, "follows", props={"weight": 1})
        db.add_edge(bob.id, carol.id, "follows", props={"weight": 1})
        db.add_edge(carol.id, dave.id, "follows", props={"weight": 1})
        db.add_edge(alice.id, dave.id, "shortcut", props={"weight": 1})

        path = db.shortest_path(alice.id, dave.id, weight_key="weight", relation_type="follows")
        assert path == [alice.id, bob.id, carol.id, dave.id]

    def test_negative_weight_raises(self, db):
        alice = db.add_node("Alice", "Person")
        bob = db.add_node("Bob", "Person")
        db.add_edge(alice.id, bob.id, "follows", props={"weight": -1})

        with pytest.raises(ValueError):
            db.shortest_path(alice.id, bob.id, weight_key="weight")

    def test_cheaper_indirect_route_overrides_earlier_direct_relaxation(self, db):
        """Regression-shape test: a node first reached via a pricier direct edge
        must be re-relaxed to the cheaper route found afterward, and the stale
        heap entry for the pricier route must not corrupt the final path."""
        alice = db.add_node("Alice", "Person")
        bob = db.add_node("Bob", "Person")
        carol = db.add_node("Carol", "Person")
        dave = db.add_node("Dave", "Person")
        db.add_edge(alice.id, bob.id, "follows", props={"weight": 5})
        db.add_edge(alice.id, carol.id, "follows", props={"weight": 1})
        db.add_edge(carol.id, bob.id, "follows", props={"weight": 1})
        db.add_edge(bob.id, dave.id, "follows", props={"weight": 1})

        path = db.shortest_path(alice.id, dave.id, weight_key="weight")
        assert path == [alice.id, carol.id, bob.id, dave.id]
