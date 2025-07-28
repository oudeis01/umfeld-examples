#!/bin/bash
set -e

# This script runs all examples inside the Processing/ as well as the
# original java Processing examples in parallel and creates a 
# comparison video or image inside the respective umfeld example dir

# Function to read JSON value using python (more reliable than jq)
get_json_value() {
    local project_name="$1"
    local json_file="$2"
    
    if [ ! -f "$json_file" ]; then
        echo "DEBUG: JSON file does not exist: $json_file" >&2
        return 1
    fi
    
    # Use python to safely parse JSON and extract the value for the project
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
            output = f'{result[0]}:{result[1]}'
            print(output)
            sys.exit(0)
        else:
            print(f'DEBUG: Entry format invalid for {project_name}: {result}', file=sys.stderr)
    else:
        pass # Do nothing, so stdout is empty
    sys.exit(0) # Changed from 1 to 0
except Exception as e:
    print(f'DEBUG: Exception occurred: {e}', file=sys.stderr)
    sys.exit(1)
"
}

# Function to generate deterministic random values for consistent movement across applications
generate_movement_seed() {
    local project_name="$1"
    # Get MD5 hash
    local md5_hash=$(echo -n "$project_name" | md5sum | cut -d' ' -f1)
    # Take the first 8 characters of the hex hash and convert to decimal
    # This ensures a smaller, more manageable number for modulo operations
    printf "%d" "0x${md5_hash:0:8}"
}

# Function to simulate keyboard input using xdotool
simulate_keyboard_input() {
    local window_id="$1"
    local text_to_type="$2"
    
    if [ -z "$window_id" ] || [ -z "$text_to_type" ]; then
        echo "Error: Missing window_id or text_to_type" >&2
        return 1
    fi
    
    echo "DEBUG: Simulating keyboard input for window ID: $window_id with text: '$text_to_type'"
    
    # Activate the window and bring it to foreground
    echo "DEBUG: Attempting to activate window $window_id..."
    xdotool windowactivate "$window_id"
    local activate_status=$?
    if [ $activate_status -ne 0 ]; then
        echo "ERROR: xdotool windowactivate failed with exit code $activate_status" >&2
        return 1
    fi
    echo "DEBUG: Window activated. Sleeping 2.0s..."
    sleep 2.0 # Increased sleep for activation
    
    # Clear any existing text first (Ctrl+A then type)
    echo "DEBUG: Attempting to send Ctrl+A..."
    xdotool key --delay 100 ctrl+a
    local ctrl_a_status=$?
    if [ $ctrl_a_status -ne 0 ]; then
        echo "WARNING: xdotool ctrl+a failed with exit code $ctrl_a_status (might be okay if no text field is focused)" >&2
    fi
    echo "DEBUG: Ctrl+A sent. Sleeping 1.0s..."
    sleep 1.0 # Increased sleep
    
    # Type the text with a small delay between characters for realism
    echo "DEBUG: Typing text: '$text_to_type'"
    xdotool type --delay 100 "$text_to_type"
    local type_status=$?
    if [ $type_status -ne 0 ]; then
        echo "ERROR: xdotool type failed with exit code $type_status" >&2
        return 1
    fi # <-- Corrected to 'fi'
    echo "DEBUG: Text typed. Sleeping 1.0s..."
    sleep 1.0 # Increased sleep
    
    # Press Enter to confirm input
    echo "DEBUG: Attempting to send Return key..."
    xdotool key --delay 100 Return
    local return_status=$?
    if [ $return_status -ne 0 ]; then
        echo "WARNING: xdotool Return failed with exit code $return_status (might be okay)" >&2
    fi
    echo "DEBUG: Return key sent. Sleeping 2.0s..."
    sleep 2.0 # Increased sleep
    
    echo "DEBUG: Keyboard simulation complete."
    return 0
}

# Function to simulate mouse movement using xdotool
simulate_mouse_movement() {
    local window_id="$1"
    local movement_type="$2"
    local project_name="$3"
    
    if [ -z "$window_id" ] || [ -z "$movement_type" ] || [ -z "$project_name" ]; then
        echo "Error: Missing required parameters for mouse simulation"
        return 1
    fi
    
    echo "Simulating mouse movement: $movement_type"
    
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
    
    # Generate deterministic seed for movement
    local seed=$(generate_movement_seed "$project_name")
    local seed_num=$(($seed % 1000))
    
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
    local entry_y=$((usable_y + usable_height / 2))
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
            local duration_per_move=0.5  # seconds per movement
            
            # Start from the entry point (already positioned)
            local current_x=$entry_x
            local current_y=$entry_y
            
            for i in $(seq 1 $movements); do
                # Use seed and iteration to generate deterministic "random" positions
                local rand_x=$(( (seed_num * i * 73) % usable_width + usable_x ))
                local rand_y=$(( (seed_num * i * 137) % usable_height + usable_y ))
                
                echo "DEBUG: Smoothly moving to position $i: ($rand_x, $rand_y)"
                
                # Calculate smooth movement steps
                local steps=20
                local dx=$(( (rand_x - current_x) / steps ))
                local dy=$(( (rand_y - current_y) / steps ))
                local step_delay=25  # milliseconds
                
                # Perform smooth movement
                for step in $(seq 1 $steps); do
                    local intermediate_x=$((current_x + dx * step))
                    local intermediate_y=$((current_y + dy * step))
                    xdotool mousemove "$intermediate_x" "$intermediate_y" 2>/dev/null
                    sleep 0.0$step_delay
                done
                
                # Update current position
                current_x=$rand_x
                current_y=$rand_y
                
                # Pause at each position
                sleep 0.2
            done
            ;;
            
        "horizontal")
            # Move from left to right and back with smooth motion
            local start_x=$usable_x
            local end_x=$((usable_x + usable_width))
            local mid_y=$((usable_y + usable_height / 2))
            
            echo "DEBUG: Smooth horizontal movement from $start_x to $end_x at y=$mid_y"
            
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
            
            # Smooth move to end position
            steps=30
            dx=$(( (end_x - start_x) / steps ))
            for step in $(seq 1 $steps); do
                local intermediate_x=$((start_x + dx * step))
                xdotool mousemove "$intermediate_x" "$mid_y" 2>/dev/null
                sleep 0.05
            done
            
            sleep 0.3
            
            # Smooth move back to start
            for step in $(seq 1 $steps); do
                local intermediate_x=$((end_x - dx * step))
                xdotool mousemove "$intermediate_x" "$mid_y" 2>/dev/null
                sleep 0.05
            done
            
            sleep 0.3
            
            # Final smooth move to a position based on seed
            local final_x=$(( (seed_num * 89) % usable_width + usable_x ))
            steps=15
            dx=$(( (final_x - start_x) / steps ))
            for step in $(seq 1 $steps); do
                local intermediate_x=$((start_x + dx * step))
                xdotool mousemove "$intermediate_x" "$mid_y" 2>/dev/null
                sleep 0.03
            done
            ;;
            
        "diagonal")
            # Move diagonally across the window with smooth transitions
            local corners=4
            local positions=(
                "$usable_x $usable_y"  # top-left
                "$((usable_x + usable_width)) $usable_y"  # top-right
                "$((usable_x + usable_width)) $((usable_y + usable_height))"  # bottom-right
                "$usable_x $((usable_y + usable_height))"  # bottom-left
            )
            
            # Start from a corner based on seed
            local start_corner=$((seed_num % corners))
            
            echo "DEBUG: Smooth diagonal movement starting from corner $start_corner"
            
            # Start from entry position
            local current_x=$entry_x
            local current_y=$entry_y
            
            for i in $(seq 0 3); do
                local pos_index=$(( (start_corner + i) % corners ))
                # Fix array access issue
                case $pos_index in
                    0) local target_x=$usable_x; local target_y=$usable_y ;;
                    1) local target_x=$((usable_x + usable_width)); local target_y=$usable_y ;;
                    2) local target_x=$((usable_x + usable_width)); local target_y=$((usable_y + usable_height)) ;;
                    3) local target_x=$usable_x; local target_y=$((usable_y + usable_height)) ;;
                esac
                
                echo "DEBUG: Smoothly moving to corner $pos_index: ($target_x, $target_y)"
                
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

# Improved function to record video of a window using ffmpeg
record_video_start() {
    local window_id="$1"
    local output_file="$2"
    local label="$3"
    local app_type="${4:-}"
    
    if [ -z "$window_id" ] || [ -z "$output_file" ]; then
        echo "Error: Missing window_id or output_file for video recording" >&2
        return 1
    fi
    
    echo "Starting video recording: $label${app_type:+ ($app_type)}"
    
    # Get window geometry
    local window_info=$(xwininfo -id "$window_id" 2>/dev/null)
    if [ $? -ne 0 ]; then
        echo "Error: Could not get window information for recording" >&2
        return 1
    fi
    
    local win_x=$(echo "$window_info" | grep "Absolute upper-left X:" | awk '{print $4}')
    local win_y=$(echo "$window_info" | grep "Absolute upper-left Y:" | awk '{print $4}')
    local win_width=$(echo "$window_info" | grep "Width:" | awk '{print $2}')
    local win_height=$(echo "$window_info" | grep "Height:" | awk '{print $2}')
    
    # Standardized dimensions for easier concatenation
    local target_width=800
    local target_height=600
    local border_width=10
    local text_padding=30
    local final_width=$((target_width + 2 * border_width))
    local final_height=$((target_height + 2 * border_width + text_padding))
    
    echo "DEBUG: Recording area - x:$win_x y:$win_y w:$win_width h:$win_height" >&2
    echo "DEBUG: Target size - w:$target_width h:$target_height" >&2
    
    # Enhanced ffmpeg recording with better quality and standardized output
    # Run ffmpeg in background and capture its PID
    ffmpeg -y -f x11grab \
        -video_size "${win_width}x${win_height}" \
        -framerate 30 \
        -i "${DISPLAY}+${win_x},${win_y}" \
        -c:v libx264 \
        -preset medium \
        -crf 18 \
        -pix_fmt yuv420p \
        -vf "scale=${target_width}:${target_height}:force_original_aspect_ratio=decrease:eval=frame,pad=${target_width}:${target_height}:(ow-iw)/2:(oh-ih)/2:color=black,pad=w=${final_width}:h=${final_height}:x=${border_width}:y=${border_width}:color=0x4682B4,drawtext=text='${label}${app_type:+ (${app_type})}':fontcolor=white:fontsize=20:x=15:y=${final_height}-25" \
        "$output_file" >"$output_file.log" 2>&1 &
    
    local ffmpeg_pid=$!
    
    # Wait and verify ffmpeg started successfully
    sleep 1
    if ! kill -0 $ffmpeg_pid 2>/dev/null; then
        echo "Error: FFmpeg failed to start" >&2
        return 1
    fi
    
    echo $ffmpeg_pid # Print PID to stdout for capture
    return 0
}

# Function to stop video recording
record_video_start() {
    local window_id="$1"
    local output_file="$2"
    local label="$3"
    local app_type="${4:-}"
    
    if [ -z "$window_id" ] || [ -z "$output_file" ]; then
        echo "Error: Missing window_id or output_file for video recording" >&2
        return 1
    fi
    
    echo "Starting video recording: $label${app_type:+ ($app_type)}"
    
    # Get window geometry
    local window_info=$(xwininfo -id "$window_id" 2>/dev/null)
    if [ $? -ne 0 ]; then
        echo "Error: Could not get window information for recording" >&2
        return 1
    fi
    
    local win_x=$(echo "$window_info" | grep "Absolute upper-left X:" | awk '{print $4}')
    local win_y=$(echo "$window_info" | grep "Absolute upper-left Y:" | awk '{print $4}')
    local win_width=$(echo "$window_info" | grep "Width:" | awk '{print $2}')
    local win_height=$(echo "$window_info" | grep "Height:" | awk '{print $2}')
    
    # Validate geometry values
    if [ -z "$win_x" ] || [ -z "$win_y" ] || [ -z "$win_width" ] || [ -z "$win_height" ]; then
        echo "Error: Could not parse window geometry" >&2
        return 1
    fi
    
    # Ensure even dimensions for video encoding (required for some codecs)
    win_width=$(( (win_width + 1) / 2 * 2 ))
    win_height=$(( (win_height + 1) / 2 * 2 ))
    
    # Standardized dimensions for easier concatenation
    local target_width=800
    local target_height=600
    local border_width=10
    local text_padding=30
    local final_width=$((target_width + 2 * border_width))
    local final_height=$((target_height + 2 * border_width + text_padding))
    
    echo "DEBUG: Recording area - x:$win_x y:$win_y w:$win_width h:$win_height" >&2
    echo "DEBUG: Target size - w:$target_width h:$target_height" >&2
    
    # Create a temporary log file for ffmpeg output
    local log_file="${output_file}.log"
    
    # Enhanced ffmpeg recording with better quality and error handling
    # Use a more reliable codec configuration
    ffmpeg -y \
        -f x11grab \
        -video_size "${win_width}x${win_height}" \
        -framerate 60 \
        -i "${DISPLAY}+${win_x},${win_y}" \
        -t 10 \
        -c:v libx264 \
        -preset ultrafast \
        -crf 23 \
        -pix_fmt yuv420p \
        -movflags +faststart \
        -vf "scale=${target_width}:${target_height}:force_original_aspect_ratio=decrease:eval=frame,pad=${target_width}:${target_height}:(ow-iw)/2:(oh-ih)/2:color=black,pad=w=${final_width}:h=${final_height}:x=${border_width}:y=${border_width}:color=0x4682B4,drawtext=text='${label}${app_type:+ (${app_type})}':fontcolor=white:fontsize=20:x=15:y=${final_height}-25:fontfile=/usr/share/fonts/TTF/DejaVuSans.ttf" \
        "$output_file" >"$log_file" 2>&1 &
    
    local ffmpeg_pid=$!
    
    # Wait longer and verify ffmpeg started successfully
    sleep 2
    if ! kill -0 $ffmpeg_pid 2>/dev/null; then
        echo "Error: FFmpeg failed to start" >&2
        if [ -f "$log_file" ]; then
            echo "FFmpeg error log:" >&2
            tail -10 "$log_file" >&2
        fi
        return 1
    fi
    
    echo $ffmpeg_pid # Print PID to stdout for capture
    return 0
}

# Function to stop video recording with better error handling
record_video_stop() {
    local ffmpeg_pid="$1"
    local output_file="$2"
    
    if [ -z "$ffmpeg_pid" ]; then
        echo "Error: Missing ffmpeg_pid to stop recording" >&2
        return 1
    fi
    
    echo "Stopping video recording (PID: $ffmpeg_pid)..."
    
    # Check if process is still running
    if kill -0 "$ffmpeg_pid" 2>/dev/null; then
        # Send SIGTERM first for graceful shutdown
        kill -SIGTERM "$ffmpeg_pid" 2>/dev/null || true
        
        # Wait for graceful shutdown with timeout
        local timeout=15
        local count=0
        while kill -0 "$ffmpeg_pid" 2>/dev/null && [ $count -lt $timeout ]; do
            sleep 1
            count=$((count + 1))
            echo -n "."
        done
        echo
        
        # Force kill if still running
        if kill -0 "$ffmpeg_pid" 2>/dev/null; then
            echo "Warning: Force killing ffmpeg process"
            kill -SIGKILL "$ffmpeg_pid" 2>/dev/null || true
            sleep 2
        fi
    fi
    
    # Wait for file system to sync
    sync
    sleep 3
    
    if [ -f "$output_file" ] && [ -s "$output_file" ]; then
        # Verify the video file is valid
        if ffprobe -v quiet -select_streams v:0 -show_entries stream=codec_name -of csv=p=0 "$output_file" >/dev/null 2>&1; then
            echo "✓ Video recorded successfully: $output_file"
            local file_size=$(du -h "$output_file" | cut -f1)
            local duration=$(ffprobe -v quiet -show_entries format=duration -of csv=p=0 "$output_file" 2>/dev/null || echo "unknown")
            echo "  File size: $file_size, Duration: ${duration}s"
            return 0
        else
            echo "✗ Video file appears to be corrupted: $output_file" >&2
        fi
    else
        echo "✗ Failed to record video or output file not found/empty: $output_file" >&2
    fi
    
    # Show ffmpeg log on failure
    if [ -f "$output_file.log" ]; then
        echo "FFmpeg log:"
        tail -20 "$output_file.log"
    fi
    return 1
}

# Enhanced function to create comparison video with better error handling
create_comparison_video() {
    local umfeld_video="$1"
    local processing_video="$2"
    local final_output="$3"
    local project_name="$4"
    
    echo "Creating enhanced comparison video for $project_name..."
    
    # Verify input files exist and are not empty
    if [ ! -f "$umfeld_video" ] || [ ! -s "$umfeld_video" ]; then
        echo "✗ Umfeld video missing or empty: $umfeld_video"
        return 1
    fi
    
    if [ ! -f "$processing_video" ] || [ ! -s "$processing_video" ]; then
        echo "✗ Processing video missing or empty: $processing_video"
        return 1
    fi
    
    # Validate video files are not corrupted
    echo "Validating input videos..."
    if ! ffprobe -v quiet -select_streams v:0 -show_entries stream=codec_name -of csv=p=0 "$umfeld_video" >/dev/null 2>&1; then
        echo "✗ Umfeld video is corrupted or invalid: $umfeld_video"
        return 1
    fi
    
    if ! ffprobe -v quiet -select_streams v:0 -show_entries stream=codec_name -of csv=p=0 "$processing_video" >/dev/null 2>&1; then
        echo "✗ Processing video is corrupted or invalid: $processing_video"
        return 1
    fi
    
    # Get video information with error handling
    local umfeld_duration=$(ffprobe -v quiet -show_entries format=duration -of csv=p=0 "$umfeld_video" 2>/dev/null)
    local processing_duration=$(ffprobe -v quiet -show_entries format=duration -of csv=p=0 "$processing_video" 2>/dev/null)
    
    # Provide fallback durations if probe fails
    if [ -z "$umfeld_duration" ] || [ "$umfeld_duration" = "N/A" ]; then
        echo "Warning: Could not determine Umfeld video duration, using 8 seconds"
        umfeld_duration="8.0"
    fi
    
    if [ -z "$processing_duration" ] || [ "$processing_duration" = "N/A" ]; then
        echo "Warning: Could not determine Processing video duration, using 8 seconds"
        processing_duration="8.0"
    fi
    
    echo "DEBUG: Umfeld duration: $umfeld_duration"
    echo "DEBUG: Processing duration: $processing_duration"
    
    # Use the shorter duration, with a minimum of 5 seconds (no maximum limit)
    local min_duration=$(python3 -c "
import sys
try:
    u_dur = float('$umfeld_duration')
    p_dur = float('$processing_duration')
    min_dur = min(u_dur, p_dur)
    # Use minimum of 5 seconds to ensure interaction is captured
    result = max(5.0, min_dur)
    print(f'{result:.1f}')
except:
    print('7.0')
" 2>/dev/null || echo "7.0")
    
    echo "DEBUG: Using duration: $min_duration seconds"
    
    # Create comparison video with improved filter chain and error handling
    local temp_output="${final_output}.tmp"
    local log_file="${final_output}.log"
    
    # First attempt: simple vertical stack
    if ffmpeg -y \
        -i "$umfeld_video" \
        -i "$processing_video" \
        -filter_complex "
        [0:v]setpts=PTS-STARTPTS,scale=820:630:force_original_aspect_ratio=decrease,pad=820:630:(ow-iw)/2:(oh-ih)/2:color=black[v0];
        [1:v]setpts=PTS-STARTPTS,scale=820:630:force_original_aspect_ratio=decrease,pad=820:630:(ow-iw)/2:(oh-ih)/2:color=black[v1];
        [v0][v1]vstack=inputs=2[v];
        [v]drawtext=text='$project_name Comparison':fontcolor=white:fontsize=24:x=(w-text_w)/2:y=20:box=1:boxcolor=black@0.7:boxborderw=3:fontfile=/usr/share/fonts/TTF/DejaVuSans-Bold.ttf[final]
        " \
        -map "[final]" \
        -c:v libx264 \
        -preset medium \
        -crf 18 \
        -pix_fmt yuv420p \
        -movflags +faststart \
        -t "$min_duration" \
        "$temp_output" >"$log_file" 2>&1; then
        
        # Move temp file to final location
        mv "$temp_output" "$final_output"
        echo "✓ Enhanced comparison video saved: $final_output"
        
        # Show file info
        local file_size=$(du -h "$final_output" | cut -f1)
        local actual_duration=$(ffprobe -v quiet -show_entries format=duration -of csv=p=0 "$final_output" 2>/dev/null || echo "unknown")
        echo "  File size: $file_size, Duration: ${actual_duration}s"
        
        return 0
    else
        echo "✗ Failed to create comparison video"
        echo "FFmpeg error log:"
        if [ -f "$log_file" ]; then
            tail -20 "$log_file"
        fi
        
        # Clean up temp file
        rm -f "$temp_output"
        
        # Try fallback method: simple concatenation without complex filters
        echo "Trying fallback method..."
        if ffmpeg -y \
            -i "$umfeld_video" \
            -i "$processing_video" \
            -filter_complex "[0:v][1:v]vstack=inputs=2[v]" \
            -map "[v]" \
            -c:v libx264 \
            -preset ultrafast \
            -crf 23 \
            -pix_fmt yuv420p \
            -t "$min_duration" \
            "$final_output" >"${log_file}.fallback" 2>&1; then
            
            echo "✓ Comparison video created with fallback method: $final_output"
            local file_size=$(du -h "$final_output" | cut -f1)
            echo "  File size: $file_size"
            return 0
        else
            echo "✗ Both methods failed to create comparison video"
            if [ -f "${log_file}.fallback" ]; then
                echo "Fallback error log:"
                tail -10 "${log_file}.fallback"
            fi
        fi
        
        # Save debug videos for analysis
        local debug_dir=$(dirname "$final_output")/debug_videos
        mkdir -p "$debug_dir"
        cp "$umfeld_video" "$debug_dir/debug_umfeld_${project_name}.mp4" 2>/dev/null || true
        cp "$processing_video" "$debug_dir/debug_processing_${project_name}.mp4" 2>/dev/null || true
        
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
    local window_id=$(xwininfo -name "$window_name" 2>/dev/null | grep "Window id:" | awk '{print $4}')
    
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
                # Get image dimensions
                local img_width=$(identify -format "%w" "$temp_capture" 2>/dev/null)
                local img_height=$(identify -format "%h" "$temp_capture" 2>/dev/null)
                
                echo "DEBUG: Original image dimensions: ${img_width}x${img_height}"
                
                if [ -n "$img_width" ] && [ -n "$img_height" ]; then
                    # Define border and padding
                    local border_width=10
                    local text_padding=30
                    
                    # Calculate new dimensions with border and text area
                    local bordered_width=$((img_width + 2 * border_width))
                    local bordered_height=$((img_height + 2 * border_width + text_padding))
                    
                    echo "DEBUG: Creating image with blue border and text label..."
                    echo "DEBUG: Final dimensions: ${bordered_width}x${bordered_height}"
                    
                    # Create image with blue border and text using ImageMagick (more reliable for text)
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
                        echo "DEBUG: ImageMagick method failed, trying FFmpeg..."
                        
                        # Fallback to FFmpeg method
                        if ffmpeg -y -i "$temp_capture" \
                            -vf "pad=w=${bordered_width}:h=${bordered_height}:x=${border_width}:y=${border_width}:color=rgb(70,130,180),drawtext=text='$label':fontcolor=white:fontsize=20:x=15:y=${bordered_height}-25" \
                            -pix_fmt rgba \
                            "$output_file" 2>/dev/null; then
                            
                            rm -f "$temp_capture"
                            echo "Successfully captured and labeled: $label (FFmpeg fallback)"
                            return 0
                        else
                            echo "DEBUG: Both methods failed, saving original with simple border..."
                            # Last resort: just add border without text
                            if convert "$temp_capture" \
                                -bordercolor "rgb(70,130,180)" \
                                -border ${border_width}x${border_width} \
                                "$output_file" 2>/dev/null; then
                                
                                rm -f "$temp_capture"
                                echo "Captured with border only: $label"
                                return 0
                            else
                                cp "$temp_capture" "$output_file"
                                rm -f "$temp_capture"
                                echo "Captured without modifications: $label"
                                return 0
                            fi
                        fi
                    fi
                else
                    echo "DEBUG: Failed to get image dimensions"
                fi
            else
                echo "DEBUG: Captured file does not exist: $temp_capture"
            fi
        else
            echo "DEBUG: Import command failed"
        fi
    else
        echo "DEBUG: Could not find window ID for: $window_name"
    fi
    
    echo "Failed to capture window: $window_name"
    return 1
}

# Function to wait for a window to appear
wait_for_window() {
    local window_name="$1"
    local timeout=15  # Increased timeout for Processing apps
    local count=0
    
    echo "Waiting for window: $window_name"
    while [ $count -lt $timeout ]; do
        if xwininfo -name "$window_name" >/dev/null 2>&1; then
            echo "Window found: $window_name"
            return 0
        fi
        sleep 1
        count=$((count + 1))
        echo -n "."
    done
    echo ""
    echo "Timeout waiting for window: $window_name"
    return 1
}

# Function for fuzzy string matching using awk (no external dependencies)
fuzzy_match() {
    local search_term="$1"
    local search_dir="$2"
    
    if [ ! -d "$search_dir" ]; then
        return 1
    fi
    
    # Get all directory names and calculate similarity scores
    find "$search_dir" -maxdepth 1 -type d -exec basename {} \; | tail -n +2 | \
    awk -v search="$search_term" '
    function levenshtein(s1, s2) {
        n = length(s1)
        m = length(s2)
        
        # Initialize distance matrix
        for (i = 0; i <= n; i++) d[i,0] = i
        for (j = 0; j <= m; j++) d[0,j] = j
        
        # Calculate distances
        for (i = 1; i <= n; i++) {
            for (j = 1; j <= m; j++) {
                cost = (substr(s1,i,1) == substr(s2,j,1)) ? 0 : 1
                d[i,j] = d[i-1,j] + 1      # deletion
                if (d[i,j-1] + 1 < d[i,j]) d[i,j] = d[i,j-1] + 1  # insertion
                if (d[i-1,j-1] + cost < d[i,j]) d[i,j] = d[i-1,j-1] + cost  # substitution
            }
        }
        return d[n,m]
    }
    
    function similarity_score(s1, s2) {
        # Convert to lowercase for comparison
        s1_lower = tolower(s1)
        s2_lower = tolower(s2)
        
        # Exact match gets highest score
        if (s1_lower == s2_lower) return 1000
        
        # Check if one contains the other
        
        
        # Calculate edit distance based similarity
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
        if (best_score >= 70) {  # Much higher similarity threshold
            print best_match
        }
    }'
}

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
# Use bash array to properly handle paths
PROJECT_PATHS=()

if [ -n "$SPECIFIC_EXAMPLE" ]; then
    # Find specific example
    echo "DEBUG: Raw find output for specific example:"
    find Processing -mindepth 2 -type f -name "application.cpp" 2>/dev/null -exec bash -c 'echo "$(dirname "{}")"' \; | grep -E "/${SPECIFIC_EXAMPLE}$"
    while IFS= read -r project_dir; do
        PROJECT_PATHS+=("$project_dir")
    done < <(find Processing -mindepth 2 -type f -name "application.cpp" 2>/dev/null -exec bash -c 'echo "$(dirname "{}")"' \; | grep -E "/${SPECIFIC_EXAMPLE}$")
    if [ ${#PROJECT_PATHS[@]} -eq 0 ]; then
        echo "Error: Example '$SPECIFIC_EXAMPLE' not found"
        echo "Available examples:"
        find Processing -mindepth 2 -type f -name "application.cpp" 2>/dev/null -exec bash -c 'echo "$(basename "$(dirname "{}")")"' \; | sort | uniq
        exit 1
    fi
else
    # Find all examples
    echo "DEBUG: Raw find output for all examples:"
    find Processing -mindepth 2 -type f -name "application.cpp" 2>/dev/null -exec bash -c 'echo "$(dirname "{}")"' \;
    while IFS= read -r project_dir; do
        PROJECT_PATHS+=("$project_dir")
    done < <(find Processing -mindepth 2 -type f -name "application.cpp" 2>/dev/null -exec bash -c 'echo "$(dirname "{}")"' \;)
fi

echo "DEBUG: PROJECT_PATHS after population: ${PROJECT_PATHS[@]}"

# Initialize counters and arrays
found_count=0
not_found_count=0
total_projects=0

# Array to store not found projects
declare -a not_found_projects

# Loop through each project path
for project_path in "${PROJECT_PATHS[@]}"
do
    total_projects=$((total_projects + 1))
    
    # DEBUG: Print what we're processing
    echo "DEBUG: Processing path: '$project_path'"
    echo "DEBUG: Current working directory: $(pwd)"
    echo "DEBUG: Path exists check: $([ -d "$project_path" ] && echo "YES" || echo "NO")"
    
    # Convert to absolute path at the beginning
    project_abs_path="$ORIGINAL_DIR/$project_path"
    echo "DEBUG: Absolute path: '$project_abs_path'"
    echo "DEBUG: Absolute path exists: $([ -d "$project_abs_path" ] && echo "YES" || echo "NO")"
    
    # Get the project name from the path
    project_name=$(basename "$project_path")
    echo "DEBUG: Project name: '$project_name'"
    
    # Find and run the corresponding Processing example
    # Replace underscores with spaces and clean up the name
    processing_project_search_name=$(echo "$project_name" | tr '_' ' ' | sed 's/[^a-zA-Z0-9 ]//g')
    
    # Default Processing examples path
processing_project_base_path="/opt/processing/modes/java/examples"

# Parse command-line options
while getopts ":p:" opt; do
  case ${opt} in
    p )
      processing_project_base_path=$OPTARG
      ;;
    \? )
      echo "Invalid option: -$OPTARG" >&2
      exit 1
      ;;
    : )
      echo "Invalid option: -$OPTARG requires an argument" >&2
      exit 1
      ;;
  esac
done
shift $((OPTIND -1))
    
    # Get category and subcategory from umfeld path
    processing_category_path=$(echo "$project_path" | sed -E 's|^Processing/([^/]+)/.*$|\1|')
    processing_subcategory_path=$(echo "$project_path" | sed -E 's|^Processing/[^/]+/([^/]+)/.*$|\1|')
    
    # Build the expected Processing path structure
    processing_search_base="$processing_project_base_path/$processing_category_path"
    
    # First try direct match in the full Processing examples directory
    processing_project_dir=$(find "$processing_project_base_path" -type d -iname "$processing_project_search_name" 2>/dev/null | head -n 1)
    
    # If not found, try with original name (with underscores converted to no separator)
    if [ ! -d "$processing_project_dir" ]; then
        # Convert conditionals_1 to conditionals1 (common Processing naming)
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
                
                # Additional validation: the match should contain most of the original name
                if [ -n "$fuzzy_match_result" ]; then
                    # Check if the core name (without common prefixes/suffixes) is present
                    core_name=$(echo "$project_name" | sed 's/^embedding_//g' | sed 's/_[0-9]*$//g' | tr '_' ' ')
                    if [[ "$(echo "$fuzzy_match_result" | tr '[:upper:]' '[:lower:]')" =~ "$(echo "$core_name" | tr '[:upper:]' '[:lower:]')" ]]; then
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
        # Add to not found array
        not_found_projects+=("$project_path")
    fi
    
    # Build and run Umfeld example
    echo "Building Umfeld: $project_name..."
    
    # DEBUG: More detailed path checking
    echo "DEBUG: About to check directory existence for: '$project_path'"
    
    # Check if the project directory exists first
    if [ ! -d "$project_abs_path" ]; then
        echo "DEBUG: Directory check failed for: '$project_abs_path'"
        echo "Project directory does not exist: $project_abs_path"
        echo "----------------------------------------"
        continue
    fi
    
    echo "DEBUG: Directory exists, proceeding with build..."
    
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
        
# Improved recording workflow section (replace in main script)
# This should replace the recording workflow section starting from "# Check if this project has test properties defined"

        # Check if this project has test properties defined
        test_props=""
        if [ -f "$TEST_PROPS_FILE" ]; then
            echo "DEBUG: Looking for test properties for project: '$project_name'"
            echo "DEBUG: Using JSON file: $TEST_PROPS_FILE"
            test_props=$(get_json_value "$project_name" "$TEST_PROPS_FILE")
            echo "DEBUG: get_json_value returned: '$test_props'"
        else
            echo "DEBUG: Test properties file not found: $TEST_PROPS_FILE"
        fi
        
        if [ -n "$test_props" ]; then
            echo "Found test properties for $project_name: $test_props"
            
            # Parse test properties
            input_type=$(echo "$test_props" | cut -d':' -f1)
            input_data=$(echo "$test_props" | cut -d':' -f2-)
            
            echo "📹 RECORDING MODE: $project_name with $input_type interaction"
            
            # Create temporary directory for video processing
            temp_dir=$(mktemp -d)
            echo "DEBUG: Created temp directory: $temp_dir"
            
            # Variables for recorded videos
            umfeld_video="$temp_dir/umfeld_video.mp4"
            processing_video="$temp_dir/processing_video.mp4"
            final_output="$project_abs_path/comparison_${project_name}.mp4"
            
            # Launch Processing example first and wait for it to be ready
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
                ./"$project_name" >/dev/null 2>&1
            ) &
            umfeld_pid=$!
            
            # Wait longer for windows to appear and stabilize
            echo "Waiting for applications to start..."
            sleep 7  # Increased wait time
            
            # Find windows with better error handling and retry logic
            umfeld_window_id=""
            processing_window_id=""
            
            # Try multiple approaches to find Umfeld window
            echo "Searching for Umfeld window..."
            for attempt in 1 2 3 4; do
                umfeld_window_id=$(xwininfo -name "$project_name" 2>/dev/null | grep "Window id:" | awk '{print $4}')
                if [ -n "$umfeld_window_id" ]; then
                    echo "Found Umfeld window on attempt $attempt: $umfeld_window_id"
                    break
                fi
                echo "Attempt $attempt: Looking for Umfeld window..."
                sleep 2
            done
            
            # Try multiple approaches to find Processing window
            echo "Searching for Processing window..."
            for attempt in 1 2 3 4; do
                processing_window_id=$(xwininfo -name "$processing_sketch_name" 2>/dev/null | grep "Window id:" | awk '{print $4}')
                if [ -z "$processing_window_id" ]; then
                    # Try alternative search patterns
                    processing_window_id=$(xwininfo -tree -root 2>/dev/null | grep -E "(Processing|$processing_sketch_name)" | head -n1 | awk '{print $1}' | tr -d '()')
                fi
                if [ -n "$processing_window_id" ]; then
                    echo "Found Processing window on attempt $attempt: $processing_window_id"
                    break
                fi
                echo "Attempt $attempt: Looking for Processing window..."
                sleep 2
            done
            
            if [ -z "$umfeld_window_id" ]; then
                echo "✗ Failed to find Umfeld window"
                # Clean up
                kill "$umfeld_pid" "$processing_pid" 2>/dev/null || true
                rm -rf "$temp_dir"
                echo "----------------------------------------"
                continue
            fi
            
            if [ -z "$processing_window_id" ]; then
                echo "✗ Failed to find Processing window"
                # Clean up
                kill "$umfeld_pid" "$processing_pid" 2>/dev/null || true
                rm -rf "$temp_dir"
                echo "----------------------------------------"
                continue
            fi
            
            echo "Found windows - Umfeld: $umfeld_window_id, Processing: $processing_window_id"
            
            # Position windows for better recording with improved error handling
            position_windows_success=false
            if [ -n "$umfeld_window_id" ] && [ -n "$processing_window_id" ]; then
                # Get Umfeld window geometry
                umfeld_geometry=$(xwininfo -id "$umfeld_window_id" 2>/dev/null)
                if [ $? -eq 0 ]; then
                    umfeld_x=$(echo "$umfeld_geometry" | grep "Absolute upper-left X:" | awk '{print $4}')
                    umfeld_y=$(echo "$umfeld_geometry" | grep "Absolute upper-left Y:" | awk '{print $4}')
                    umfeld_height=$(echo "$umfeld_geometry" | grep "Height:" | awk '{print $2}')
                    
                    if [ -n "$umfeld_x" ] && [ -n "$umfeld_y" ] && [ -n "$umfeld_height" ]; then
                        # Calculate new position for Processing window (below Umfeld)
                        processing_x=$umfeld_x
                        processing_y=$((umfeld_y + umfeld_height + 50))
                        
                        echo "Positioning Processing window at ($processing_x, $processing_y)"
                        if xdotool windowmove "$processing_window_id" "$processing_x" "$processing_y" 2>/dev/null; then
                            position_windows_success=true
                        elif wmctrl -i -r "$processing_window_id" -e "0,${processing_x},${processing_y},-1,-1" 2>/dev/null; then
                            position_windows_success=true
                        else
                            echo "Warning: Could not position Processing window"
                        fi
                    fi
                fi
            fi
            
            # Wait for windows to settle after positioning
            sleep 3
            
            # Record both applications with improved error handling
            record_success=false
            
            # Record Umfeld application with interaction
            echo "Recording Umfeld application..."
            record_umfeld_pid=$(record_video_start "$umfeld_window_id" "$umfeld_video" "Umfeld" "umfeld")
            umfeld_record_success=false
            
            if [ -n "$record_umfeld_pid" ] && [ "$record_umfeld_pid" != "0" ]; then
                echo "Started Umfeld recording (PID: $record_umfeld_pid)"
                
                # Wait for recording to start properly
                sleep 3
                
                # Perform interaction based on input type
                case "$input_type" in
                    "keyboard")
                        echo "Performing keyboard interaction: $input_data"
                        simulate_keyboard_input "$umfeld_window_id" "$input_data"
                        ;;
                    "mouse")
                        echo "Performing mouse interaction: $input_data"
                        simulate_mouse_movement "$umfeld_window_id" "$input_data" "$project_name"
                        ;;
                    *)
                        echo "Unknown interaction type: $input_type"
                        ;;
                esac
                
                # Wait for interaction effects to be visible
                sleep 4
                
                # Stop recording
                if record_video_stop "$record_umfeld_pid" "$umfeld_video"; then
                    umfeld_record_success=true
                fi
            else
                echo "✗ Failed to start Umfeld recording"
            fi
            
            # Record Processing application with the same interaction
            echo "Recording Processing application..."
            record_processing_pid=$(record_video_start "$processing_window_id" "$processing_video" "Processing" "processing")
            processing_record_success=false
            
            if [ -n "$record_processing_pid" ] && [ "$record_processing_pid" != "0" ]; then
                echo "Started Processing recording (PID: $record_processing_pid)"
                
                # Wait for recording to start properly
                sleep 3
                
                # Perform the same interaction (deterministic for mouse, same text for keyboard)
                case "$input_type" in
                    "keyboard")
                        echo "Performing keyboard interaction: $input_data"
                        simulate_keyboard_input "$processing_window_id" "$input_data"
                        ;;
                    "mouse")
                        echo "Performing mouse interaction: $input_data"
                        simulate_mouse_movement "$processing_window_id" "$input_data" "$project_name"
                        ;;
                    *)
                        echo "Unknown interaction type: $input_type"
                        ;;
                esac
                
                # Wait for interaction effects to be visible
                sleep 4
                
                # Stop recording
                if record_video_stop "$record_processing_pid" "$processing_video"; then
                    processing_record_success=true
                fi
            else
                echo "✗ Failed to start Processing recording"
            fi
            
            # Create comparison video if we have both recordings
            if [ "$umfeld_record_success" = true ] && [ "$processing_record_success" = true ]; then
                echo "Creating comparison video..."
                if create_comparison_video "$umfeld_video" "$processing_video" "$final_output" "$project_name"; then
                    echo "✓ Comparison video created successfully"
                    record_success=true
                else
                    echo "✗ Failed to create comparison video"
                fi
            else
                echo "✗ Missing video files for comparison"
                echo "  Umfeld recording success: $umfeld_record_success"
                echo "  Processing recording success: $processing_record_success"
                echo "  Umfeld video exists: $([ -f "$umfeld_video" ] && echo "YES" || echo "NO")"
                echo "  Processing video exists: $([ -f "$processing_video" ] && echo "YES" || echo "NO")"
                
                # Save any successful recordings for debugging
                if [ -f "$umfeld_video" ]; then
                    cp "$umfeld_video" "$project_abs_path/debug_umfeld_${project_name}.mp4"
                    echo "  Saved debug Umfeld video"
                fi
                if [ -f "$processing_video" ]; then
                    cp "$processing_video" "$project_abs_path/debug_processing_${project_name}.mp4"
                    echo "  Saved debug Processing video"
                fi
            fi
            
            # Clean up temporary directory
            rm -rf "$temp_dir"
            
            if [ "$record_success" = true ]; then
                echo "✅ RECORDING COMPLETE: $project_name"
            else
                echo "❌ RECORDING FAILED: $project_name"
            fi
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
                ./"$project_name" >/dev/null 2>&1
            ) &
            umfeld_pid=$!
            
            # Wait for Umfeld window to appear first
            sleep 3
            
            # Get Umfeld window position and size
            umfeld_window_id=$(xwininfo -name "$project_name" 2>/dev/null | grep "Window id:" | awk '{print $4}')
            if [ -n "$umfeld_window_id" ]; then
                # Get window geometry
                umfeld_geometry=$(xwininfo -id "$umfeld_window_id" 2>/dev/null)
                umfeld_x=$(echo "$umfeld_geometry" | grep "Absolute upper-left X:" | awk '{print $4}')
                umfeld_y=$(echo "$umfeld_geometry" | grep "Absolute upper-left Y:" | awk '{print $4}')
                umfeld_height=$(echo "$umfeld_geometry" | grep "Height:" | awk '{print $2}')
                
                echo "DEBUG: Umfeld window position: ${umfeld_x},${umfeld_y} height: ${umfeld_height}"
                
                # Calculate new position for Processing window (below Umfeld)
                processing_x=$umfeld_x
                processing_y=$((umfeld_y + umfeld_height + 30))  # 30px gap
                
                echo "DEBUG: Moving Processing window to: ${processing_x},${processing_y}"
                
                # Wait a bit more for Processing window to appear
                sleep 2
                
                # Find and move Processing window
                processing_window_id=$(xwininfo -name "$processing_sketch_name" 2>/dev/null | grep "Window id:" | awk '{print $4}')
                if [ -z "$processing_window_id" ]; then
                    # Try alternative search methods
                    processing_window_id=$(xwininfo -tree -root | grep -i "$processing_sketch_name" | head -n1 | awk '{print $1}')
                fi
                
                if [ -n "$processing_window_id" ]; then
                    echo "DEBUG: Found Processing window ID: $processing_window_id"
                    # Move Processing window below Umfeld window
                    xdotool windowmove "$processing_window_id" "$processing_x" "$processing_y" 2>/dev/null || {
                        echo "DEBUG: xdotool failed, trying wmctrl..."
                        wmctrl -i -r "$processing_window_id" -e "0,${processing_x},${processing_y},-1,-1" 2>/dev/null || {
                            echo "DEBUG: Both xdotool and wmctrl failed to move window"
                        }
                    }
                else
                    echo "DEBUG: Could not find Processing window for positioning"
                fi
            else
                echo "DEBUG: Could not find Umfeld window for reference positioning"
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
                
                # Debug: Check if both input files exist and get their info
                echo "DEBUG: Checking input files..."
                echo "DEBUG: Umfeld capture exists: $([ -f "$umfeld_capture" ] && echo "YES" || echo "NO")"
                echo "DEBUG: Processing capture exists: $([ -f "$processing_capture" ] && echo "YES" || echo "NO")"
                
                if [ -f "$umfeld_capture" ] && [ -f "$processing_capture" ]; then
                    echo "DEBUG: Umfeld image info: $(identify "$umfeld_capture" 2>/dev/null || echo "Failed to get info")"
                    echo "DEBUG: Processing image info: $(identify "$processing_capture" 2>/dev/null || echo "Failed to get info")"
                    
                    echo "DEBUG: Attempting vertical image concatenation..."
                    
                    # Method 1: Using ImageMagick for vertical concatenation (more reliable)
                    if convert "$umfeld_capture" "$processing_capture" -append "$final_output" 2>/dev/null; then
                        echo "✓ Comparison image saved (ImageMagick method): $final_output"
                    elif ffmpeg -y -i "$umfeld_capture" -i "$processing_capture" \
                        -filter_complex "[0:v][1:v]vstack=inputs=2[v]" \
                        -map "[v]" -pix_fmt rgba \
                        "$final_output" 2>/dev/null; then
                        # Method 2: Using ffmpeg with vertical stack as fallback
                        echo "✓ Comparison image saved (FFmpeg method): $final_output"
                    else
                        echo "✗ Failed to create comparison image with both methods"
                        echo "DEBUG: Saving individual images for inspection..."
                        cp "$umfeld_capture" "$project_abs_path/debug_umfeld_${project_name}.png" 2>/dev/null || true
                        cp "$processing_capture" "$project_abs_path/debug_processing_${project_name}.png" 2>/dev/null || true
                    fi
                else
                    echo "✗ Input files missing for comparison"
                fi
            else
                echo "✗ Failed to capture both windows (Umfeld: $captured_umfeld, Processing: $captured_processing)"
            fi
            
            # Clean up temporary directory
            rm -rf "$temp_dir"
        fi
        
        # Clean up all processes and windows
        echo "Cleaning up applications..."
        
        # Kill the specific processes we started (with error suppression)
        if [ -n "$umfeld_pid" ]; then
            kill "$umfeld_pid" 2>/dev/null || true
            wait "$umfeld_pid" 2>/dev/null || true
        fi
        if [ -n "$processing_pid" ]; then
            kill "$processing_pid" 2>/dev/null || true
            wait "$processing_pid" 2>/dev/null || true
        fi
        
        # Wait a moment for graceful shutdown
        sleep 1
        
        # More targeted cleanup - only kill processes that match exact patterns
        # Kill umfeld executable specifically
        if pgrep -f "^./${project_name}$" >/dev/null 2>&1; then
            pkill -f "^./${project_name}$" 2>/dev/null || true
        fi
        
        # Kill Processing sketch more specifically 
        if pgrep -f "processing.*${processing_sketch_name}" >/dev/null 2>&1; then
            pkill -f "processing.*${processing_sketch_name}" 2>/dev/null || true
        fi
        
        # Kill java processes that are specifically Processing sketches (not all java processes)
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

echo "========================================"
echo "MATCHING SUMMARY"
echo "========================================"
echo -e "\033[32m✓ Found: $found_count\033[0m"
echo -e "\033[31m✗ Not found: $not_found_count\033[0m"
echo "Total: $total_projects"

# Print all not found project paths (only if not running specific example)
if [ ${#not_found_projects[@]} -gt 0 ] && [ -z "$SPECIFIC_EXAMPLE" ]; then
    echo ""
    echo "========================================"
    echo "NOT FOUND PROJECTS PATHS"
    echo "========================================"
    for not_found_path in "${not_found_projects[@]}"; do
        echo -e "\033[31m✗\033[0m $not_found_path"
    done
fi

echo "Processing complete."
