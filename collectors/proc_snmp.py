from __future__ import annotations
from typing import Dict, List

SOURCE = "/proc/net/snmp"

NEEDED_COUNTERS = {
    'Ip': {'OutNoRoutes', 'FragFails', 'ReasmFails'},
    'Udp': {'InCsumErrors', 'RcvbufErrors', 'InErrors', 'SndbufErrors'}
}

class ProcNetSnmp:
    """
    Collector for SNMP network statistics from /proc/net/snmp.
    
    Reads and parses kernel network statistics for various protocols and their counters
    defined in an internal dictonary called NEEDED_COUNTERS.
    """
    
    def read(self) -> Dict[str, Dict[str, int]]:
        """
        Read and parse SNMP statistics from /proc/net/snmp.
        
        Returns:
            Dictionary mapping protocol names to their counter values.
            Only includes protocols and counters defined in NEEDED_COUNTERS.
            Also includes a '_source' key with the file path.
        """
        out: Dict[str, Dict[str, int]] = {}
        
        with open(SOURCE, "r", encoding="utf-8") as f:
            lines = [l.strip() for l in f if l.strip()]
        
        for i in range(0, len(lines), 2):
            header = lines[i]; 
            values = lines[i+1]
            
            section = header.split(":")[0]
            
            if section not in NEEDED_COUNTERS:
                continue
            
            keys: List[str] = header.split(":")[1].split()
            vals = list(map(int, values.split(":")[1].split()))
            
            protocol_dict = {}
            for counter, value in zip(keys, vals):
                if counter in NEEDED_COUNTERS[section]:
                    protocol_dict[counter] = value
            
            out[section] = protocol_dict
        
        out["_source"] = SOURCE
        
        return out
