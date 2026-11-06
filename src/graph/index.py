from collections import defaultdict
from uuid import UUID
from .schemas import Node, Edge, EdgeKey
from .storage import GraphStorage


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
        label = self.node_to_label_index.get(node_id)
        if label is None:
            raise KeyError(f"Label for {node_id} not Found.")
        return label

    def get_nodes_by_label(self, node_label: str) -> list[UUID]:
        return self.label_to_node_index.get(node_label, [])

    def get_neighbors(self, node_id: UUID):
        return self.store._neighbors(node_id)
    
    def get_edge(self, key: EdgeKey) -> Edge:
        src_id, relation_type, dst_id = key
        neighbors = self.store._neighbors(src_id)
        dst_edges = neighbors.get(dst_id)
        if dst_edges is None:
            raise KeyError(f"Source {src_id} has no destination edges.")
        edge = dst_edges.get(relation_type)
        if edge is None:
            raise KeyError(f"Edge between {src_id}->{dst_id} not found.")
        return edge

    def get_neighbors_by_relation_type(self, node_id: UUID, relation_type: str):
        relation_edges = self.relation_index.get(relation_type, {})
        neighbors = relation_edges.get(node_id, [])
        return neighbors

    def get_neighbor_edges_by_relation_type(self, node_id: UUID, relation_type: str):
        neighbor_edges: dict[UUID, Edge] = {}
        relation_neighbors = self.get_neighbors_by_relation_type(node_id, relation_type)
        for neighbor in relation_neighbors:
            edge_key = (node_id, relation_type, neighbor)
            neighbor_edges[neighbor] = self.get_edge(edge_key)

        return neighbor_edges