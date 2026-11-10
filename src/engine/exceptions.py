from uuid import UUID
from src.graph import Node

class SproutDBError(Exception):
    pass

class NodeNotFoundError(SproutDBError):
    def __init__(self, node_id: UUID | None = None, name: str | None = None):
        self.node_id = node_id
        self.name = name
        identifier = f"id={node_id}" if node_id is not None else f"name={name}"
        super().__init__(f"No node found with {identifier}")

class EdgeNotFoundError(SproutDBError):
    def __init__(self, src_id: UUID | None, relation_type: str | None, dst_id: UUID | None):
        self.src_id = src_id
        self.dst_id = dst_id
        self.relation_type = relation_type
        super().__init__(f"No Edge ({src_id} -> {relation_type} -> {dst_id}) found.")

class AmbiguousNodeNameError(SproutDBError):
    def __init__(self, name: str, matches: list[Node]):
        self.name = name
        self.matches = matches
        # create a small preview so performance doesn't slog on large Node numbers
        preview = ", ".join(str(n.id) for n in matches[:2])
        remaining = len(matches) - 2
        suffix = f", and {remaining} more" if remaining > 0 else "" # no suffix if only 2 matches
        super().__init__(f"{len(matches)} nodes named {name!r}: {preview}{suffix}") # !r = includes '' using repr() so "'Alice'" instead of just "Alice"