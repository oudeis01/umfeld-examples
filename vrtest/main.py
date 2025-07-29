from typing import Optional, List
import threading
import time
import sys
import argparse
from utils import *


def process_umfeld_project(_project_name:str, _umfeld_lst: List, _original_lst: List, _pairs: dict, _props: dict, original: bool = False, verbose: bool = True) -> Optional[str]:
    # 1. build run
    # Always use Umfeld project path for output location
    umfeld_path = next((p for p in _umfeld_lst if _project_name in p), None)
    if umfeld_path is None:
        print(f"{Fore.RED}No Umfeld project path found for {_project_name}.{Style.RESET_ALL}")
        return None
    umfeld_path = os.path.abspath(umfeld_path)
    print(f"{Fore.CYAN}umfeld_path: {umfeld_path}{Style.RESET_ALL}")
    if original:
        # Find the original project path for running, but output stays in Umfeld dir
        orig_proj_name = _pairs.get(_project_name)
        orig_path = next((p for p in _original_lst if orig_proj_name in p), None)
        if orig_path is None:
            print(f"{Fore.RED}No original project path found for {orig_proj_name}.{Style.RESET_ALL}")
            return None
        orig_path = os.path.abspath(orig_path)
        pid = build_and_run_original_processing_example(orig_path, True)
        time.sleep(1.5)
    else:
        pid = build_and_run_umfeld_processing_example(umfeld_path, True, verbose=verbose)
        time.sleep(1.5)

    # 2. check test_props.json
    IS_INTERACTIVE = False
    if _project_name in _props:
        IS_INTERACTIVE = is_interactive(_props, _project_name)

    # 3. prepare simulation
    mouse_actions = []
    keys = []
    # Use client area for accurate recording region
    if original:
        x, y, w, h = get_client_area_by_title(_pairs[_project_name])
    else:
        x, y, w, h = get_client_area_by_title(_project_name)
    print(f"{Fore.BLUE}Client area for {_pairs[_project_name] if original else _project_name}: {x},{y},{w},{h}.{Style.RESET_ALL}")

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
        if _props[_project_name][0] == "mouse":
            # Pass all mouse actions (move, press, release) for drag/click support
            run_mouse_action_sequence((x, y, w, h), mouse_actions, total_duration=5)
        elif _props[_project_name][0] == "keyboard":
            # Ensure keys is a string, not a list
            if isinstance(keys, list):
                keys_str = ''.join(keys)
            else:
                keys_str = str(keys)
            if original:
                send_keys_to_window(_pairs[_project_name], keys_str, delay=100, total_duration=5, window_rect=(x, y, w, h))
            else:
                send_keys_to_window(_project_name, keys_str, delay=100, total_duration=5, window_rect=(x, y, w, h))

    if IS_INTERACTIVE and record_thread is not None:
        record_thread.join()

    # 6. pad video/image
    if video_path and os.path.exists(video_path):
        if original:
            add_bottom_text_padding(video_path, "Processing", padding=50, verbose=verbose)
        else:
            add_bottom_text_padding(video_path, "Umfeld", padding=50, verbose=verbose)
    else:
        print(f"{Fore.RED}Video/image file not found: {video_path}{Style.RESET_ALL}")
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
    args = parser.parse_args()

    umfeld_processing_example_root = args.umfeld_example_dir
    original_processing_example_root = args.processing_example_dir

    print(f"Umfeld Example Directory: {umfeld_processing_example_root}")
    print(f"Processing Example Directory: {original_processing_example_root}")

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

    for u in umfeld_lst:
        
        _umfeld_project_name = os.path.basename(u).split('.')[0]  # Extract project name from path

        print(f"{Fore.GREEN}Processing project: {_umfeld_project_name}{Style.RESET_ALL}")

        umfeld_video = process_umfeld_project(_umfeld_project_name, umfeld_lst, original_lst, pairs, props, verbose=VERBOSE)

        processing_video = process_umfeld_project(_umfeld_project_name, umfeld_lst, original_lst, pairs, props, original=True, verbose=VERBOSE)

        # 8. Concatenate the two videos/images if both exist
        if umfeld_video and processing_video and os.path.exists(umfeld_video) and os.path.exists(processing_video):
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
