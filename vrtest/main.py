from typing import Optional, List
import time
import sys
import argparse
import os
from rapidfuzz import process
from datetime import datetime
from colorama import Fore, Style

# Import the centralized logging and all other utils
from utils import *

def process_umfeld_project(
    _project_name: str, 
    _umfeld_lst: List[str], 
    _original_lst: List[str], 
    _pairs: dict, 
    _props: dict, 
    original: bool = False
) -> Optional[str]:
    """
    Processes a single project (either Umfeld or original Processing).
    Handles building, running, interaction, and recording.
    """
    project_start_time = time.time()
    project_type = "Processing" if original else "Umfeld"
    component_prefix = f"{project_type}"

    # Master Umfeld path is always needed for output location
    umfeld_path = next((p for p in _umfeld_lst if os.path.basename(p) == _project_name), None)
    if not umfeld_path:
        log_message(f"[{_project_name}] Master Umfeld path not found in list.", component=component_prefix, level="ERROR", color=Fore.RED)
        return None
    umfeld_path = os.path.abspath(umfeld_path)

    pid = None
    project_path = None
    window_title = None

    with time_logger("build and run", f"{project_type}-Build", _project_name):
        if original:
            orig_proj_name = _pairs.get(_project_name)
            if not orig_proj_name:
                log_message(f"[{_project_name}] No matching Processing project found in pairs dict.", component=component_prefix, level="WARNING", color=Fore.YELLOW)
                return None
            
            project_path = next((p for p in _original_lst if os.path.basename(p) == orig_proj_name), None)
            if not project_path:
                log_message(f"[{orig_proj_name}] Path not found in original list.", component=component_prefix, level="ERROR", color=Fore.RED)
                return None
            
            project_path = os.path.abspath(project_path)
            pid = build_and_run_original_processing_example(project_path, True)
            window_title = orig_proj_name
        else:
            project_path = umfeld_path
            pid = build_and_run_umfeld_processing_example(project_path, True)
            window_title = _project_name

    if pid is None:
        # The build/run function already logs the specific failure
        return None

    win_id = None
    with time_logger("window detection", "Window", _project_name):
        log_message("Waiting 3.0s for application window to initialize...", component=component_prefix, color=Fore.BLUE)
        time.sleep(3.0)

        # Get window geometry and the specific window ID
        x, y, w, h, win_id = get_client_area(pid, window_title, is_java_process=original)
        if w == 0 or h == 0 or not win_id:
            log_message(f"Could not find window for '{window_title}' (PID: {pid}). Skipping.", component=component_prefix, level="ERROR", color=Fore.RED)
            kill_process(pid)
            return None
        log_message(f"Found window for '{window_title}' (ID: {win_id}): x={x}, y={y}, w={w}, h={h}", component=component_prefix, color=Fore.BLUE)

    # Prepare for interaction if any
    is_interactive_flag = is_interactive(_props, _project_name)
    
    # animation 타입인지 확인 (영상 녹화하지만 인터랙션 없음)
    is_animation = _project_name in _props and _props[_project_name] and _props[_project_name][0] == "animation"
    
    # Determine output path (always in the Umfeld project directory)
    output_name = f"processing_{_pairs.get(_project_name)}" if original else f"umfeld_{_project_name}"
    output_ext = ".mp4" if (is_interactive_flag or is_animation) else ".png"
    output_path = os.path.join(umfeld_path, output_name + output_ext)

    # Start recording or take screenshot
    record_thread = None
    with time_logger("capture/recording", "Capture", _project_name):
        if is_interactive_flag or is_animation:
            log_message(f"Starting video recording to: {output_path}", component=f"{component_prefix}-Record", color=Fore.CYAN)
            record_thread = record_window_video_async((x, y, w, h), duration=5, output_path=output_path)
        else:
            log_message(f"Capturing screenshot to: {output_path}", component=f"{component_prefix}-Capture", color=Fore.CYAN)
            capture_window_image((x, y, w, h), output_path=output_path)

    # Run simulation if interactive
    if is_interactive_flag:
        with time_logger("interaction", "Interact", _project_name):
            interaction_type = _props[_project_name][0]
            log_message(f"Running '{interaction_type}' simulation.", component=f"{component_prefix}-Interact", color=Fore.GREEN)
            try:
                if interaction_type == "mouse":
                    mouse_actions = generate_random_mouse_actions(w, h, 10, "press" in _props[_project_name], "drag" in _props[_project_name], seed=_project_name)
                    run_mouse_action_sequence((x, y, w, h), mouse_actions, total_duration=5)
                elif interaction_type == "keyboard":
                    keys = ''.join(_props[_project_name][1])
                    # Pass the exact window ID to avoid ambiguity
                    send_keys_to_window(win_id, keys, total_duration=5, window_rect=(x, y, w, h))
            except Exception as e:
                log_message(f"Interaction failed: {e}", component=f"{component_prefix}-Interact", level="ERROR", color=Fore.RED)
                kill_process(pid)
                if record_thread: record_thread.join() # Ensure recorder finishes
                return None

    if record_thread:
        record_thread.join()

    # Post-processing (padding) and cleanup
    if not os.path.exists(output_path):
        log_message(f"Output file not found after recording: {output_path}. Skipping.", component=component_prefix, level="ERROR", color=Fore.RED)
        kill_process(pid)
        return None

    with time_logger("post-processing", f"{component_prefix}-ffmpeg", _project_name):
        log_message(f"Adding '{project_type}' label to output file.", component=f"{component_prefix}-ffmpeg", color=Fore.CYAN)
        add_bottom_text_padding(output_path, project_type)
    
    kill_process(pid)
    
    total_duration = time.time() - project_start_time
    log_message(f"Total processing time: {total_duration:.2f}s",
                component=f"{project_type}-Total", color=Fore.MAGENTA)
    return output_path

##==============================================================================
if __name__ == "__main__":
    main_start_time = time.time()
    parser = argparse.ArgumentParser(description="Run Umfeld and Processing examples.")
    parser.add_argument("--umfeld_example_dir", type=str, default="../Processing/", help="Root directory for Umfeld Processing examples.")
    parser.add_argument("--processing_example_dir", type=str, default="/opt/processing/modes/java/examples/", help="Root directory for original Processing examples.")
    parser.add_argument("--project", type=str, help="Run a single project by fuzzy matching its name.")
    parser.add_argument("--category", type=str, help="Run projects from a specific category (e.g., 'Basics/Input', 'Basics/Math').")
    args = parser.parse_args()

    # Check for mutually exclusive options
    if args.project and args.category:
        print(f"{Fore.RED}Error: --project and --category options cannot be used together. Please use only one.{Style.RESET_ALL}")
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
    pairs = fuzzy_match_pairs(umfeld_lst, original_lst, args.umfeld_example_dir, args.processing_example_dir)

    projects_to_run = []
    if args.project:
        def normalize_name(name):
            return name.replace('_', '').replace(' ', '').lower()

        choices = [os.path.basename(p) for p in umfeld_lst]
        normalized_input = normalize_name(args.project)

        # Filter choices by the length of their normalized names
        length_matched_choices = [
            c for c in choices if len(normalize_name(c)) == len(normalized_input)
        ]

        best_match = None
        # If we have candidates of the same length, perform fuzzy matching only on them
        if length_matched_choices:
            log_message(f"Found {len(length_matched_choices)} same-length candidate(s) for '{args.project}'.", component="Init")
            # Use a dictionary to match against normalized names but retrieve the original
            choices_dict = {name: normalize_name(name) for name in length_matched_choices}
            result = process.extractOne(normalized_input, choices_dict)
            if result:
                # For dicts, result is (value, score, key)
                _, _, best_match = result
        
        # If no same-length candidates were found, fall back to fuzzy matching all projects
        if not best_match:
            log_message(f"No same-length candidates. Falling back to fuzzy matching all {len(choices)} projects.", component="Init", level="WARNING", color=Fore.YELLOW)
            result = process.extractOne(args.project, choices)
            if result:
                # For lists, result is (choice, score, index)
                best_match, _, _ = result
        
        # If a project was selected, add its full path to the run list
        if best_match:
            log_message(f"Selected project to run: '{best_match}'", component="Init", color=Fore.CYAN)
            try:
                idx = choices.index(best_match)
                projects_to_run.append(umfeld_lst[idx])
            except ValueError:
                # This should not happen if best_match came from choices
                log_message(f"Internal error: Could not find path for selected project '{best_match}'.", component="Init", level="ERROR", color=Fore.RED)
                sys.exit(1)
        else:
            log_message(f"No matching project found for '{args.project}'. Exiting.", component="Init", level="ERROR", color=Fore.RED)
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

    else:
        projects_to_run = umfeld_lst

    log_message(f"Found {len(umfeld_lst)} Umfeld and {len(original_lst)} Processing projects. Matched {len(pairs)} pairs.", component="Init")
    log_message(f"Starting processing for {len(projects_to_run)} projects.", component="Init", color=Fore.GREEN)

    for u_path in projects_to_run:
        umfeld_project_name = os.path.basename(u_path)
        log_message(f"Processing Umfeld project: '{umfeld_project_name}'", component="Main", color=Style.BRIGHT)

        matched_name = pairs.get(umfeld_project_name)
        if matched_name:
            log_message(f"Matched with Processing project: '{matched_name}'", component="Match", color=Fore.CYAN)
        else:
            log_message(f"No match found. Skipping Processing part.", component="Match", level="WARNING", color=Fore.YELLOW)

        # Run Umfeld version
        umfeld_video = process_umfeld_project(umfeld_project_name, umfeld_lst, original_lst, pairs, props)
        
        # Run Processing version
        processing_video = process_umfeld_project(umfeld_project_name, umfeld_lst, original_lst, pairs, props, original=True)

        # Concatenate results
        if umfeld_video and processing_video:
            is_image = umfeld_video.lower().endswith(('.png', '.jpg', '.jpeg'))
            final_path = os.path.join(os.path.dirname(umfeld_video), f"comparison-{umfeld_project_name}{'.png' if is_image else '.mp4'}")
            
            with time_logger("concatenation", "Concat", umfeld_project_name):
                log_message(f"Concatenating results to: {final_path}", component="Concat", color=Fore.GREEN)
                if is_image:
                    concat_images(processing_video, umfeld_video, final_path)
                else:
                    concat_videos_ffmpeg_filter(processing_video, umfeld_video, final_path)
        else:
            log_message("One or both outputs failed, skipping concatenation.", component="Concat", level="WARNING", color=Fore.YELLOW)
            
        log_message(f"Finished processing '{umfeld_project_name}'.", component="Main", color=Style.BRIGHT)
        print("-" * 80)

    main_end_time = time.time()
    total_main_duration = main_end_time - main_start_time
    log_message(f"Total script execution time: {total_main_duration:.2f}s", component="Init", color=Fore.GREEN)
    log_message("--- Test Run Finished ---", component="Init", color=Fore.GREEN)
