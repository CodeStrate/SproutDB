from collections import deque
import heapq
from src.graph import GraphIndex


class GraphTraversal:
    def __init__(self, index: GraphIndex):
        self.index = index

    def bfs(self, start, relation_type=None, node_label=None, max_depth=None):
        if start not in self.index.store._nodes:
            return []
        
        visited_set = set()
        traversed_path: list[tuple] = [] # nodes + edges
        q = deque()
        visited_set.add(start)
        q.append((start, 0)) # 0 is depth

        while q:
            current_node, depth = q.popleft()
            # Move the label filter in the end. traversing by label will break under this case Person -> Person -> Book,
            # if Person gets dropped Book label isn't reached
            # Better move is filter nodes by label as we append.
            if node_label is None or self.index.get_node_label(current_node) == node_label:
                traversed_path.append((current_node, depth))
            if max_depth is not None and depth >= max_depth:
                continue # skips all nodes past depth but still computes nodes at max_depth by ignoring.
            neighbors = self.index.get_neighbors(current_node) if relation_type is None else self.index.get_neighbors_by_relation_type(current_node, relation_type)
            for neighbor in neighbors:
                if neighbor not in visited_set:
                    visited_set.add(neighbor)
                    q.append((neighbor, depth + 1))
            
        
        return traversed_path

    def shortest_path(self, start, end, weight_key=None, relation_type=None): # dijkstra if weight, fall back to bfs otherwise
        if start not in self.index.store._nodes or end not in self.index.store._nodes:
            return []

        if start == end:
            return [start]

        if weight_key is None:
            return self._bfs_shortest_path(start, end, relation_type)
        return self._dijkstra_shortest_path(start, end, weight_key, relation_type)

    def _bfs_shortest_path(self, start, end, relation_type=None):
        parent = {start: None}
        q = deque([start])

        while q:
            current_node = q.popleft()
            if current_node == end:
                return self._reconstruct_path(parent, end)
            neighbors = self.index.get_neighbors(current_node) if relation_type is None else self.index.get_neighbors_by_relation_type(current_node, relation_type)
            for neighbor in neighbors:
                if neighbor not in parent:
                    parent[neighbor] = current_node
                    q.append(neighbor)

        return []

    def _dijkstra_shortest_path(self, start, end, weight_key, relation_type=None):
        parent = {start: None}
        dist = {start: 0}
        heap = [(0, start)]

        while heap:
            current_dist, current_node = heapq.heappop(heap)
            if current_node == end:
                return self._reconstruct_path(parent, end)
            if current_dist > dist[current_node]:
                continue # stale entry: a shorter path to this node was already found

            if relation_type is None:
                # unfiltered as every (neighbor, relation_type) edge is its own candidate —
                # a multigraph with parallel edges of different weights isn't collapsed
                # to one edge per neighbor

                neighbor_edges = self.index.get_neighbors(current_node) # dict[UUID, dict[str, Edge]]
                edge_candidates = (
                    (neighbor, edge)
                    for neighbor, edges_by_relation in neighbor_edges.items()
                    for edge in edges_by_relation.values()
                )
            else:
                neighbor_edges = self.index.get_neighbor_edges_by_relation_type(current_node, relation_type) # dict[UUID, Edge]
                edge_candidates = neighbor_edges.items()

            for neighbor, edge in edge_candidates:
                weight = edge.props.get(weight_key, 1)
                if weight < 0:
                    raise ValueError(
                        f"Negative edge weight ({weight}) between {current_node} and {neighbor} "
                        "is not supported by Dijkstra's algorithm."
                    )

                new_dist = current_dist + weight
                if new_dist < dist.get(neighbor, float('inf')):
                    dist[neighbor] = new_dist
                    parent[neighbor] = current_node
                    heapq.heappush(heap, (new_dist, neighbor))

        return []

    @staticmethod
    def _reconstruct_path(parent, end):
        path = []
        node = end
        while node is not None:
            path.append(node)
            node = parent[node]
        path.reverse()
        return path
