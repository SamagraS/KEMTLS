#!/bin/bash
# Setup Network Emulation using tc (Traffic Control) and Netem
# Requires root privileges (sudo)

show_help() {
    echo "Usage: ./setup_netem.sh [OPTIONS]"
    echo "Options:"
    echo "  --rtt MS       Round-Trip Time to simulate (default: 31)"
    echo "  --loss PERCENT Packet loss percentage to simulate (default: 0)"
    echo "  --reset        Remove all active tc rules on loopback"
    echo "  --show         Display current tc rules on loopback"
}

RTT=31
LOSS=0
RESET=0
SHOW=0

while [[ "$#" -gt 0 ]]; do
    case $1 in
        --rtt) RTT="$2"; shift ;;
        --loss) LOSS="$2"; shift ;;
        --reset) RESET=1 ;;
        --show) SHOW=1 ;;
        -h|--help) show_help; exit 0 ;;
        *) echo "Unknown parameter passed: $1"; exit 1 ;;
    esac
    shift
done

# Define interface
IFACE="lo"

if [ "$SHOW" -eq 1 ]; then
    echo "Current rules on $IFACE:"
    sudo tc qdisc show dev $IFACE
    exit 0
fi

if [ "$RESET" -eq 1 ]; then
    echo "Resetting tc rules on $IFACE..."
    sudo tc qdisc del dev $IFACE root 2>/dev/null
    echo "Done."
    exit 0
fi

# Reset existing first to avoid errors
sudo tc qdisc del dev $IFACE root 2>/dev/null

# Apply delay (half RTT for one-way since it applies both ways on loopback)
DELAY=$(echo "scale=2; $RTT / 2" | bc)

echo "Applying Netem settings to $IFACE:"
echo " - One-way Delay (ms): ${DELAY}ms (Total RTT: ${RTT}ms)"
echo " - Packet Loss (%): $LOSS%"

if [ "$LOSS" != "0" ] && [ "$LOSS" != "0.0" ]; then
    sudo tc qdisc add dev $IFACE root netem delay ${DELAY}ms loss ${LOSS}%
else
    sudo tc qdisc add dev $IFACE root netem delay ${DELAY}ms
fi

echo "Done. Verify with: ./setup_netem.sh --show"
