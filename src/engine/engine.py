from uuid import uuid4, UUID
import os

from src.utils import SPROUTDB_DIR, NAMESPACE_FILE
from src.graph import GraphStorage, GraphIndex, Node, Edge
from .node_ops import NodeOperations
from .edge_ops import EdgeOperations


class SproutDB:
    def __init__(self):
        self._generate_namespace_uuid()
        self.store = GraphStorage()
        self.index = GraphIndex(self.store)
        self._node_ops = NodeOperations(self.store, self.index)
        self._edge_ops = EdgeOperations(self.store, self.index)

    def _generate_namespace_uuid(self):
        os.makedirs(SPROUTDB_DIR, exist_ok=True)
        try:
            with open(NAMESPACE_FILE, "x", encoding="utf-8") as f:
                f.write(str(uuid4()))
        except FileExistsError:
            pass

    # -- node operations --
    def add_node(self, name: str, label: str, props: dict | None = None) -> Node:
        return self._node_ops.add_node(name, label, props)

    def get_node(self, node_id: UUID) -> Node:
        return self._node_ops.get_node(node_id)

    def has_node(self, node_id: UUID) -> bool:
        return self._node_ops.has_node(node_id)

    def find_node(self, node_name: str) -> Node:
        return self._node_ops.find_node(node_name)

    def find_nodes(self, node_name: str) -> list[Node]:
        return self._node_ops.find_nodes(node_name)

    def get_nodes_by_label(self, label: str) -> list[Node]:
        return self._node_ops.get_nodes_by_label(label)

    # -- edge operations --
    def add_edge(self, src_id: UUID, dst_id: UUID, relation_type: str, props: dict | None = None) -> Edge:
        return self._edge_ops.add_edge(src_id, dst_id, relation_type, props)

    def get_edge(self, src_id: UUID, relation_type: str, dst_id: UUID) -> Edge:
        return self._edge_ops.get_edge(src_id, relation_type, dst_id)

    def get_neighbors(self, node_id: UUID) -> dict[UUID, dict[str, Edge]]:
        return self._edge_ops.get_neighbors(node_id)

    def get_neighbors_by_relation_type(self, node_id: UUID, relation_type: str) -> list[UUID]:
        return self._edge_ops.get_neighbors_by_relation_type(node_id, relation_type)

    def get_neighbor_edges_by_relation_type(self, node_id: UUID, relation_type: str) -> dict[UUID, Edge]:
        return self._edge_ops.get_neighbor_edges_by_relation_type(node_id, relation_type)

    def get_edges_by_relation_type(self, relation_type: str) -> list[Edge]:
        return self._edge_ops.get_edges_by_relation_type(relation_type)
