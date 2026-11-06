from uuid import uuid4
import os
from src.utils import SPROUTDB_DIR, NAMESPACE_FILE

class SproutDB:
    def __init__(self):
        self._generate_namespace_uuid()
    
    def _generate_namespace_uuid(self):
        os.makedirs(SPROUTDB_DIR, exist_ok=True)
        try:
            with open(NAMESPACE_FILE, "x", encoding="utf-8") as f:
                f.write(str(uuid4()))
        except FileExistsError:
            pass
    