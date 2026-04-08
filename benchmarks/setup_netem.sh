#!/bin/bash
set -euo pipefail

IFACE="${IFACE:-eth0}"

usage() {
    echo "Usage: $0 apply <scenario>|clear|show"
    echo "Scenarios: LAN FAST_WAN TYPICAL_WAN SLOW_WAN LOSS_LOW LOSS_HIGH LOSS_SEVERE"
}

need_tc() {
    if ! command -v tc >/dev/null 2>&1; then
        echo "tc not found; netem unsupported on this host"
        exit 2
    fi
}

apply_scenario() {
    local scenario="$1"
    sudo tc qdisc del dev "$IFACE" root 2>/dev/null || true

    case "$scenario" in
        LAN)
            sudo tc qdisc add dev "$IFACE" root handle 1: htb default 10
            sudo tc class add dev "$IFACE" parent 1: classid 1:10 htb rate 1000mbit
            sudo tc qdisc add dev "$IFACE" parent 1:10 handle 10: netem delay 0ms
            ;;
        FAST_WAN)
            sudo tc qdisc add dev "$IFACE" root handle 1: htb default 10
            sudo tc class add dev "$IFACE" parent 1: classid 1:10 htb rate 100mbit
            sudo tc qdisc add dev "$IFACE" parent 1:10 handle 10: netem delay 10ms
            ;;
        TYPICAL_WAN)
            sudo tc qdisc add dev "$IFACE" root handle 1: htb default 10
            sudo tc class add dev "$IFACE" parent 1: classid 1:10 htb rate 20mbit
            sudo tc qdisc add dev "$IFACE" parent 1:10 handle 10: netem delay 40ms
            ;;
        SLOW_WAN)
            sudo tc qdisc add dev "$IFACE" root handle 1: htb default 10
            sudo tc class add dev "$IFACE" parent 1: classid 1:10 htb rate 5mbit
            sudo tc qdisc add dev "$IFACE" parent 1:10 handle 10: netem delay 100ms
            ;;
        LOSS_LOW)
            sudo tc qdisc add dev "$IFACE" root handle 1: htb default 10
            sudo tc class add dev "$IFACE" parent 1: classid 1:10 htb rate 50mbit
            sudo tc qdisc add dev "$IFACE" parent 1:10 handle 10: netem delay 15ms loss gemodel 1% 20% 0% 0%
            ;;
        LOSS_HIGH)
            sudo tc qdisc add dev "$IFACE" root handle 1: htb default 10
            sudo tc class add dev "$IFACE" parent 1: classid 1:10 htb rate 10mbit
            sudo tc qdisc add dev "$IFACE" parent 1:10 handle 10: netem delay 25ms loss gemodel 3% 20% 0% 0%
            ;;
        LOSS_SEVERE)
            sudo tc qdisc add dev "$IFACE" root handle 1: htb default 10
            sudo tc class add dev "$IFACE" parent 1: classid 1:10 htb rate 5mbit
            sudo tc qdisc add dev "$IFACE" parent 1:10 handle 10: netem delay 40ms loss gemodel 5% 20% 0% 0%
            ;;
        *)
            echo "Unknown scenario: $scenario"
            usage
            exit 1
            ;;
    esac
}

cmd="${1:-}"
arg="${2:-}"

case "$cmd" in
    apply)
        need_tc
        if [ -z "$arg" ]; then
            usage
            exit 1
        fi
        apply_scenario "$arg"
        echo "[*] Applied netem scenario $arg on $IFACE"
        ;;
    clear)
        need_tc
        sudo tc qdisc del dev "$IFACE" root 2>/dev/null || true
        echo "[*] Cleared netem rules on $IFACE"
        ;;
    show)
        need_tc
        sudo tc qdisc show dev "$IFACE"
        ;;
    *)
        usage
        exit 1
        ;;
esac
