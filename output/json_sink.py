from __future__ import annotations
import json
from typing import Any, Dict
from core.util import ensure_parent

class JsonSink:
    """
    JSON output sink for writing structured data to NDJSON format.
    
    Appends each record as a separate JSON object line to the specified file.
    Creates parent directories if they don't exist.
    """
    
    def __init__(self, path: str) -> None:
        """
        Initialize JSON sink with output file path.
        
        Args:
            path: File path for JSON output
        """
        self.path = path
        ensure_parent(self.path)

    def write(self, obj: Dict[str, Any]) -> None:
        """
        Write a single object as JSON line to the output file.
        
        Args:
            obj: Dictionary object to serialize and write
        """
        with open(self.path, "a", encoding="utf-8") as f:
            f.write(json.dumps(obj) + "\n")
