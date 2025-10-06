from __future__ import annotations
from typing import Dict, List

SOURCE = "/proc/net/softnet_stat"

class SoftnetStat:
    """
    Sums 'dropped' and 'time_squeeze' across all CPUs.
    Fields are hexadecimal: 0=processed, 1=dropped, 2=time_squeeze, ...
    """
    def read(self) -> Dict[str, int | str]:
        total_dropped = 0
        try:
            with open(SOURCE, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    cols = line.split()
                    if len(cols) >= 3:
                        total_dropped += int(cols[1], 16)
            return {"_source": SOURCE, "dropped": total_dropped}
        except FileNotFoundError:
            return {"_source": SOURCE, "dropped": 0}
