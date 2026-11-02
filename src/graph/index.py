from collections import defaultdict
from uuid import UUID
from src.graph.schemas import Node, Edge, EdgeKey
from src.graph.storage import GraphStorage


class GraphIndex:
    def __init__(self, store: GraphStorage):
        self.relation_index: defaultdict[str, defaultdict[UUID, list[UUID]]] = defaultdict(lambda: defaultdict(list))
        self.label_to_node_index: dict[str, list[UUID]] = defaultdict(list) # label : [node_ids...]
        self.node_to_label_index: dict[UUID, str] = {} # node_id : label
        self.store = store

    def add_node(self, node: Node):
        self.store._add_node(node)
        self.node_to_label_index[node.id] = node.label
        self.label_to_node_index[node.label].append(node.id)

    def add_edge(self, edge: Edge):
        self.store._add_edge(edge)
        if edge.dst_id not in self.relation_index[edge.relation_type][edge.src_id]:
            self.relation_index[edge.relation_type][edge.src_id].append(edge.dst_id)

    def get_node_label(self, node_id: UUID) -> str:
        return self.node_to_label_index[node_id]

    def get_nodes_by_label(self, node_label: str) -> list[UUID]:
        return self.label_to_node_index[node_label]

    def get_neighbor_edges(self, node_id: UUID):
        return self.store._neighbors(node_id)
    
    def get_edge(self, key: EdgeKey):
        pass

    def get_neighbors(self, node_id: UUID):
        pass