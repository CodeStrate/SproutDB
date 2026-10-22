from .schemas import Node, Edge
from uuid import UUID

class GraphStorage:
    def __init__(self):
        self._nodes: dict[UUID, Node] = {} # node_id -> Node object
        self._succ: dict[UUID, dict[UUID, dict[str, Edge]]] = {} # src_id -> dst_id
        self._name_idx: dict[str, list[UUID]] = {} # name -> [node_id, ...] can support duplicate names (i.e. Bob can be 2 diff nodes)

    
    def _add_node(self, node: Node) -> None:
        if node.id in self._nodes:
            raise ValueError(f"Node of ID {node.id} already exists")

        self._nodes[node.id] = node
        self._name_idx.setdefault(node.name, []).append(node.id)
        self._succ.setdefault(node.id, {})

    def _add_edge(self, edge: Edge) -> None:
        if edge.src_id not in self._nodes or edge.dst_id not in self._nodes:
            raise KeyError(f"Both edge endpoints must exist in the graph.")

        edge_by_dst = self._succ[edge.src_id]
        edge_by_relation = edge_by_dst.setdefault(edge.dst_id, {})

        # duplicate edge relation is prop update
        if edge.relation_type in edge_by_relation:
            edge_by_relation[edge.relation_type].props.update(edge.props)
            return

        edge_by_relation[edge.relation_type] = edge

    def _neighbors(self, node_id: UUID) -> dict[UUID, dict[str, Edge]]:
        return self._succ.get(node_id, {})