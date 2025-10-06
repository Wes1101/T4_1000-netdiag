from __future__ import annotations
import os, time, socket, pathlib
from typing import Any, Dict

def now_ts() -> float:
    """
    Get current Unix timestamp.
    
    Returns:
        Current time as float seconds since epoch
    """
    return time.time()

def hostname() -> str:
    """
    Get system hostname.
    
    Returns:
        Current system hostname as string
    """
    return socket.gethostname()

def ensure_parent(path: str | os.PathLike) -> None:
    """
    Create parent directories for a file path, if they don't exist.
    
    Args:
        path: File path whose parent directories should be created
    """
    pathlib.Path(path).parent.mkdir(parents=True, exist_ok=True)
