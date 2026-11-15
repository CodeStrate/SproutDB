from src.graph import GraphStorage, GraphIndex, Edge
from .exceptions import NodeNotFoundError, EdgeNotFoundError
from uuid import UUID


class EdgeOperations:
    def __init__(self, store: GraphStorage, index: GraphIndex):
        self.store = store
        self.index = index

    def add_edge(self, src_id: UUID, dst_id: UUID, relation_type: str, props: dict | None = None) -> Edge:
        if src_id not in self.store._nodes:
            raise NodeNotFoundError(node_id=src_id)
        if dst_id not in self.store._nodes:
            raise NodeNotFoundError(node_id=dst_id)
        new_edge = Edge(src_id=src_id, dst_id=dst_id, relation_type=relation_type, props=props or {})
        self.index.add_edge(new_edge)
        return new_edge

    def get_edge(self, src_id: UUID, relation_type: str, dst_id: UUID) -> Edge:
        if src_id not in self.store._nodes:
            raise NodeNotFoundError(node_id=src_id)
        if dst_id not in self.store._nodes:
            raise NodeNotFoundError(node_id=dst_id)
        try:
            return self.index.get_edge((src_id, relation_type, dst_id))
        except KeyError:
            raise EdgeNotFoundError(src_id, relation_type, dst_id)

    def get_neighbors(self, node_id: UUID) -> dict[UUID, dict[str, Edge]]:
        return self.index.get_neighbors(node_id)

    def get_neighbors_by_relation_type(self, node_id: UUID, relation_type: str) -> list[UUID]:
        return self.index.get_neighbors_by_relation_type(node_id, relation_type)

    def get_neighbor_edges_by_relation_type(self, node_id: UUID, relation_type: str) -> dict[UUID, Edge]:
        return self.index.get_neighbor_edges_by_relation_type(node_id, relation_type)

    def get_edges_by_relation_type(self, relation_type: str) -> list[Edge]:
        edges = []
        for src_id, dst_ids in self.index.relation_index.get(relation_type, {}).items():
            for dst_id in dst_ids:
                edges.append(self.index.get_edge((src_id, relation_type, dst_id)))
        return edges

