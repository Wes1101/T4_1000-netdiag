"""
report_ndjson.py
Reads NDJSON logs from the agent (record_type=="delta") and outputs a hierarchical
analysis: Layer -> Component -> Counter, both absolute and percentage.

Usage:
    python3 report_ndjson.py /path/to/events.ndjson
"""

import sys
import json
from collections import defaultdict, OrderedDict
from typing import Tuple, Dict

# ---------------------- Mapping Rules ----------------------

def map_bucket(key: str) -> Tuple[str, str]:
    """
    Maps a metric key to a (Layer, Component) pair.
    Layer: L1/L2/L3/L4/Other
    Component: Finer subdivision (e.g., NIC/MAC vs. KernelPath)
    """
    # L1 Physical
    if key.startswith("sys_net.") and key.endswith(".rx_crc_errors"):
        return ("L1:Physical", "CRC/Signal")

    # L2 DataLink (NIC/MAC)
    if key.startswith("sys_net.") and any(
        s in key for s in (
            ".rx_dropped", ".rx_missed_errors", ".collisions",
            ".tx_errors", ".tx_carrier_errors", ".tx_window_errors"
        )
    ):
        return ("L2:DataLink", "NIC/MAC")

    # L2 DataLink (KernelPath)
    if key.startswith("softnet."):
        return ("L2:DataLink", "KernelPath")

    # L3 Network
    if key.startswith("snmp.Ip.") and any(
        s in key for s in ("OutNoRoutes", "FragFails", "ReasmFails")
    ):
        return ("L3:Network", "IP")

    # L4 UDP
    if key.startswith("snmp.Udp.") and any(
        s in key for s in ("InErrors", "InCsumErrors", "RcvbufErrors", "SndbufErrors", "NoPorts")
    ):
        return ("L4:UDP", "UDP")

    return ("Other", "Other")

def source_of(key: str) -> str:
    """
    Returns the Linux source for each metric key (for display).
    """
    if key.startswith("sys_net."):
        if key.endswith(".carrier"):
            return "/sys/class/net/<iface>/*"
        return "/sys/class/net/<iface>/statistics/*"
    if key.startswith("snmp."):     return "/proc/net/snmp"
    if key.startswith("softnet."):  return "/proc/net/softnet_stat"
    
    return "(unknown)"

# ---------------------- Analysis ----------------------

def fmt_pct(n: float) -> str:
    return f"{n:5.1f}%"

def main(path: str) -> None:
    # Aggregation containers
    totals_global = 0
    by_layer: Dict[str, int] = defaultdict(int)
    by_layer_comp: Dict[Tuple[str, str], int] = defaultdict(int)
    by_counter: Dict[str, int] = defaultdict(int)
    counter_src: Dict[str, str] = {}

    # Read NDJSON
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue
            if rec.get("record_type") != "delta":
                continue
            payload = rec.get("payload", {})
            if not isinstance(payload, dict):
                continue
            for k, v in payload.items():
                if isinstance(v, (int, float)) and v != 0:
                    layer, comp = map_bucket(k)
                    by_counter[k] += int(v)
                    by_layer[layer] += int(v)
                    by_layer_comp[(layer, comp)] += int(v)
                    totals_global += int(v)
                    counter_src.setdefault(k, source_of(k))

    if totals_global == 0:
        print("No numeric delta values > 0 found.")
        return

    # Output: Summary by Layer
    print("=== Error shares by Layer ===")
    for layer, val in sorted(by_layer.items(), key=lambda x: -x[1]):
        print(f"{layer:26s} {val:10d}  ({fmt_pct(val / totals_global * 100)})")
    print(f"{'Total errors/drops':26s} {totals_global:10d}\n")

    # Stable order of layers for detailed view
    layer_order = ["L1:Physical", "L2:DataLink", "L3:Network", "L4:UDP", "Other"]

    # Per Layer: Components + Counters
    for layer in layer_order:
        # Which components exist in this layer?
        comps = [(lc[1], val) for lc, val in by_layer_comp.items() if lc[0] == layer]
        if not comps:
            continue
        layer_sum = by_layer[layer]
        print(f"## {layer}  (Sum: {layer_sum}, Share of total: {fmt_pct(layer_sum/totals_global*100)})")

        # Components sorted
        comp_names_sorted = [name for name, _ in sorted(comps, key=lambda x: -x[1])]
        for comp in comp_names_sorted:
            comp_sum = by_layer_comp[(layer, comp)]
            print(f"  - Component: {comp}  "
                  f"(Sum: {comp_sum}, "
                  f"Share of layer: {fmt_pct(comp_sum/layer_sum*100)}, "
                  f"Share of total: {fmt_pct(comp_sum/totals_global*100)})")

            # All counters of this component, sorted by value
            counters = [(k, v) for k, v in by_counter.items() if map_bucket(k) == (layer, comp)]
            counters.sort(key=lambda kv: -kv[1])

            # Print all counters
            for k, v in counters:
                pct_comp = v / comp_sum * 100 if comp_sum else 0.0
                pct_total = v / totals_global * 100
                src = counter_src.get(k, "(unknown)")
                print(f"      • {k:70s} {v:10d}  "
                      f"[{fmt_pct(pct_comp)} of comp., {fmt_pct(pct_total)} total]   <{src}>")
        print()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 report_ndjson.py /path/to/events.ndjson")
        sys.exit(1)
    main(sys.argv[1])
