from uuid import UUID

class SproutDBError(Exception):
    pass

class NodeNotFoundError(SproutDBError):
    def __init__(self, node_id: UUID | None = None, name: str | None = None):
        self.node_id = node_id
        self.name = name
        identifier = f"id={node_id}" if node_id is not None else f"name={name}"
        super().__init__(f"No node found with {identifier}")

        