from __future__ import annotations
import time
import os
from typing import Dict, Any
import yaml  # from pyyaml

from core.util import now_ts, hostname
from core.aggregator import Aggregator
from output.json_sink import JsonSink

# Collectors
from collectors.sys_net import SysNet
from collectors.proc_snmp import ProcNetSnmp
from collectors.softnet_stat import SoftnetStat

SCHEMA_VERSION = "1.0"

def load_config(path: str = "config.yml") -> Dict[str, Any]:
    """
    Load configuration from YAML file and override with environment variables.
    
    Environment variables override YAML values:
    - NETDIAG_IFACE: Network interface (e.g., eth0)
    - NETDIAG_POLL_INTERVAL: Polling interval in seconds (e.g., 1.0)
    - NETDIAG_OUTPUT_PATH: Output file path (e.g., /var/log/netdiag/events.json)
    
    Args:
        path: Path to the YAML configuration file
        
    Returns:
        Dictionary containing merged configuration from file and environment variables
    """
    # load configuration from yaml
    try:
        with open(path, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f) or {}
    except FileNotFoundError:
        print(f"Warning: Config file {path} not found, using defaults")
        config = {}
    
    # check for envoirement variables
    if "NETDIAG_IFACE" in os.environ:
        config["iface"] = os.environ["NETDIAG_IFACE"]
    
    if "NETDIAG_POLL_INTERVAL" in os.environ:
        try:
            config["poll_interval_sec"] = float(os.environ["NETDIAG_POLL_INTERVAL"])
        except ValueError:
            print(f"Warning: Invalid NETDIAG_POLL_INTERVAL value: {os.environ['NETDIAG_POLL_INTERVAL']}")
    
    if "NETDIAG_OUTPUT_PATH" in os.environ:
        if "output" not in config:
            config["output"] = {}
        config["output"]["path"] = os.environ["NETDIAG_OUTPUT_PATH"]
    
    return config

def build_snapshot_payload(iface: str) -> Dict[str, Any]:
    """
    Build a snapshot payload containing network metrics from various sources.
    
    Collects data from:
    - SysNet: /sys/class/net/{iface}/carrier and statistics
    - ProcNetSnmp: /proc/net/snmp (IP/UDP/TCP counters)
    
    Args:
        iface: Network interface name to collect data for
        
    Returns:
        Dictionary containing network metrics snapshot
    """
    # Core sources
    sysn  = SysNet(iface).read()                # /sys/carrier(_changes) + statistics/*
    snmp  = ProcNetSnmp().read()                # /proc/net/snmp (Ip/Udp)
    softn = SoftnetStat().read()               # /proc/net/softnet_stat

    payload = {
        "sys_net": sysn,
        "snmp": snmp,
        "softnet": softn,
    }

    return payload

def main() -> None:
    """
    Main application loop for the network diagnostics agent.
    
    This function:
    1. Loads configuration from YAML and environment variables
    2. Initializes data collectors and output sink
    3. Continuously polls network metrics at specified intervals
    4. Generates both snapshot and delta records
    5. Writes data to JSON output sink
    
    The loop runs indefinitely until interrupted.
    """
    
    # load config and intialize objects
    cfg = load_config()
    iface = cfg.get("iface", "envp0")
    interval = float(cfg.get("poll_interval_sec", 1.0))
    out_cfg = cfg.get("output", {"path": "./events.ndjson"})
    sink = JsonSink(out_cfg["path"])

    host = hostname()
    seq = 0
    agg = Aggregator()

    while True:
        ts = now_ts()
        payload_snapshot = build_snapshot_payload(iface)

        # Build numeric tree for delta genaration. Ingore non-counter
        payload_delta = agg.update({
            "sys_net": {
                "carrier_changes" : payload_snapshot["sys_net"].get("carrier_changes", {}),
                "statistics": payload_snapshot["sys_net"].get("statistics", {})
            },
            "snmp": {
                "Ip":  payload_snapshot["snmp"].get("Ip", {}),
                "Udp": payload_snapshot["snmp"].get("Udp", {})
            },
            "softnet": {
                "dropped": payload_snapshot["softnet"].get("dropped", 0),
            }
        })
        
        # remove not changed deltas
        payload_delta = {k:v for k,v in payload_delta.items() if isinstance(v,(int,float)) and v != 0}

        # SNAPSHOT record
        seq += 1
        sink.write({
            "schema_version": SCHEMA_VERSION,
            "record_type": "snapshot",
            "host": host,
            "iface": iface,
            "ts_unix": ts,
            "seq": seq,
            "payload": payload_snapshot,
            "meta": {"interval_sec": interval}
        })

        # DELTA record (if exists)
        if payload_delta:
            seq += 1
            sink.write({
                "schema_version": SCHEMA_VERSION,
                "record_type": "delta",
                "host": host,
                "iface": iface,
                "ts_unix": ts,
                "seq": seq,
                "payload": payload_delta,
                "meta": {"interval_sec": interval}
            })

        time.sleep(interval)

if __name__ == "__main__":
    main()
