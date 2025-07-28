#!/bin/zsh

# Check if we're in the right directory
if [ ! -d "Processing" ]; then
    echo "Error: This script must be run from the umfeld-examples-fork directory"
    echo "Current directory: $(pwd)"
    exit 1
fi

# Get the number of processor cores
NPROC=$(nproc)

# Store the original working directory
ORIGINAL_DIR=$(pwd)

# Check if test properties file exists and load it
TEST_PROPS_FILE="$ORIGINAL_DIR/test_props.json"
if [ -f "$TEST_PROPS_FILE" ]; then
    echo "Loading test properties from: $TEST_PROPS_FILE"
else
    echo "Warning: Test properties file not found: $TEST_PROPS_FILE"
fi

# Check if a specific example name is provided
SPECIFIC_EXAMPLE=""
if [ $# -eq 1 ]; then
    SPECIFIC_EXAMPLE="$1"
    echo "Running specific example: $SPECIFIC_EXAMPLE"
    echo "========================================"
fi

# Find all application.cpp files in the Processing examples directory
if [ -n "$SPECIFIC_EXAMPLE" ]; then
    PROJECT_PATHS=($(find Processing -mindepth 2 -type f -name "application.cpp" | sed 's|/application.cpp||' | grep -E "/${SPECIFIC_EXAMPLE}$"))
    if [ ${#PROJECT_PATHS[@]} -eq 0 ]; then
        echo "Error: Example '$SPECIFIC_EXAMPLE' not found"
        echo "Available examples:"
        find Processing -mindepth 2 -type f -name "application.cpp" | sed 's|/application.cpp||' | sed 's|.*/||' | sort | uniq
        exit 1
    fi
else
    PROJECT_PATHS=($(find Processing -mindepth 2 -type f -name "application.cpp" | sed 's|/application.cpp||'))
fi

# Initialize counters and arrays
found_count=0
not_found_count=0
total_projects=0

# Array to store not found projects
declare -a not_found_projects

# Function to read JSON value using python
# @brief Reads test properties from JSON file for a specific project
# @param project_name The name of the project to look up
# @param json_file Path to the JSON configuration file
# @return Prints "input_type:input_data" if found, exits with error code 1 if not found
get_json_value() {
    local project_name="$1"
    local json_file="$2"
    
    if [ ! -f "$json_file" ]; then
        echo "DEBUG: JSON file does not exist: $json_file" >&2
        return 1
    fi
    
    python3 -c "
import json
import sys

try:
    with open('$json_file', 'r') as f:
        data = json.load(f)
    
    project_name = '$project_name'
    if project_name in data:
        result = data[project_name]
        if isinstance(result, list) and len(result) >= 2:
            # Check if there's a third element (press option)
            if len(result) >= 3 and result[2] == 'press':
                print(f'{result[0]}:{result[1]}:press')
            else:
                print(f'{result[0]}:{result[1]}')
            sys.exit(0)
    sys.exit(1)
except Exception as e:
    print(f'DEBUG: Exception occurred: {e}', file=sys.stderr)
    sys.exit(1)
"
}

# Function to generate deterministic random values for consistent movement across applications
# @brief Generates a deterministic seed based on project name for consistent randomization
# @param project_name The name of the project
# @return Prints a numeric seed value
generate_movement_seed() {
    local project_name="$1"
    echo "$project_name" | md5sum | cut -d' ' -f1 | tr -d 'a-f' | head -c 8
}

# Function to simulate keyboard input using xdotool
# @brief Simulates keyboard input in the target window using xdotool
# @param window_id The X11 window identifier for the target window
# @param text_to_type The text string to be typed into the window
# @return 0 on success, 1 on failure
simulate_keyboard_input() {
    local window_id="$1"
    local text_to_type="$2"
    
    if [ -z "$window_id" ] || [ -z "$text_to_type" ]; then
        echo "Error: Missing window_id or text_to_type"
        return 1
    fi
    
    echo "Simulating keyboard input: '$text_to_type'"
    
    # Focus the window first
    xdotool windowfocus "$window_id" 2>/dev/null || return 1
    sleep 0.5
    
    # Type the text with a small delay between characters for realism
    xdotool type --delay 100 "$text_to_type" 2>/dev/null || return 1
    
    return 0
}

# Function to simulate mouse movement using xdotool
# @brief Simulates mouse movement patterns within a specified window with consistent behavior across apps
# @param window_id The X11 window identifier for the target window
# @param movement_type Type of movement: "random", "horizontal", "diagonal"
# @param project_name Name of the project (used for deterministic randomization)
# @return 0 on success, 1 on failure
simulate_mouse_movement() {
    local window_id="$1"
    local movement_type="$2"
    local project_name="$3"
    local drag_mode="$4"  # New parameter for drag operations
    
    if [ -z "$window_id" ] || [ -z "$movement_type" ] || [ -z "$project_name" ]; then
        echo "Error: Missing required parameters for mouse simulation"
        return 1
    fi
    
    local is_drag=false
    if [ "$drag_mode" = "press" ]; then
        is_drag=true
        echo "🖱️ DRAG MODE: Simulating mouse drag operations"
    fi
    
    echo "Simulating mouse movement: $movement_type $([ "$is_drag" = true ] && echo "with dragging" || echo "")"
    
    # Get window geometry
    local window_info=$(xwininfo -id "$window_id" 2>/dev/null)
    if [ $? -ne 0 ]; then
        echo "Error: Could not get window information"
        return 1
    fi
    
    local win_x=$(echo "$window_info" | grep "Absolute upper-left X:" | awk '{print $4}')
    local win_y=$(echo "$window_info" | grep "Absolute upper-left Y:" | awk '{print $4}')
    local win_width=$(echo "$window_info" | grep "Width:" | awk '{print $2}')
    local win_height=$(echo "$window_info" | grep "Height:" | awk '{print $2}')
    
    # Add some margin to avoid window borders
    local margin=20
    local usable_x=$((win_x + margin))
    local usable_y=$((win_y + margin))
    local usable_width=$((win_width - 2 * margin))
    local usable_height=$((win_height - 2 * margin))
    
    # Detect app type to handle coordinate system differences
    local is_processing=false
    if [[ "$project_name" =~ ^[A-Z] ]] || echo "$window_info" | grep -qi "processing"; then
        is_processing=true
        echo "DEBUG: Detected Processing app - using inverted Y coordinates"
    else
        echo "DEBUG: Detected Umfeld app - using standard coordinates"
    fi
    
    # Function to convert Y coordinate for Processing apps (invert Y axis)
    convert_y_coordinate() {
        local y_input="$1"
        if [ "$is_processing" = true ]; then
            # For Processing: invert Y within the usable area
            local relative_y=$((y_input - usable_y))
            local inverted_relative_y=$((usable_height - relative_y))
            echo $((usable_y + inverted_relative_y))
        else
            # For Umfeld: use Y as-is
            echo "$y_input"
        fi
    }
    
    # Generate deterministic seed for movement
    local seed=$(generate_movement_seed "$project_name")
    local seed_num=$((0x$seed % 1000))
    
    echo "DEBUG: Window geometry - x:$win_x y:$win_y w:$win_width h:$win_height"
    echo "DEBUG: Usable area - x:$usable_x y:$usable_y w:$usable_width h:$usable_height"
    echo "DEBUG: Movement seed: $seed_num"
    
    # Focus the window
    xdotool windowfocus "$window_id" 2>/dev/null
    sleep 0.5
    
    # Move mouse to safe starting position outside the window (left side)
    local safe_start_x=$((win_x - 50))
    local safe_start_y=$((win_y + win_height / 2))
    echo "DEBUG: Moving mouse to safe starting position: ($safe_start_x, $safe_start_y)"
    xdotool mousemove "$safe_start_x" "$safe_start_y" 2>/dev/null
    sleep 0.3
    
    # Smoothly enter the window from the left side
    local entry_x=$((usable_x + 10))
    local entry_y_base=$((usable_y + usable_height / 2))
    local entry_y=$(convert_y_coordinate "$entry_y_base")
    echo "DEBUG: Smoothly entering window to: ($entry_x, $entry_y)"
    
    local entry_steps=15
    local entry_dx=$(( (entry_x - safe_start_x) / entry_steps ))
    local entry_dy=$(( (entry_y - safe_start_y) / entry_steps ))
    
    for step in $(seq 1 $entry_steps); do
        local intermediate_x=$((safe_start_x + entry_dx * step))
        local intermediate_y=$((safe_start_y + entry_dy * step))
        xdotool mousemove "$intermediate_x" "$intermediate_y" 2>/dev/null
        sleep 0.02
    done
    
    sleep 0.2
    
    case "$movement_type" in
        "random")
            # Generate multiple random movements over 4 seconds with smooth transitions
            local movements=8
            local current_x=$entry_x
            local current_y=$entry_y
            
            if [ "$is_drag" = true ]; then
                echo "DEBUG: Multiple drag segments mode - creating $movements random drag operations"
                
                for i in $(seq 1 $movements); do
                    # Generate consistent random positions for both apps (base coordinates)
                    local rand_x_offset=$(( (seed_num * i * 73) % usable_width ))
                    local rand_y_offset=$(( (seed_num * i * 137) % usable_height ))
                    
                    # Calculate base target position
                    local target_x=$((usable_x + rand_x_offset))
                    local target_y_base=$((usable_y + rand_y_offset))
                    
                    # Convert Y coordinate based on app type
                    local target_y=$(convert_y_coordinate "$target_y_base")
                    
                    # Decide drag characteristics for this segment
                    local drag_length=$(( (seed_num * i * 29) % 3 ))  # 0=short, 1=medium, 2=long
                    local drag_speed=$(( (seed_num * i * 41) % 3 ))   # 0=fast, 1=medium, 2=slow
                    
                    case $drag_length in
                        0) 
                            local drag_name="SHORT"
                            local steps=8
                            ;;
                        1) 
                            local drag_name="MEDIUM"
                            local steps=15
                            ;;
                        2) 
                            local drag_name="LONG"
                            local steps=25
                            ;;
                    esac
                    
                    case $drag_speed in
                        0) 
                            local speed_name="FAST"
                            local step_delay=0.01
                            ;;
                        1) 
                            local speed_name="MEDIUM"
                            local step_delay=0.03
                            ;;
                        2) 
                            local speed_name="SLOW"
                            local step_delay=0.06
                            ;;
                    esac
                    
                    echo "DEBUG: Drag segment $i: $drag_name $speed_name drag to ($target_x, $target_y) [base_y: $target_y_base]"
                    
                    # Start this drag segment
                    echo "DEBUG: Starting drag segment $i at ($current_x, $current_y)"
                    xdotool mousedown 1 2>/dev/null
                    sleep 0.05
                    
                    # Calculate smooth movement steps for this drag
                    local dx=$(( (target_x - current_x) / steps ))
                    local dy=$(( (target_y - current_y) / steps ))
                    
                    # Perform the drag movement
                    for step in $(seq 1 $steps); do
                        local intermediate_x=$((current_x + dx * step))
                        local intermediate_y=$((current_y + dy * step))
                        xdotool mousemove "$intermediate_x" "$intermediate_y" 2>/dev/null
                        sleep $step_delay
                    done
                    
                    # End this drag segment
                    echo "DEBUG: Ending drag segment $i at ($target_x, $target_y)"
                    xdotool mouseup 1 2>/dev/null
                    
                    # Update current position
                    current_x=$target_x
                    current_y=$target_y
                    
                    # Random pause between drag segments
                    local pause_var=$(( (seed_num * i * 19) % 4 ))
                    case $pause_var in
                        0) sleep 0.1 ;;  # Very short pause
                        1) sleep 0.2 ;;  # Short pause
                        2) sleep 0.4 ;;  # Medium pause
                        3) sleep 0.6 ;;  # Long pause
                    esac
                done
            else
                # Normal movement mode (no dragging)
                for i in $(seq 1 $movements); do
                    # Generate consistent random positions for both apps (base coordinates)
                    local rand_x_offset=$(( (seed_num * i * 73) % usable_width ))
                    local rand_y_offset=$(( (seed_num * i * 137) % usable_height ))
                    
                    # Calculate base target position
                    local target_x=$((usable_x + rand_x_offset))
                    local target_y_base=$((usable_y + rand_y_offset))
                    
                    # Convert Y coordinate based on app type
                    local target_y=$(convert_y_coordinate "$target_y_base")
                    
                    echo "DEBUG: Moving to position $i: ($target_x, $target_y) [base_y: $target_y_base]"
                    
                    # Calculate smooth movement steps
                    local steps=20
                    local dx=$(( (target_x - current_x) / steps ))
                    local dy=$(( (target_y - current_y) / steps ))
                    
                    # Perform smooth movement
                    for step in $(seq 1 $steps); do
                        local intermediate_x=$((current_x + dx * step))
                        local intermediate_y=$((current_y + dy * step))
                        xdotool mousemove "$intermediate_x" "$intermediate_y" 2>/dev/null
                        sleep 0.025
                    done
                    
                    # Update current position
                    current_x=$target_x
                    current_y=$target_y
                    
                    # Pause at each position
                    sleep 0.2
                done
            fi
            ;;
            
        "horizontal")
            # Move from left to right and back with smooth motion
            local start_x=$usable_x
            local end_x=$((usable_x + usable_width))
            local mid_y_base=$((usable_y + usable_height / 2))
            local mid_y=$(convert_y_coordinate "$mid_y_base")
            
            echo "DEBUG: Smooth horizontal $([ "$is_drag" = true ] && echo "drag segments" || echo "movement") from $start_x to $end_x at y=$mid_y [base_y: $mid_y_base]"
            
            # Start from entry point and move to actual start position
            local current_x=$entry_x
            local current_y=$entry_y
            
            # Smooth move to horizontal start position
            local steps=15
            local dx=$(( (start_x - current_x) / steps ))
            local dy=$(( (mid_y - current_y) / steps ))
            
            for step in $(seq 1 $steps); do
                local intermediate_x=$((current_x + dx * step))
                local intermediate_y=$((current_y + dy * step))
                xdotool mousemove "$intermediate_x" "$intermediate_y" 2>/dev/null
                sleep 0.03
            done
            
            sleep 0.3
            current_x=$start_x
            current_y=$mid_y
            
            if [ "$is_drag" = true ]; then
                echo "DEBUG: Multiple horizontal drag segments mode"
                
                # Create 4-6 horizontal drag segments
                local drag_segments=$(( 4 + (seed_num % 3) ))  # 4, 5, or 6 segments
                local segment_width=$((usable_width / drag_segments))
                
                for seg in $(seq 1 $drag_segments); do
                    # Calculate segment target
                    local segment_target_x=$((start_x + segment_width * seg))
                    if [ $segment_target_x -gt $end_x ]; then
                        segment_target_x=$end_x
                    fi
                    
                    # Decide drag characteristics for this segment
                    local drag_length=$(( (seed_num * seg * 31) % 3 ))  # 0=short, 1=medium, 2=long
                    local drag_speed=$(( (seed_num * seg * 43) % 3 ))   # 0=fast, 1=medium, 2=slow
                    
                    case $drag_length in
                        0) 
                            local drag_name="SHORT"
                            local steps=6
                            ;;
                        1) 
                            local drag_name="MEDIUM"
                            local steps=12
                            ;;
                        2) 
                            local drag_name="LONG"
                            local steps=20
                            ;;
                    esac
                    
                    case $drag_speed in
                        0) 
                            local speed_name="FAST"
                            local step_delay=0.02
                            ;;
                        1) 
                            local speed_name="MEDIUM"
                            local step_delay=0.04
                            ;;
                        2) 
                            local speed_name="SLOW"
                            local step_delay=0.07
                            ;;
                    esac
                    
                    echo "DEBUG: Horizontal drag segment $seg: $drag_name $speed_name drag from $current_x to $segment_target_x"
                    
                    # Start this drag segment
                    xdotool mousedown 1 2>/dev/null
                    sleep 0.05
                    
                    # Calculate movement for this segment
                    local dx=$(( (segment_target_x - current_x) / steps ))
                    
                    # Perform the horizontal drag
                    for step in $(seq 1 $steps); do
                        local intermediate_x=$((current_x + dx * step))
                        xdotool mousemove "$intermediate_x" "$mid_y" 2>/dev/null
                        sleep $step_delay
                    done
                    
                    # End this drag segment
                    xdotool mouseup 1 2>/dev/null
                    
                    # Update current position
                    current_x=$segment_target_x
                    
                    # Random pause between segments
                    local pause_var=$(( (seed_num * seg * 23) % 4 ))
                    case $pause_var in
                        0) sleep 0.1 ;;  # Very short pause
                        1) sleep 0.2 ;;  # Short pause
                        2) sleep 0.3 ;;  # Medium pause
                        3) sleep 0.5 ;;  # Long pause
                    esac
                done
            else
                # Normal movement mode
                steps=30
                dx=$(( (end_x - start_x) / steps ))
                for step in $(seq 1 $steps); do
                    local intermediate_x=$((start_x + dx * step))
                    xdotool mousemove "$intermediate_x" "$mid_y" 2>/dev/null
                    sleep 0.05
                done
                
                sleep 0.3
                
                # Move back to start
                for step in $(seq 1 $steps); do
                    local intermediate_x=$((end_x - dx * step))
                    xdotool mousemove "$intermediate_x" "$mid_y" 2>/dev/null
                    sleep 0.05
                done
                
                sleep 0.3
                
                # Final move to a position based on seed
                local final_x=$(( (seed_num * 89) % usable_width + usable_x ))
                steps=15
                dx=$(( (final_x - start_x) / steps ))
                for step in $(seq 1 $steps); do
                    local intermediate_x=$((start_x + dx * step))
                    xdotool mousemove "$intermediate_x" "$mid_y" 2>/dev/null
                    sleep 0.03
                done
            fi
            ;;
            
        "diagonal")
            # Move diagonally across the window with smooth transitions
            local start_corner=$((seed_num % 4))
            
            echo "DEBUG: Smooth diagonal movement starting from corner $start_corner"
            
            # Start from entry position
            local current_x=$entry_x
            local current_y=$entry_y
            
            for i in $(seq 0 3); do
                local pos_index=$(( (start_corner + i) % 4 ))
                
                # Calculate base corner positions (same for both apps)
                local target_x_base target_y_base
                case $pos_index in
                    0) target_x_base=$usable_x; target_y_base=$usable_y ;;
                    1) target_x_base=$((usable_x + usable_width)); target_y_base=$usable_y ;;
                    2) target_x_base=$((usable_x + usable_width)); target_y_base=$((usable_y + usable_height)) ;;
                    3) target_x_base=$usable_x; target_y_base=$((usable_y + usable_height)) ;;
                esac
                
                # Convert coordinates based on app type
                local target_x=$target_x_base
                local target_y=$(convert_y_coordinate "$target_y_base")
                
                echo "DEBUG: Smoothly moving to corner $pos_index: ($target_x, $target_y) [base_y: $target_y_base]"
                
                # Calculate smooth diagonal movement
                local steps=25
                local dx=$(( (target_x - current_x) / steps ))
                local dy=$(( (target_y - current_y) / steps ))
                
                # Perform smooth diagonal movement
                for step in $(seq 1 $steps); do
                    local intermediate_x=$((current_x + dx * step))
                    local intermediate_y=$((current_y + dy * step))
                    xdotool mousemove "$intermediate_x" "$intermediate_y" 2>/dev/null
                    sleep 0.04
                done
                
                # Update current position
                current_x=$target_x
                current_y=$target_y
                
                # Pause at corner
                sleep 0.2
            done
            ;;
            
        *)
            echo "Warning: Unknown movement type: $movement_type"
            return 1
            ;;
    esac
    
    return 0
}

# Function to record video of a window using ffmpeg
# @brief Records video of a specified window for a given duration
# @param window_id The X11 window identifier for the target window
# @param output_file Path to the output video file
# @param duration Duration of recording in seconds (default: 4)
# @param label Text label to overlay on the video
# @return 0 on success, 1 on failure
record_window_video() {
    local window_id="$1"
    local output_file="$2"
    local duration="${3:-4}"
    local label="$4"
    
    if [ -z "$window_id" ] || [ -z "$output_file" ]; then
        echo "Error: Missing window_id or output_file for video recording"
        return 1
    fi
    
    echo "Recording video: $label for ${duration}s"
    
    # Get window geometry
    local window_info=$(xwininfo -id "$window_id" 2>/dev/null)
    if [ $? -ne 0 ]; then
        echo "Error: Could not get window information for recording"
        return 1
    fi
    
    local win_x=$(echo "$window_info" | grep "Absolute upper-left X:" | awk '{print $4}')
    local win_y=$(echo "$window_info" | grep "Absolute upper-left Y:" | awk '{print $4}')
    local win_width=$(echo "$window_info" | grep "Width:" | awk '{print $2}')
    local win_height=$(echo "$window_info" | grep "Height:" | awk '{print $2}')
    
    # Add border and text area
    local border_width=10
    local text_padding=30
    local final_width=$((win_width + 2 * border_width))
    local final_height=$((win_height + 2 * border_width + text_padding))
    
    echo "DEBUG: Recording area - x:$win_x y:$win_y w:$win_width h:$win_height"
    
    # Record the window with ffmpeg
    ffmpeg -y -f x11grab \
        -video_size "${win_width}x${win_height}" \
        -framerate 30 \
        -i "${DISPLAY}+${win_x},${win_y}" \
        -t "$duration" \
        -c:v libx264 \
        -preset fast \
        -crf 23 \
        -pix_fmt yuv420p \
        -vf "pad=w=${final_width}:h=${final_height}:x=${border_width}:y=${border_width}:color=rgb(70,130,180),drawtext=text='${label}':fontcolor=white:fontsize=20:x=15:y=${final_height}-25" \
        "$output_file" >/dev/null 2>&1
    
    if [ $? -eq 0 ]; then
        echo "✓ Video recorded successfully: $output_file"
        return 0
    else
        echo "✗ Failed to record video"
        return 1
    fi
}

# Function to capture a window by name and add text label with blue border
capture_and_label_window() {
    local window_name="$1"
    local label="$2"
    local output_file="$3"
    local temp_dir="$4"
    
    echo "Attempting to capture window: $window_name"
    
    # Wait a bit for window to be ready
    sleep 2
    
    # Try to find and capture the window using xwininfo and import
    local window_id=$(xwininfo -name "$window_name" 2>/dev/null | grep "Window id:" | cut -d' ' -f4)
    
    if [ -z "$window_id" ]; then
        # Alternative: try with partial name match
        window_id=$(xwininfo -tree -root | grep -i "$window_name" | head -n1 | awk '{print $1}')
    fi
    
    if [ -n "$window_id" ]; then
        # Capture the window
        local temp_capture="$temp_dir/temp_capture_${label}.png"
        echo "DEBUG: Capturing window ID: $window_id"
        
        if import -window "$window_id" "$temp_capture" 2>/dev/null; then
            echo "DEBUG: Window captured successfully to: $temp_capture"
            
            if [ -f "$temp_capture" ]; then
                # Add border and text using ImageMagick
                local border_width=10
                local text_padding=30
                
                if convert "$temp_capture" \
                    -bordercolor "rgb(70,130,180)" \
                    -border ${border_width}x${border_width} \
                    -background "rgb(70,130,180)" \
                    -splice 0x${text_padding} \
                    -font DejaVu-Sans \
                    -pointsize 20 \
                    -fill white \
                    -gravity Southwest \
                    -annotate +15+5 "$label" \
                    "$output_file" 2>/dev/null; then
                    
                    rm -f "$temp_capture"
                    echo "Successfully captured and labeled: $label"
                    return 0
                else
                    # Fallback: just copy the original
                    cp "$temp_capture" "$output_file"
                    rm -f "$temp_capture"
                    echo "Captured without modifications: $label"
                    return 0
                fi
            fi
        fi
    fi
    
    echo "Failed to capture window: $window_name"
    return 1
}

# Function to wait for a window to appear
wait_for_window() {
    local window_name="$1"
    local timeout=10
    local count=0
    
    while [ $count -lt $timeout ]; do
        if xwininfo -name "$window_name" >/dev/null 2>&1; then
            return 0
        fi
        sleep 1
        count=$((count + 1))
    done
    return 1
}

# Function for fuzzy string matching using awk (no external dependencies)
fuzzy_match() {
    local search_term="$1"
    local search_dir="$2"
    
    if [ ! -d "$search_dir" ]; then
        return 1
    fi
    
    find "$search_dir" -maxdepth 1 -type d -exec basename {} \; | tail -n +2 | \
    awk -v search="$search_term" '
    function levenshtein(s1, s2) {
        n = length(s1)
        m = length(s2)
        
        for (i = 0; i <= n; i++) d[i,0] = i
        for (j = 0; j <= m; j++) d[0,j] = j
        
        for (i = 1; i <= n; i++) {
            for (j = 1; j <= m; j++) {
                cost = (substr(s1,i,1) == substr(s2,j,1)) ? 0 : 1
                d[i,j] = d[i-1,j] + 1
                if (d[i,j-1] + 1 < d[i,j]) d[i,j] = d[i,j-1] + 1
                if (d[i-1,j-1] + cost < d[i,j]) d[i,j] = d[i-1,j-1] + cost
            }
        }
        return d[n,m]
    }
    
    function similarity_score(s1, s2) {
        s1_lower = tolower(s1)
        s2_lower = tolower(s2)
        
        if (s1_lower == s2_lower) return 1000
        if (index(s1_lower, s2_lower) > 0 || index(s2_lower, s1_lower) > 0) return 500
        
        max_len = (length(s1) > length(s2)) ? length(s1) : length(s2)
        if (max_len == 0) return 0
        
        edit_dist = levenshtein(s1_lower, s2_lower)
        return int(100 * (1 - edit_dist / max_len))
    }
    
    {
        score = similarity_score($0, search)
        if (score > best_score) {
            best_score = score
            best_match = $0
        }
    }
    
    END {
        if (best_score >= 70) {
            print best_match
        }
    }'
}

# Main processing loop
for project_path in $PROJECT_PATHS[@]
do
    total_projects=$((total_projects + 1))
    
    echo "DEBUG: Processing path: '$project_path'"
    
    # Convert to absolute path
    project_abs_path="$ORIGINAL_DIR/$project_path"
    
    # Get the project name from the path
    project_name=$(basename "$project_path")
    echo "DEBUG: Project name: '$project_name'"
    
    # Find matching Processing example
    processing_project_search_name=$(echo "$project_name" | tr '_' ' ' | sed 's/[^a-zA-Z0-9 ]//g')
    processing_project_base_path="/opt/processing/modes/java/examples"
    
    # Get category and subcategory from umfeld path
    processing_category_path=$(echo $project_path | sed -E 's|^Processing/([^/]+)/.*$|\1|')
    processing_subcategory_path=$(echo $project_path | sed -E 's|^Processing/[^/]+/([^/]+)/.*$|\1|')
    
    # Build the expected Processing path structure
    processing_search_base="$processing_project_base_path/$processing_category_path"
    
    # First try direct match in the full Processing examples directory
    processing_project_dir=$(find "$processing_project_base_path" -type d -iname "$processing_project_search_name" 2>/dev/null | head -n 1)
    
    # If not found, try with original name (with underscores converted to no separator)
    if [ ! -d "$processing_project_dir" ]; then
        processing_compact_name=$(echo "$project_name" | tr -d '_')
        processing_project_dir=$(find "$processing_project_base_path" -type d -iname "$processing_compact_name" 2>/dev/null | head -n 1)
    fi
    
    # If still not found, try exact matches in the specific category/subcategory ONLY
    if [ ! -d "$processing_project_dir" ]; then
        processing_subcategory_dir="$processing_search_base/$processing_subcategory_path"
        
        if [ -d "$processing_subcategory_dir" ]; then
            echo "Searching in: $processing_category_path/$processing_subcategory_path"
            
            # Try exact match in subcategory
            processing_project_dir=$(find "$processing_subcategory_dir" -maxdepth 1 -type d -iname "$processing_project_search_name" 2>/dev/null | head -n 1)
            
            # Try compact name in subcategory
            if [ ! -d "$processing_project_dir" ]; then
                processing_compact_name=$(echo "$project_name" | tr -d '_')
                processing_project_dir=$(find "$processing_subcategory_dir" -maxdepth 1 -type d -iname "$processing_compact_name" 2>/dev/null | head -n 1)
            fi
            
            # Only use fuzzy matching as last resort and with higher threshold
            if [ ! -d "$processing_project_dir" ]; then
                fuzzy_match_result=$(fuzzy_match "$processing_project_search_name" "$processing_subcategory_dir")
                
                if [ -n "$fuzzy_match_result" ]; then
                    core_name=$(echo "$project_name" | sed 's/^embedding_//g' | sed 's/_[0-9]*$//g' | tr '_' ' ')
                    if [[ "$fuzzy_match_result" =~ $(echo "$core_name" | tr '[:upper:]' '[:lower:]') ]]; then
                        processing_project_dir="$processing_subcategory_dir/$fuzzy_match_result"
                        echo "DEBUG: Fuzzy match accepted: $project_name -> $fuzzy_match_result"
                    else
                        echo "DEBUG: Fuzzy match rejected: $project_name -> $fuzzy_match_result (core name mismatch)"
                    fi
                fi
            fi
        fi
    fi
    
    # Print result in a compact format with colors
    if [ -d "$processing_project_dir" ]; then
        echo -e "\033[32m✓\033[0m $project_name → $(basename "$processing_project_dir")"
        found_count=$((found_count + 1))
    else
        echo -e "\033[31m✗\033[0m $project_name → NOT FOUND"
        not_found_count=$((not_found_count + 1))
        not_found_projects+=("$project_path")
    fi
    
    # Build and run Umfeld example
    echo "Building Umfeld: $project_name..."
    
    # Check if the project directory exists first
    if [ ! -d "$project_abs_path" ]; then
        echo "Project directory does not exist: $project_abs_path"
        echo "----------------------------------------"
        continue
    fi
    
    # First check if the project directory and files exist
    if [ ! -f "$project_abs_path/CMakeLists.txt" ]; then
        echo "No CMakeLists.txt found in $project_abs_path"
        echo "----------------------------------------"
        continue
    fi
    
    # Build directly without complex subshell handling
    cd "$project_abs_path" || continue
    rm -rf build
    mkdir -p build
    cd build || continue
    
    cmake_success=false
    make_success=false
    
    # Test cmake
    if cmake .. >/dev/null 2>&1; then
        cmake_success=true
    fi
    
    # Test make only if cmake succeeded
    if [ "$cmake_success" = true ]; then
        if make -j$NPROC >/dev/null 2>&1; then
            make_success=true
        fi
    fi
    
    # Go back to original directory
    cd "$ORIGINAL_DIR" >/dev/null
    
    # Check if build was successful
    if [ "$cmake_success" = true ] && [ "$make_success" = true ] && [ -x "$project_abs_path/build/$project_name" ]; then
        echo "✓ BUILD SUCCESS: $project_name"
        
        # Skip if no matching Processing example found
        if [ ! -d "$processing_project_dir" ]; then
            echo "⏭️  SKIPPING: No matching Processing example found for $project_name"
            echo "----------------------------------------"
            continue
        fi
        
        # Check if this project has test properties defined
        local test_props=""
        if [ -f "$TEST_PROPS_FILE" ]; then
            echo "DEBUG: Looking for test properties for project: '$project_name'"
            test_props=$(get_json_value "$project_name" "$TEST_PROPS_FILE")
            echo "DEBUG: Test properties result: '$test_props'"
        fi
        
        if [ -n "$test_props" ]; then
            echo "Found test properties for $project_name: $test_props"
            
            # Parse test properties (format: "input_type:input_data" or "input_type:input_data:press")
            local input_type=$(echo "$test_props" | cut -d':' -f1)
            local input_data=$(echo "$test_props" | cut -d':' -f2)
            local press_option=$(echo "$test_props" | cut -d':' -f3)
            
            # Check if press option is specified
            local interaction_mode=""
            if [ "$press_option" = "press" ]; then
                interaction_mode=" with DRAG/PRESS"
            fi
            
            echo "📹 RECORDING MODE: $project_name with $input_type interaction$interaction_mode"
            
            # Create temporary directory for video processing
            temp_dir=$(mktemp -d)
            
            # Variables for recorded videos
            umfeld_video="$temp_dir/umfeld_video.mp4"
            processing_video="$temp_dir/processing_video.mp4"
            final_output="$project_abs_path/comparison_${project_name}.mp4"
            
            # Launch Processing example
            processing_sketch_parent_dir=$(dirname "$processing_project_dir")
            processing_sketch_name=$(basename "$processing_project_dir")
            
            echo "Launching Processing: $processing_sketch_name"
            (
                cd "$processing_sketch_parent_dir" && \
                processing-java --sketch="$processing_sketch_name" --run >/dev/null 2>&1
            ) &
            processing_pid=$!
            
            # Launch Umfeld example
            echo "Launching Umfeld: $project_name"
            (
                cd "$project_abs_path/build" && \
                ./"$project_name"
            ) &
            umfeld_pid=$!
            
            # Wait for windows to appear and position them
            sleep 3
            
            # Get Umfeld window position and size
            umfeld_window_id=$(xwininfo -name "$project_name" 2>/dev/null | grep "Window id:" | cut -d' ' -f4)
            if [ -n "$umfeld_window_id" ]; then
                # Get window geometry
                umfeld_geometry=$(xwininfo -id "$umfeld_window_id" 2>/dev/null)
                umfeld_x=$(echo "$umfeld_geometry" | grep "Absolute upper-left X:" | awk '{print $4}')
                umfeld_y=$(echo "$umfeld_geometry" | grep "Absolute upper-left Y:" | awk '{print $4}')
                umfeld_height=$(echo "$umfeld_geometry" | grep "Height:" | awk '{print $2}')
                
                # Calculate new position for Processing window (below Umfeld)
                processing_x=$umfeld_x
                processing_y=$((umfeld_y + umfeld_height + 30))
                
                # Wait for Processing window and position it
                sleep 2
                processing_window_id=$(xwininfo -name "$processing_sketch_name" 2>/dev/null | grep "Window id:" | cut -d' ' -f4)
                if [ -z "$processing_window_id" ]; then
                    processing_window_id=$(xwininfo -tree -root | grep -i "$processing_sketch_name" | head -n1 | awk '{print $1}')
                fi
                
                if [ -n "$processing_window_id" ]; then
                    xdotool windowmove "$processing_window_id" "$processing_x" "$processing_y" 2>/dev/null || \
                    wmctrl -i -r "$processing_window_id" -e "0,${processing_x},${processing_y},-1,-1" 2>/dev/null
                fi
            fi
            
            # Wait for windows to settle
            sleep 1
            
            # Record Umfeld application with interaction
            echo "Recording Umfeld application..."
            if [ -n "$umfeld_window_id" ]; then
                # Start recording in background
                record_window_video "$umfeld_window_id" "$umfeld_video" 4 "Umfeld" &
                record_umfeld_pid=$!
                
                # Wait a moment for recording to start
                sleep 0.5
                
                # Perform interaction based on input type
                case "$input_type" in
                    "keyboard")
                        simulate_keyboard_input "$umfeld_window_id" "$input_data"
                        ;;
                    "mouse")
                        simulate_mouse_movement "$umfeld_window_id" "$input_data" "$project_name" "$press_option"
                        ;;
                esac
                
                # Wait for recording to complete
                wait $record_umfeld_pid
            fi
            
            # Record Processing application with the same interaction
            echo "Recording Processing application..."
            if [ -n "$processing_window_id" ]; then
                # Start recording in background
                record_window_video "$processing_window_id" "$processing_video" 4 "Processing" &
                record_processing_pid=$!
                
                # Wait a moment for recording to start
                sleep 0.5
                
                # Perform the same interaction (deterministic for mouse, same text for keyboard)
                case "$input_type" in
                    "keyboard")
                        simulate_keyboard_input "$processing_window_id" "$input_data"
                        ;;
                    "mouse")
                        simulate_mouse_movement "$processing_window_id" "$input_data" "$project_name" "$press_option"
                        ;;
                esac
                
                # Wait for recording to complete
                wait $record_processing_pid
            fi
            
            # Create comparison video if we have both recordings
            if [ -f "$umfeld_video" ] && [ -f "$processing_video" ]; then
                echo "Creating comparison video..."
                
                echo "DEBUG: Checking input video files..."
                echo "DEBUG: Umfeld video exists: $([ -f "$umfeld_video" ] && echo "YES" || echo "NO")"
                echo "DEBUG: Processing video exists: $([ -f "$processing_video" ] && echo "YES" || echo "NO")"
                
                if ffmpeg -y -i "$umfeld_video" -i "$processing_video" \
                    -filter_complex "[0:v][1:v]vstack=inputs=2[v]" \
                    -map "[v]" -c:v libx264 -preset fast -crf 23 -pix_fmt yuv420p \
                    "$final_output" >/dev/null 2>&1; then
                    echo "✓ Comparison video saved: $final_output"
                else
                    echo "✗ Failed to create comparison video"
                    echo "DEBUG: Saving individual videos for inspection..."
                    cp "$umfeld_video" "$project_abs_path/debug_umfeld_${project_name}.mp4" 2>/dev/null || true
                    cp "$processing_video" "$project_abs_path/debug_processing_${project_name}.mp4" 2>/dev/null || true
                fi
            else
                echo "✗ Failed to record both applications"
            fi
            
            # Clean up temporary directory
            rm -rf "$temp_dir"
            
        else
            echo "📸 CAPTURE MODE: $project_name (no test properties defined)"
            
            # Original capture logic for projects without test properties
            echo "Launching applications for capture..."
            
            # Create temporary directory for image processing
            temp_dir=$(mktemp -d)
            
            # Variables for captured images
            umfeld_capture="$temp_dir/umfeld_capture.png"
            processing_capture="$temp_dir/processing_capture.png"
            final_output="$project_abs_path/comparison_${project_name}.png"
            
            # Launch Processing example
            processing_sketch_parent_dir=$(dirname "$processing_project_dir")
            processing_sketch_name=$(basename "$processing_project_dir")
            
            echo "Launching Processing: $processing_sketch_name"
            (
                cd "$processing_sketch_parent_dir" && \
                processing-java --sketch="$processing_sketch_name" --run >/dev/null 2>&1
            ) &
            processing_pid=$!
            
            # Launch Umfeld example
            echo "Launching Umfeld: $project_name"
            (
                cd "$project_abs_path/build" && \
                ./"$project_name"
            ) &
            umfeld_pid=$!
            
            # Wait for Umfeld window to appear first
            sleep 3
            
            # Get Umfeld window position and size
            umfeld_window_id=$(xwininfo -name "$project_name" 2>/dev/null | grep "Window id:" | cut -d' ' -f4)
            if [ -n "$umfeld_window_id" ]; then
                # Get window geometry
                umfeld_geometry=$(xwininfo -id "$umfeld_window_id" 2>/dev/null)
                umfeld_x=$(echo "$umfeld_geometry" | grep "Absolute upper-left X:" | awk '{print $4}')
                umfeld_y=$(echo "$umfeld_geometry" | grep "Absolute upper-left Y:" | awk '{print $4}')
                umfeld_height=$(echo "$umfeld_geometry" | grep "Height:" | awk '{print $2}')
                
                # Calculate new position for Processing window (below Umfeld)
                processing_x=$umfeld_x
                processing_y=$((umfeld_y + umfeld_height + 30))
                
                # Wait a bit more for Processing window to appear
                sleep 2
                
                # Find and move Processing window
                processing_window_id=$(xwininfo -name "$processing_sketch_name" 2>/dev/null | grep "Window id:" | cut -d' ' -f4)
                if [ -z "$processing_window_id" ]; then
                    processing_window_id=$(xwininfo -tree -root | grep -i "$processing_sketch_name" | head -n1 | awk '{print $1}')
                fi
                
                if [ -n "$processing_window_id" ]; then
                    xdotool windowmove "$processing_window_id" "$processing_x" "$processing_y" 2>/dev/null || \
                    wmctrl -i -r "$processing_window_id" -e "0,${processing_x},${processing_y},-1,-1" 2>/dev/null
                fi
            fi
            
            # Wait a bit more for windows to settle
            sleep 2
            
            # Capture windows
            captured_umfeld=false
            captured_processing=false
            
            # Try to capture Umfeld window
            if wait_for_window "$project_name"; then
                if capture_and_label_window "$project_name" "Umfeld" "$umfeld_capture" "$temp_dir"; then
                    captured_umfeld=true
                fi
            fi
            
            # Try to capture Processing window
            if wait_for_window "$processing_sketch_name"; then
                if capture_and_label_window "$processing_sketch_name" "Processing" "$processing_capture" "$temp_dir"; then
                    captured_processing=true
                fi
            fi
            
            # Create comparison image if we have both captures
            if [ "$captured_umfeld" = true ] && [ "$captured_processing" = true ]; then
                echo "Creating comparison image..."
                
                if [ -f "$umfeld_capture" ] && [ -f "$processing_capture" ]; then
                    if convert "$umfeld_capture" "$processing_capture" -append "$final_output" 2>/dev/null; then
                        echo "✓ Comparison image saved: $final_output"
                    else
                        echo "✗ Failed to create comparison image"
                    fi
                else
                    echo "✗ Input files missing for comparison"
                fi
            else
                echo "✗ Failed to capture both windows"
            fi
            
            # Clean up temporary directory
            rm -rf "$temp_dir"
        fi
        
        # Clean up all processes and windows
        echo "Cleaning up applications..."
        
        # Kill the specific processes we started
        if [ -n "$umfeld_pid" ]; then
            kill $umfeld_pid 2>/dev/null || true
            wait $umfeld_pid 2>/dev/null || true
        fi
        if [ -n "$processing_pid" ]; then
            kill $processing_pid 2>/dev/null || true
            wait $processing_pid 2>/dev/null || true
        fi
        
        # Wait a moment for graceful shutdown
        sleep 1
        
        # More targeted cleanup
        if pgrep -f "^./${project_name}$" >/dev/null 2>&1; then
            pkill -f "^./${project_name}$" 2>/dev/null || true
        fi
        
        if pgrep -f "processing.*${processing_sketch_name}" >/dev/null 2>&1; then
            pkill -f "processing.*${processing_sketch_name}" 2>/dev/null || true
        fi
        
        if pgrep -f "java.*${processing_sketch_name}" >/dev/null 2>&1; then
            pkill -f "java.*${processing_sketch_name}" 2>/dev/null || true
        fi
        
        # Wait a bit more to ensure cleanup
        sleep 1
        
        echo "Finished: $project_name"
        echo "----------------------------------------"
    else
        echo "✗ BUILD FAILED: $project_name"
        echo "Debug: cmake=$cmake_success, make=$make_success, executable=$([ -x "$project_abs_path/build/$project_name" ] && echo "yes" || echo "no")"
        echo "----------------------------------------"
    fi
done

echo "=========================================="
echo "MATCHING SUMMARY"
echo "=========================================="
echo -e "\033[32m✓ Found: $found_count\033[0m"
echo -e "\033[31m✗ Not found: $not_found_count\033[0m"
echo "Total: $total_projects"

# Print all not found project paths
if [ ${#not_found_projects[@]} -gt 0 ] && [ -z "$SPECIFIC_EXAMPLE" ]; then
    echo ""
    echo "=========================================="
    echo "NOT FOUND PROJECTS PATHS"
    echo "=========================================="
    for not_found_path in "${not_found_projects[@]}"; do
        echo -e "\033[31m✗\033[0m $not_found_path"
    done
fi

echo "Processing complete."
