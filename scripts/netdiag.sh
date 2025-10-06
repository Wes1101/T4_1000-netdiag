#!/usr/bin/bash
set -euo pipefail

# Defaults
IFACE="eth0"
BIND_IP=""
OUT="/var/log/netdiag/events.ndjson"
AGENT_PY="../agent.py"
DURATION=30
BANDWIDTH="90M"
PROTOCOL="udp"    
TARGET=""                                   # error if empty
PORT=5200
PARALLEL=1
TOPN=10

usage() {
  cat <<EOF
Usage: $(basename "$0") [-i iface] [-B iface ip] [-o out.ndjson] [-a agent.py] [-d sec] [-b bw] [-t host] [-p port]
  -i  Interface                      (default: $IFACE)
  -B  Binding IP adress for iperf3   (default: iface IP)
  -o  NDJSON output file             (default: $OUT)
  -a  Path to agent.py               (default: $AGENT_PY)
  -d  iperf3 duration (seconds)      (default: $DURATION)
  -b  iperf3 bandwidth               (default: $BANDWIDTH)
  -t  Target host                     
  -p  Port                           (default: $PORT)
  -h  Help
EOF
}

# parse arguments with getopts
while getopts "i:B:o:a:d:b:P:t:p:h" opt; do
  case "$opt" in
    i) IFACE="$OPTARG" ;;
    B) BIND_IP="$OPTARG" ;;
    o) OUT="$OPTARG" ;;
    a) AGENT_PY="$OPTARG" ;;
    d) DURATION="$OPTARG" ;;
    b) BANDWIDTH="$OPTARG" ;;
    s) START_SERVER=1 ;;
    t) TARGET="$OPTARG" ;;
    p) PORT="$OPTARG" ;;
    h) usage; exit 0 ;;
    \?) echo "Unknown option: -$OPTARG" >&2; usage; exit 1 ;;
    :)  echo "Option -$OPTARG needs an argument." >&2; usage; exit 1 ;;
  esac
done

# Checks
command -v python3 >/dev/null || { echo "[WARNING] python3 required."; exit 1; }
command -v iperf3 >/dev/null || { echo "[WARNING] iperf3 required."; exit 1; }
command -v jq >/dev/null || { echo "[WARNING] jq required."; exit 1; }
command -v awk >/dev/null || { echo "[WARNING] awk required."; exit 1; }

[[ -f "$AGENT_PY" ]] || { echo "[WARNING] agent not found: $AGENT_PY"; exit 1; }

if [[ -z "$TARGET" ]]; then
  echo "[ERROR] -t: define <host>."; usage; exit 1
fi

if [[ -z "$BIND_IP" ]]; then
    BIND_IP=$(ip -4 addr show dev "$IFACE" \
        | awk '/inet / {print $2}' \
        | cut -d/ -f1 \
        | head -n 1)
fi

# outfile
mkdir -p "$(dirname "$OUT")"

if [[ -f "$OUT" ]]; then
  mv "$OUT" "$OUT.$(date +%s).bak"
fi

# start agent
AGENT_ERR="/tmp/netdiag_agent_stderr.log"
echo "[INFO] start agent: $AGENT_PY (iface=$IFACE, out=$OUT)"
export NETDIAG_IFACE="$IFACE"
export NETDIAG_OUTPUT_PATH="$OUT"

python3 "$AGENT_PY" > /dev/null 2>"$AGENT_ERR" &
AGENT_PID=$!
echo "[INFO] agent pid: $AGENT_PID"

#
cleanup() {
  echo "[CLEANUP] Cleanup after interrupt …"
  stop_agent
}
trap cleanup EXIT INT TERM

# start iperf3 load
IPERF_CMD=(iperf3 -c "$TARGET" -B "$BIND_IP" -p "$PORT" -t "$DURATION" -u -b "$BANDWIDTH")
echo "[INFO] iperf3 cmd: ${IPERF_CMD[*]}"
"${IPERF_CMD[@]}"

# stop agent
stop_agent(){
    if ps -p "$AGENT_PID" >/dev/null 2>&1; then
    echo "[INFO] stop agent …"
    kill -TERM "$AGENT_PID" 2>/dev/null || true
    for i in {1..5}; do
        ps -p "$AGENT_PID" >/dev/null 2>&1 || break
        sleep 1
    done
    ps -p "$AGENT_PID" >/dev/null 2>&1 && kill -KILL "$AGENT_PID" 2>/dev/null || true
    fi
}
stop_agent

#
echo
echo "=== Report aus NDJSON ($OUT) ==="
[[ -f "$OUT" ]] || { echo "[WARNING] output misses: $OUT"; exit 1; }

echo
echo "[DONE]"
echo "Agent stderr: $AGENT_ERR"
