from typing import Optional, List
import threading
import time
import sys
import argparse
from utils import *
from rapidfuzz import process


def process_umfeld_project(_project_name:str, _umfeld_lst: List, _original_lst: List, _pairs: dict, _props: dict, original: bool = False, verbose: bool = True) -> Optional[str]:
    # 1. build run
    # Always use Umfeld project path for output location
    umfeld_path = next((p for p in _umfeld_lst if _project_name in p), None)
    if umfeld_path is None:
        print(f"{Fore.RED}No Umfeld project path found for {_project_name}.{Style.RESET_ALL}")
        return None
    umfeld_path = os.path.abspath(umfeld_path)
    print(f"{Fore.CYAN}umfeld_path: {umfeld_path}{Style.RESET_ALL}")
    pid = None
    if original:
        # Find the original project path for running, but output stays in Umfeld dir
        orig_proj_name = _pairs.get(_project_name)
        orig_path = next((p for p in _original_lst if orig_proj_name in p), None)
        if orig_path is None:
            print(f"{Fore.RED}No original project path found for {orig_proj_name}.{Style.RESET_ALL}")
            return None
        orig_path = os.path.abspath(orig_path)
        pid = build_and_run_original_processing_example(orig_path, True)
    else:
        pid = build_and_run_umfeld_processing_example(umfeld_path, True, verbose=verbose)
    
    if pid is None:
        print(f"{Fore.YELLOW}Skipping project due to build/run failure: {_project_name}{Style.RESET_ALL}")
        return None

    time.sleep(1.5)

    # 2. check test_props.json
    IS_INTERACTIVE = False
    if _project_name in _props:
        IS_INTERACTIVE = is_interactive(_props, _project_name)

    # 3. prepare simulation
    mouse_actions = []
    keys = []
    # Use client area for accurate recording region
    window_title = _pairs[_project_name] if original else _project_name
    x, y, w, h = get_client_area(pid, window_title, is_java_process=original)
    if w == 0 or h == 0:
        print(f"{Fore.RED}Could not find window for {window_title} with PID {pid}. Skipping.{Style.RESET_ALL}")
        kill_process(pid)
        return None
    print(f"{Fore.BLUE}Client area for {window_title}: {x},{y},{w},{h}.{Style.RESET_ALL}")

    if IS_INTERACTIVE:
        if _props[_project_name][0] == "mouse":
            include_click = "press" in _props[_project_name]
            include_drag = "drag" in _props[_project_name]
            mouse_actions = generate_random_mouse_actions(x, y, w, h, 10, include_click=include_click, include_drag=include_drag, seed=_project_name)
        elif _props[_project_name][0] == "keyboard":
            keys = _props[_project_name][1]

    # 4. start recording
    video_path = None
    record_thread = None
    if IS_INTERACTIVE:
        if original:
            video_path = os.path.join(umfeld_path, f"processing_{_pairs[_project_name]}.mp4")
        else:
            video_path = os.path.join(umfeld_path, f"umfeld_{_project_name}.mp4")
        print(f"{Fore.CYAN}video_path: {video_path}{Style.RESET_ALL}")
        record_thread = record_window_video_async(
            (x,y,w,h), 
            duration=5, 
            output_path=video_path,
            verbose=verbose
        )   
    else:
        # For non-interactive projects, take a screenshot instead of recording video
        if original:
            video_path = os.path.join(umfeld_path, f"processing_{_pairs[_project_name]}.png")
        else:
            video_path = os.path.join(umfeld_path, f"umfeld_{_project_name}.png")
        print(f"{Fore.CYAN}video_path: {video_path}{Style.RESET_ALL}")
        capture_window_image(
            (x, y, w, h), 
            output_path=video_path,
            verbose=verbose
        )

    # 5. run simulation
    if IS_INTERACTIVE:
        print(f"{Fore.GREEN}Running simulation for {_project_name}.{Style.RESET_ALL}-{IS_INTERACTIVE}")
        try:
            if _props[_project_name][0] == "mouse":
                # Pass all mouse actions (move, press, release) for drag/click support
                run_mouse_action_sequence((x, y, w, h), mouse_actions, total_duration=5)
            elif _props[_project_name][0] == "keyboard":
                # Ensure keys is a string, not a list
                if isinstance(keys, list):
                    keys_str = ''.join(keys)
                else:
                    keys_str = str(keys)
                send_keys_to_window(window_title, keys_str, delay=100, total_duration=5, window_rect=(x, y, w, h))
        except Exception as e:
            print(f"{Fore.RED}Interaction failed for {_project_name}: {e}{Style.RESET_ALL}")
            kill_process(pid)
            return None

    if IS_INTERACTIVE and record_thread is not None:
        record_thread.join()

    # 6. pad video/image
    if not video_path or not os.path.exists(video_path):
        print(f"{Fore.RED}Video/image file not found after recording: {video_path}. Skipping.{Style.RESET_ALL}")
        kill_process(pid)
        return None

    if original:
        add_bottom_text_padding(video_path, "Processing", padding=50, verbose=verbose)
    else:
        add_bottom_text_padding(video_path, "Umfeld", padding=50, verbose=verbose)

    # 7. kill process
    kill_process(pid)
    
    return video_path




##==============================================================================
##==============================================================================
if __name__ == "__main__":
    

    # Initial blank lines for status output
    print("\n\n\n")

    # Argument parsing
    parser = argparse.ArgumentParser(description="Run Umfeld and Processing examples.")
    parser.add_argument("--umfeld_example_dir", type=str, default="../Processing/",
                        help="Root directory for Umfeld Processing examples.")
    parser.add_argument("--processing_example_dir", type=str, default="/opt/processing/modes/java/examples/",
                        help="Root directory for original Processing examples.")
    parser.add_argument("--project", type=str, help="Run a single project by fuzzy matching its name.")
    args = parser.parse_args()

    umfeld_processing_example_root = args.umfeld_example_dir
    original_processing_example_root = args.processing_example_dir

    print(f"Umfeld Example Directory: {umfeld_processing_example_root}")
    print(f"Processing Example Directory: {original_processing_example_root}")

    if not args.project:
        while True:
            response = input("Do you want to proceed with these directories? (y/n): ").lower()
            if response == 'y':
                break
            elif response == 'n':
                print("Exiting program.")
                sys.exit(0)
            else:
                print("Invalid input. Please enter 'y' or 'n'.")

    # global variables
    umfeld_lst = get_all_umfeld_processing_examples(umfeld_processing_example_root)
    original_lst = get_all_original_processing_examples(original_processing_example_root)
    pairs = fuzzy_match_pairs(umfeld_lst, original_lst)
    props = load_test_props()

    VERBOSE = False

    projects_to_run = []
    if args.project:
        # Find the best match for the given project name
        project_name = args.project
        choices = [os.path.basename(p) for p in umfeld_lst]
        result = process.extractOne(project_name, choices)
        if result:
            best_match, score, idx = result
            print(f"Found project: {best_match} (score: {score})")
            projects_to_run.append(umfeld_lst[idx])
        else:
            print(f"{Fore.RED}No matching project found for '{project_name}'.{Style.RESET_ALL}")
            sys.exit(1)
    else:
        projects_to_run = umfeld_lst

    for u in projects_to_run:
        
        _umfeld_project_name = os.path.basename(u).split('.')[0]  # Extract project name from path

        print(f"{Fore.GREEN}Processing project: {_umfeld_project_name}{Style.RESET_ALL}")

        umfeld_video = process_umfeld_project(_umfeld_project_name, umfeld_lst, original_lst, pairs, props, verbose=VERBOSE)
        if not umfeld_video:
            print(f"{Fore.YELLOW}Skipping project {_umfeld_project_name} due to Umfeld run failure.{Style.RESET_ALL}\n\n")
            continue

        processing_video = process_umfeld_project(_umfeld_project_name, umfeld_lst, original_lst, pairs, props, original=True, verbose=VERBOSE)
        if not processing_video:
            print(f"{Fore.YELLOW}Skipping concatenation for {_umfeld_project_name} due to Processing run failure.{Style.RESET_ALL}\n\n")
            continue

        # 8. Concatenate the two videos/images if both exist
        if os.path.exists(umfeld_video) and os.path.exists(processing_video):
            is_image = any(umfeld_video.lower().endswith(ext) for ext in ['.png', '.jpg', '.jpeg', '.bmp'])
            
            if is_image:
                final_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "test_video_final.png")
                concat_images(
                    processing_video,
                    umfeld_video,
                    output_path=final_path
                )
            else:
                final_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "test_video_final.mp4")
                concat_videos_ffmpeg_filter(
                    processing_video,
                    umfeld_video,
                    output_path=final_path,
                    verbose=VERBOSE
                )
        else:
            print(
                f"{Fore.RED}One or both video/image files are missing, skipping concatenation.{Style.RESET_ALL}"
            )
        print("\n\n")
    
    
    
    print(f"{Fore.GREEN}Main program exiting.{Style.RESET_ALL}")
