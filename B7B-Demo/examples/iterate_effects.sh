#!/bin/bash
# iterate_effects.sh - Easy iteration through animation effects
#
# This script helps you preview all animation effects one by one.
# Terminal assumed: 80x25 clean state
#
# Usage:
#   ./iterate_effects.sh              # Show menu of options
#   ./iterate_effects.sh all          # Generate all effects to files
#   ./iterate_effects.sh play <name>  # Auto-play a specific effect

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEMO_DIR="$(dirname "$SCRIPT_DIR")"
OUTPUT_BASE="$DEMO_DIR/output"

# Available effects
EFFECTS=(
    "scroll"
    "phase"
    "amplitude"
    "morph-sin-tri"
    "morph-sin-cos"
    "resolution-up"
    "resolution-down"
    "resolution-bounce"
    "composite"
)

# Available renderers
RENDERERS=(
    "unicode"
    "cp437"
    "ascii"
)

show_menu() {
    clear
    echo "============================================"
    echo " B7B-Demo Animation Effect Iterator"
    echo "============================================"
    echo ""
    echo " EFFECTS:"
    for i in "${!EFFECTS[@]}"; do
        echo "   $((i+1)). ${EFFECTS[$i]}"
    done
    echo ""
    echo " RENDERERS: unicode (default), cp437, ascii"
    echo ""
    echo " COMMANDS:"
    echo "   play <effect> [renderer] [delay]"
    echo "   view <effect> [renderer]"
    echo "   gen <effect> [renderer]"
    echo "   all    - Generate all effects to files"
    echo "   q      - Quit"
    echo ""
}

play_effect() {
    local effect="${1:-scroll}"
    local renderer="${2:-unicode}"
    local delay="${3:-0.1}"

    echo "Playing $effect with $renderer renderer (delay: ${delay}s)"
    echo "Press Ctrl+C to stop"
    sleep 1

    python3 "$SCRIPT_DIR/animation_viewer.py" \
        --effect "$effect" \
        --renderer "$renderer" \
        --delay "$delay" \
        --loops 3
}

view_effect() {
    local effect="${1:-scroll}"
    local renderer="${2:-unicode}"

    echo "Interactive view of $effect (press Enter for next frame, q to quit)"
    sleep 1

    python3 "$SCRIPT_DIR/animation_viewer.py" \
        --effect "$effect" \
        --renderer "$renderer" \
        --interactive
}

generate_effect() {
    local effect="${1:-scroll}"
    local renderer="${2:-unicode}"
    local output_dir="$OUTPUT_BASE/${renderer}/${effect}"

    echo "Generating $effect with $renderer to $output_dir"
    python3 "$SCRIPT_DIR/animation_viewer.py" \
        --effect "$effect" \
        --renderer "$renderer" \
        --output "$output_dir" \
        --frames 32
}

generate_all() {
    echo "Generating all effects for all renderers..."
    echo ""

    for renderer in "${RENDERERS[@]}"; do
        echo "=== Renderer: $renderer ==="
        for effect in "${EFFECTS[@]}"; do
            local output_dir="$OUTPUT_BASE/${renderer}/${effect}"
            echo "  Generating $effect..."
            python3 "$SCRIPT_DIR/animation_viewer.py" \
                --effect "$effect" \
                --renderer "$renderer" \
                --output "$output_dir" \
                --frames 32 \
                > /dev/null
        done
        echo ""
    done

    echo "Done! Files are in $OUTPUT_BASE/"
    echo ""
    echo "To iterate through frames in a terminal:"
    echo "  for f in $OUTPUT_BASE/unicode/scroll/frame_*.txt; do clear; cat \"\$f\"; read; done"
}

# Main
case "$1" in
    all)
        generate_all
        ;;
    play)
        play_effect "$2" "$3" "$4"
        ;;
    view)
        view_effect "$2" "$3"
        ;;
    gen)
        generate_effect "$2" "$3"
        ;;
    ""|menu)
        show_menu
        echo -n "Command: "
        read -r cmd arg1 arg2 arg3
        case "$cmd" in
            [1-9])
                idx=$((cmd-1))
                if [ $idx -lt ${#EFFECTS[@]} ]; then
                    view_effect "${EFFECTS[$idx]}" "$arg1"
                fi
                ;;
            play) play_effect "$arg1" "$arg2" "$arg3" ;;
            view) view_effect "$arg1" "$arg2" ;;
            gen)  generate_effect "$arg1" "$arg2" ;;
            all)  generate_all ;;
            q|quit) exit 0 ;;
            *) echo "Unknown command: $cmd" ;;
        esac
        ;;
    *)
        echo "Usage: $0 [all|play|view|gen] [effect] [renderer] [delay]"
        echo ""
        echo "Examples:"
        echo "  $0                    # Show interactive menu"
        echo "  $0 all                # Generate all effects"
        echo "  $0 play scroll        # Auto-play scroll effect"
        echo "  $0 view phase unicode # Interactive phase effect"
        ;;
esac
