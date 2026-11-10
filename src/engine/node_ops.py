from src.graph import GraphStorage, GraphIndex, Node
from uuid import UUID
from .exceptions import NodeNotFoundError, AmbiguousNodeNameError 

class NodeOperations:
    def __init__(self, store: GraphStorage, index: GraphIndex):
        self.store = store
        self.index = index

    def add_node(self, name: str, label: str, props: dict | None = None) -> Node:
        new_node = Node(name=name, label=label, props=props or {})
        self.index.add_node(new_node)
        return new_node

    def get_node(self, node_id: UUID) -> Node:
        node = self.store._nodes.get(node_id)
        if node is None:
            raise NodeNotFoundError(node_id=node_id)
        return node

    def has_node(self, node_id: UUID) -> bool:
        return node_id in self.store._nodes

    def find_nodes(self, node_name: str) -> list[Node]:
        node_ids = self.store._name_idx.get(node_name, [])
        return [self.store._nodes[node_id] for node_id in node_ids]

    def find_node(self, node_name: str) -> Node:
        matches = self.find_nodes(node_name)
        if not matches:
            raise NodeNotFoundError(name=node_name)
        if len(matches) > 1:
            raise AmbiguousNodeNameError(node_name, matches)

        return matches[0]

    def get_nodes_by_label(self, label: str) -> list[Node]:
        node_ids = self.index.get_nodes_by_label(label)
        return [self.store._nodes[node_id] for node_id in node_ids]