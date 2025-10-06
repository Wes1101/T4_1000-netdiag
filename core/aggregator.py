from __future__ import annotations
from typing import Any, Dict

class Aggregator:
    """
    Calculates deltas between consecutive metric snapshots.
    """
    
    def __init__(self) -> None:
        """Initialize aggregator with no previous snapshot."""
        self._prev: Dict[str, Any] | None = None

    def update(self, snapshot: Dict[str, Any]) -> Dict[str, Any]:
        """
        Calculate deltas between current and previous snapshot.
        
        Args:
            snapshot: Current metrics snapshot
            
        Returns:
            Dictionary containing delta values for numeric counters.
            Empty dict on first call (no previous snapshot available).
        """
        if self._prev is None:
            self._prev = snapshot
            return {}
        deltas: Dict[str, Any] = {}
        self._diff("", self._prev, snapshot, deltas)
        self._prev = snapshot
        return deltas

    def _diff(self, path: str, a: Any, b: Any, out: Dict[str, Any]) -> None:
        """
        Recursively calculate differences between two values.
        
        Args:
            path: Dot-separated path to current value in nested dict
            a: Previous value
            b: Current value
            out: Output dictionary to store deltas
        """
        if isinstance(a, dict) and isinstance(b, dict):
            for k in b.keys():
                if k in a:
                    key = f"{path}.{k}" if path else k
                    self._diff(key, a[k], b[k], out)
        elif isinstance(a, int) and isinstance(b, int):
            d = b - a
            if d < 0:
                d = b  # reset/wrap
            out[path] = d
        elif isinstance(a, float) and isinstance(b, float):
            out[path] = b - a
        else:
            if a != b:
                out[path] = b
