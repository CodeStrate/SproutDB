from dotenv import load_dotenv
import os
load_dotenv()

SPROUTDB_DIR = os.getenv("SPROUTDB_DIR", ".sproutdb")
NAMESPACE_FILE = f"{SPROUTDB_DIR}/namespace.uuid"