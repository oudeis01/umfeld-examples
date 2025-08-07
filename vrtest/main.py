from typing import Optional, List
import time
import sys
import argparse
import os
import subprocess
from rapidfuzz import process
from datetime import datetime
from colorama import Fore, Style

# Import the centralized logging and all other utils
from utils import *

def process_project(
    project_name: str, 
    umfeld_lst: List[str], 
    original_lst: List[str], 
    props: dict, 
    original: bool = False,
    clean_build: bool = False
) -> Optional[str]:
    """
    Process a single project (either Umfeld or original Processing).
    Handle building, running, interaction, and recording.
    """
    project_start_time = time.time()
    project_type = "Processing" if original else "Umfeld"
    component_prefix = project_type

    # Find project paths - project names are now identical between frameworks
    umfeld_path = next((p for p in umfeld_lst if os.path.basename(p) == project_name), None)
    if not umfeld_path:
        log_message(f"Umfeld project '{project_name}' not found", component=component_prefix, level="ERROR", color=Fore.RED)
        return None
    umfeld_path = os.path.abspath(umfeld_path)

    pid = None
    project_path = None
    window_title = project_name

    with time_logger("build and run", f"{project_type}-Build", project_name):
        if original:
            project_path = next((p for p in original_lst if os.path.basename(p) == project_name), None)
            if not project_path:
                log_message(f"Processing project '{project_name}' not found", component=component_prefix, level="ERROR", color=Fore.RED)
                return None
            
            project_path = os.path.abspath(project_path)
            pid = build_and_run_original_processing_example(project_path, True)
        else:
            project_path = umfeld_path
            pid = build_and_run_umfeld_processing_example(project_path, True, clean_build=clean_build)

    if pid is None:
        return None

    win_id = None
    with time_logger("window detection", "Window", project_name):
        log_message("Waiting 3.0s for application window to initialize...", component=component_prefix, color=Fore.BLUE)
        time.sleep(3.0)

        # Get window geometry and specific window ID
        x, y, w, h, win_id = get_client_area(pid, window_title, is_java_process=original)
        if w == 0 or h == 0 or not win_id:
            error_msg = f"WINDOW_NOT_FOUND: Could not find window for '{window_title}' (PID: {pid}) - Application may not have started properly or window creation failed"
            log_message(error_msg, component=component_prefix, level="ERROR", color=Fore.RED)
            kill_process(pid)
            return None
        log_message(f"Found window for '{window_title}' (ID: {win_id}): x={x}, y={y}, w={w}, h={h}", component=component_prefix, color=Fore.BLUE)

    # Check interaction requirements
    project_props = is_interactive(props, project_name)
    is_animation = project_props and project_props[0] == "animation"
    is_interactive_flag = bool(project_props) and not is_animation
    
    # Determine output path (in comparison folder in vrtest directory)
    comparison_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "comparison")
    os.makedirs(comparison_dir, exist_ok=True)
    
    output_name = f"processing_{project_name}" if original else f"umfeld_{project_name}"
    output_ext = ".mp4" if (is_interactive_flag or is_animation) else ".png"
    output_path = os.path.join(comparison_dir, output_name + output_ext)

    # Start recording or take screenshot
    record_thread = None
    with time_logger("capture/recording", "Capture", project_name):
        if is_interactive_flag or is_animation:
            log_message(f"Starting video recording to: {output_path}", component=f"{component_prefix}-Record", color=Fore.CYAN)
            record_thread = record_window_video_async((x, y, w, h), duration=5, output_path=output_path)
        else:
            log_message(f"Capturing screenshot to: {output_path}", component=f"{component_prefix}-Capture", color=Fore.CYAN)
            capture_window_image((x, y, w, h), output_path=output_path)

    # Run interaction simulation if needed
    if is_interactive_flag:
        with time_logger("interaction", "Interact", project_name):
            interaction_type = project_props[0]
            log_message(f"Running '{interaction_type}' simulation", component=f"{component_prefix}-Interact", color=Fore.GREEN)
            try:
                if interaction_type == "mouse":
                    mouse_actions = generate_random_mouse_actions(0, 0, w, h, 10, "press" in project_props, "drag" in project_props, seed=project_name)
                    run_mouse_action_sequence((x, y, w, h), mouse_actions, total_duration=5)
                elif interaction_type == "keyboard":
                    _handle_keyboard_interaction(x, y, w, h, project_props[1:], component_prefix, win_id)
            except Exception as e:
                log_message(f"Interaction failed: {e}", component=f"{component_prefix}-Interact", level="ERROR", color=Fore.RED)
                kill_process(pid)
                if record_thread: 
                    record_thread.join()
                return None

    if record_thread:
        record_thread.join()

    # Verify output file exists
    if not os.path.exists(output_path):
        log_message(f"Output file not found: {output_path}", component=component_prefix, level="ERROR", color=Fore.RED)
        kill_process(pid)
        return None

    # Add project type label to output
    with time_logger("post-processing", f"{component_prefix}-ffmpeg", project_name):
        log_message(f"Adding '{project_type}' label to output file", component=f"{component_prefix}-ffmpeg", color=Fore.CYAN)
        add_bottom_text_padding(output_path, project_type)
    
    kill_process(pid)
    
    total_duration = time.time() - project_start_time
    log_message(f"Total processing time: {total_duration:.2f}s", component=f"{project_type}-Total", color=Fore.MAGENTA)
    return output_path

def _handle_keyboard_interaction(x: int, y: int, w: int, h: int, key_inputs: List[str], component_prefix: str, win_id: str) -> None:
    """
    Handle keyboard interaction by focusing window and sending key inputs using xdotool.
    """
    try:
        # Prepare the key sequence for xdotool
        has_arrow_keys = any(key in ["UP", "DOWN"] for key in key_inputs)
        
        if has_arrow_keys:
            # Handle arrow keys with timing constraints
            max_keys = min(len(key_inputs), int(5.0 / 0.3))
            limited_keys = key_inputs[:max_keys]
            
            # Convert to xdotool format
            xdotool_keys = []
            for key_input in limited_keys:
                if key_input == "UP":
                    xdotool_keys.append("Up")
                elif key_input == "DOWN":
                    xdotool_keys.append("Down") 
                else:
                    # For text input, we need to escape special characters
                    escaped_key = key_input.replace("'", "''")
                    xdotool_keys.append(f"type '{escaped_key}'")
            
            # Calculate delay to distribute keys evenly over 5 seconds
            if len(xdotool_keys) > 1:
                delay_between_keys = 5.0 / len(xdotool_keys)
            else:
                delay_between_keys = 0
            
            # Send keys one by one with calculated delays using specific window ID
            for i, key_cmd in enumerate(xdotool_keys):
                if key_cmd.startswith("type"):
                    # For typing, use xdotool with window ID
                    text_to_type = key_cmd.split("'")[1]
                    try:
                        subprocess.run(["xdotool", "windowactivate", "--sync", win_id, "type", text_to_type], check=True)
                    except subprocess.CalledProcessError:
                        log_message(f"Failed to type text: {text_to_type}", component=component_prefix, level="WARNING", color=Fore.YELLOW)
                else:
                    # For special keys, use xdotool with window ID
                    try:
                        subprocess.run(["xdotool", "windowactivate", "--sync", win_id, "key", key_cmd], check=True)
                    except subprocess.CalledProcessError:
                        log_message(f"Failed to send key: {key_cmd}", component=component_prefix, level="WARNING", color=Fore.YELLOW)
                
                # Wait calculated delay before next key (except for last key)
                if i < len(xdotool_keys) - 1:
                    time.sleep(delay_between_keys)
        else:
            # Regular keyboard input - use xdotool with delay option for better handling
            all_text = "".join(key_inputs)
            
            # Calculate delay in milliseconds to distribute characters evenly over 5 seconds
            if len(all_text) > 1:
                delay_ms = int((5.0 * 1000) / len(all_text))
            else:
                delay_ms = 0
            
            # Use xdotool with --delay option for more reliable character input
            try:
                if delay_ms > 0:
                    subprocess.run(["xdotool", "windowactivate", "--sync", win_id, "type", "--delay", str(delay_ms), all_text], check=True)
                else:
                    subprocess.run(["xdotool", "windowactivate", "--sync", win_id, "type", all_text], check=True)
            except subprocess.CalledProcessError:
                log_message(f"Failed to send keyboard input to window", component=component_prefix, level="WARNING", color=Fore.YELLOW)
                
    except Exception as e:
        log_message(f"Keyboard interaction failed: {e}", component=f"{component_prefix}-Interact", level="ERROR", color=Fore.RED)

##==============================================================================
if __name__ == "__main__":
    main_start_time = time.time()
    parser = argparse.ArgumentParser(description="Run Umfeld and Processing examples.")
    parser.add_argument("--umfeld_example_dir", type=str, default="../Processing/", help="Root directory for Umfeld Processing examples.")
    parser.add_argument("--processing_example_dir", type=str, default="/opt/processing/modes/java/examples/", help="Root directory for original Processing examples.")
    parser.add_argument("--project", type=str, help="Run a single project by fuzzy matching its name.")
    parser.add_argument("--category", type=str, help="Run projects from a specific category (e.g., 'Basics/Input', 'Basics/Math').")
    parser.add_argument("--failed-list", type=str, help="Path to text file containing failed project paths (one per line) to re-run only those projects.")
    args = parser.parse_args()

    # Check for mutually exclusive options
    exclusive_options = [args.project, args.category, args.failed_list]
    if sum(bool(opt) for opt in exclusive_options) > 1:
        print(f"{Fore.RED}Error: --project, --category, and --failed-list options cannot be used together. Please use only one.{Style.RESET_ALL}")
        sys.exit(1)

    # Setup centralized logging
    log_file_name = f"run_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    log_file_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), log_file_name)
    setup_logging(log_file_path)

    log_message("--- Test Run Started ---", component="Init", color=Fore.GREEN)
    log_message(f"Umfeld Example Dir: {os.path.abspath(args.umfeld_example_dir)}", component="Init")
    log_message(f"Processing Example Dir: {os.path.abspath(args.processing_example_dir)}", component="Init")

    # Load all projects and properties
    umfeld_lst = get_all_umfeld_processing_examples(args.umfeld_example_dir)
    original_lst = get_all_original_processing_examples(args.processing_example_dir)
    props = load_test_props()

    projects_to_run = []
    if args.project:
        # Simple exact match since project names are now standardized
        choices = [os.path.basename(p) for p in umfeld_lst]
        
        if args.project in choices:
            best_match = args.project
        else:
            # Fall back to fuzzy matching if exact match fails
            result = process.extractOne(args.project, choices)
            best_match = result[0] if result and result[1] > 70 else None
        
        if best_match:
            log_message(f"Selected project: '{best_match}'", component="Init", color=Fore.CYAN)
            idx = choices.index(best_match)
            projects_to_run.append(umfeld_lst[idx])
        else:
            log_message(f"No matching project found for '{args.project}'", component="Init", level="ERROR", color=Fore.RED)
            sys.exit(1)

    elif args.category:
        # Filter projects by category
        filtered_projects = filter_projects_by_category(umfeld_lst, args.category, args.umfeld_example_dir)
        
        if filtered_projects:
            log_message(f"Found {len(filtered_projects)} projects in category '{args.category}':", component="Init", color=Fore.CYAN)
            for proj in filtered_projects:
                log_message(f"  - {os.path.basename(proj)}", component="Init", color=Fore.CYAN)
            projects_to_run = filtered_projects
        else:
            log_message(f"No projects found in category '{args.category}'. Exiting.", component="Init", level="ERROR", color=Fore.RED)
            sys.exit(1)

    elif args.failed_list:
        # Load failed projects from file
        if not os.path.exists(args.failed_list):
            log_message(f"Failed projects file not found: {args.failed_list}", component="Init", level="ERROR", color=Fore.RED)
            sys.exit(1)
        
        try:
            with open(args.failed_list, 'r', encoding='utf-8') as f:
                failed_paths = [line.strip() for line in f if line.strip()]
            
            # Filter umfeld_lst to only include projects from the failed list
            failed_project_names = [os.path.basename(path) for path in failed_paths]
            projects_to_run = [p for p in umfeld_lst if os.path.basename(p) in failed_project_names]
            
            if projects_to_run:
                log_message(f"Loaded {len(failed_paths)} failed project paths from '{args.failed_list}':", component="Init", color=Fore.CYAN)
                log_message(f"Found {len(projects_to_run)} matching projects to re-run:", component="Init", color=Fore.CYAN)
                for proj in projects_to_run:
                    log_message(f"  - {os.path.basename(proj)}", component="Init", color=Fore.CYAN)
            else:
                log_message(f"No matching projects found from failed list. Exiting.", component="Init", level="ERROR", color=Fore.RED)
                sys.exit(1)
                
        except Exception as e:
            log_message(f"Error reading failed projects file '{args.failed_list}': {e}", component="Init", level="ERROR", color=Fore.RED)
            sys.exit(1)

    else:
        # Sort projects alphabetically by project name for consistent processing order
        projects_to_run = sorted(umfeld_lst, key=lambda p: os.path.basename(p).lower())

    log_message(f"Found {len(umfeld_lst)} Umfeld and {len(original_lst)} Processing projects", component="Init")
    log_message(f"Starting processing for {len(projects_to_run)} projects", component="Init", color=Fore.GREEN)

    for u_path in projects_to_run:
        project_name = os.path.basename(u_path)
        log_message(f"Processing project: '{project_name}'", component="Main", color=Style.BRIGHT)

        # Check if Processing version exists
        has_processing = any(os.path.basename(p) == project_name for p in original_lst)
        if not has_processing:
            log_message(f"No Processing version found for '{project_name}', skipping Processing part", component="Main", level="WARNING", color=Fore.YELLOW)

        # Run Umfeld version
        clean_build = bool(args.failed_list)  # Clean build only for failed-list retry
        umfeld_output = process_project(project_name, umfeld_lst, original_lst, props, clean_build=clean_build)
        
        # Run Processing version if available
        processing_output = None
        if has_processing:
            processing_output = process_project(project_name, umfeld_lst, original_lst, props, original=True, clean_build=clean_build)

        # Concatenate results if both succeeded
        if umfeld_output and processing_output:
            is_image = umfeld_output.lower().endswith(('.png', '.jpg', '.jpeg'))
            comparison_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "comparison")
            final_path = os.path.join(comparison_dir, f"comparison-{project_name}{'.png' if is_image else '.mp4'}")
            
            with time_logger("concatenation", "Concat", project_name):
                log_message(f"Concatenating results to: {final_path}", component="Concat", color=Fore.GREEN)
                try:
                    if is_image:
                        concat_images(processing_output, umfeld_output, final_path)
                    else:
                        concat_videos_ffmpeg_filter(processing_output, umfeld_output, final_path)
                    
                    # Verify concatenation was successful
                    if not os.path.exists(final_path):
                        error_msg = f"CONCAT_ERROR: Concatenation failed - output file not created: {final_path}"
                        log_message(error_msg, component="Concat", level="ERROR", color=Fore.RED)
                    else:
                        # Delete individual framework files after successful concatenation
                        try:
                            if os.path.exists(umfeld_output):
                                os.remove(umfeld_output)
                                log_message(f"Deleted individual Umfeld file: {os.path.basename(umfeld_output)}", component="Cleanup", color=Fore.CYAN)
                            if os.path.exists(processing_output):
                                os.remove(processing_output)
                                log_message(f"Deleted individual Processing file: {os.path.basename(processing_output)}", component="Cleanup", color=Fore.CYAN)
                        except Exception as e:
                            log_message(f"Warning: Could not delete individual files: {e}", component="Cleanup", level="WARNING", color=Fore.YELLOW)
                except Exception as e:
                    error_msg = f"CONCAT_ERROR: Failed to concatenate files for '{project_name}': {e}"
                    log_message(error_msg, component="Concat", level="ERROR", color=Fore.RED)
        else:
            # Log specific reasons for concatenation failure
            missing_files = []
            if not umfeld_output:
                missing_files.append("Umfeld")
            if not processing_output:
                missing_files.append("Processing")
            
            error_msg = f"CONCAT_SKIP: Cannot concatenate '{project_name}' - missing {' and '.join(missing_files)} output file(s)"
            log_message(error_msg, component="Concat", level="WARNING", color=Fore.YELLOW)
            
        log_message(f"Finished processing '{project_name}'", component="Main", color=Style.BRIGHT)
        print("-" * 80)

    main_end_time = time.time()
    total_main_duration = main_end_time - main_start_time
    log_message(f"Total script execution time: {total_main_duration:.2f}s", component="Init", color=Fore.GREEN)
    log_message("--- Test Run Finished ---", component="Init", color=Fore.GREEN)
