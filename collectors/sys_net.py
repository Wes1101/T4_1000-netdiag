from __future__ import annotations
import os
from typing import Dict

SOURCE_CARRIER = "/sys/class/net/{iface}/carrier"
SOURCE_STATS = "/sys/class/net/{iface}/statistics"

class SysNet:
    """
    Collector for network interface information from /sys/class/net.
    
    Collects:
    - Carrier status (UP/DOWN) indicating physical link state
    - Carrier changes count (link flaps)
    - Interface statistics (errors, drops, collisions, etc.)
    """

    def __init__(self, iface: str) -> None:
        """
        Initialize SysNet collector for a specific network interface.
        
        Args:
            iface: Network interface name (e.g., 'eth0', 'enp0s31f6')
        """
        self.iface = iface

    def read(self) -> Dict[str, object]:
        """
        Read network interface information from sysfs.
        
        Returns:
            Dictionary containing:
            - carrier: Link state ("1" for up, "0" for down)
            - carrier_changes: Number of link state changes
            - statistics: Dict of interface statistics (rx/tx counters, errors)
            - _source: Source file paths
        """
        out: Dict[str, object] = {"_source": f"{SOURCE_CARRIER.format(iface=self.iface)}, {SOURCE_STATS.format(iface=self.iface)}"}
        
        # carrier
        try:
            with open(SOURCE_CARRIER.format(iface=self.iface), "r", encoding="utf-8") as f:
                out["carrier"] = f.read().strip()  # "up = 1" | "down = 0"
        except FileNotFoundError:
            out["carrier"] = "unknown"

        try:
            with open(SOURCE_CARRIER.format(iface=self.iface) + "_changes", "r", encoding="utf-8") as f:
                out["carrier_changes"] = f.read().strip()  # changes of the carrier value
        except FileNotFoundError:
            pass

        # statistics/*
        stats_dir = SOURCE_STATS.format(iface=self.iface)
        stats: Dict[str, int] = {}
        try:
            for name in os.listdir(stats_dir):
                p = os.path.join(stats_dir, name)
                try:
                    with open(p, "r", encoding="utf-8") as f:
                        v = int(f.read().strip())
                        stats[name] = v
                except (FileNotFoundError, ValueError):
                    continue
        except FileNotFoundError:
            pass

        out["statistics"] = stats
        
        return out
