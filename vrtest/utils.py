import os
import sys
import subprocess
import time
import signal
import json
import logging
import random
import re
import threading
from contextlib import contextmanager
from datetime import datetime
from enum import Enum, auto
from typing import Optional, List, Tuple, Dict, Any

from colorama import Fore, Style
from PIL import Image
from pynput.mouse import Controller

def setup_logging(log_file_path: str) -> None:
    """
    Set up centralized logging to both console and file.
    """
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] %(message)s',
        handlers=[
            logging.FileHandler(log_file_path),
            logging.StreamHandler(sys.stdout)
        ]
    )

def log_message(message: str, level: str = "INFO", color: Optional[str] = None, component: Optional[str] = None) -> None:
    """
    Log message to both file and console with optional color formatting.
    """
    # Clean ANSI escape codes for file logging
    ansi_escape = re.compile(r'\x1b\[([0-9]{1,2}(;[0-9]{1,2})*)?[mGK]')
    clean_message = ansi_escape.sub('', message)

    # Log to file using logging module
    logger = logging.getLogger()
    if level == "ERROR":
        logger.error(clean_message)
    elif level == "WARNING":
        logger.warning(clean_message)
    elif level == "DEBUG":
        logger.debug(clean_message)
    else:
        logger.info(clean_message)

    # Print to console with optional color
    if color:
        print(f"{color}{message}{Style.RESET_ALL}")
    else:
        print(message)

@contextmanager
def time_logger(description: str, component: str, project_name: str):
    """
    Context manager for timing operations and logging results.
    """
    start_time = time.time()
    log_message(f"Starting {description} for {project_name}", component=component, color=Fore.BLUE)
    try:
        yield
    finally:
        duration = time.time() - start_time
        log_message(f"Completed {description} for {project_name} in {duration:.2f}s", 
                   component=component, color=Fore.GREEN)

class InteractiveType(Enum):
    """
    Enumeration of supported interaction types.
    """
    MOUSE_RANDOM = auto()
    MOUSE_CLICK = auto()
    MOUSE_DRAG = auto()
    KEYBOARD = auto()



def get_all_umfeld_processing_examples(umfeld_processing_example_root: str) -> List[str]:
    """
    Get all Umfeld processing example directories (excluding templates).
    Returns directories 3 levels deep from root.
    """
    result = []
    for root, dirs, files in os.walk(umfeld_processing_example_root):
        # Check if directory is at correct depth (3 levels from root)
        if root.count(os.sep) - umfeld_processing_example_root.count(os.sep) == 2:
            if "template" not in root.lower():
                result.append(root)
    return result

def get_cmake_project_name(project_path: str) -> Optional[str]:
    """
    Parse CMakeLists.txt to get the actual project name.
    Returns None if not found or parsing fails.
    """
    cmake_file = os.path.join(project_path, "CMakeLists.txt")
    if not os.path.exists(cmake_file):
        return None
    
    try:
        with open(cmake_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Look for project() declaration
        import re
        match = re.search(r'project\s*\(\s*([^)]+)\s*\)', content, re.IGNORECASE)
        if match:
            # Extract just the project name (first argument)
            project_line = match.group(1).strip()
            project_name = project_line.split()[0]  # Get first word
            return project_name
    except Exception as e:
        print(f"Warning: Could not parse CMakeLists.txt in {project_path}: {e}")
    
    return None

def get_all_original_processing_examples(original_processing_example_root: str) -> List[str]:
    """
    Get all original Processing example directories (excluding templates).
    Returns directories 3 levels deep from root.
    """
    result = []
    for root, dirs, files in os.walk(original_processing_example_root):
        # Check if directory is at correct depth (3 levels from root)
        if root.count(os.sep) - original_processing_example_root.count(os.sep) == 2:
            if "template" not in root.lower():
                result.append(root)
    return result

def build_and_run_umfeld_processing_example(example_path: str, nohup: bool, verbose: bool = True, clean_build: bool = False) -> Optional[int]:
    """
    Build and run Umfeld processing example using CMake and Make.
    Returns PID of started process or None if failed.
    """
    example_path = os.path.abspath(example_path)
    example_name = os.path.basename(example_path)
    build_dir = os.path.join(example_path, "build")
    
    # Get actual project name from CMakeLists.txt (may differ from folder name)
    project_name = get_cmake_project_name(example_path) or example_name
    
    # Prepare build commands with proper path quoting
    build_cmd = ["cmake", "-S", example_path, "-B", build_dir, "-DCMAKE_BUILD_TYPE=Debug"]
    make_cmd = ["make", "-C", build_dir, "-j32"]
    run_cmd = [os.path.join(build_dir, project_name)]
    
    cwd = os.getcwd()
    try:
        # Clean build directory if requested (for failed-list retries)
        if clean_build and os.path.exists(build_dir):
            import shutil
            shutil.rmtree(build_dir)
        
        if not os.path.exists(build_dir):
            os.makedirs(build_dir)
        
        # Configure output redirection
        stdout = None if verbose else subprocess.DEVNULL
        stderr = None if verbose else subprocess.DEVNULL
        
        # Build the project
        subprocess.run(build_cmd, check=True, stdout=stdout, stderr=stderr)
        subprocess.run(make_cmd, check=True, stdout=stdout, stderr=stderr)
        
        # Run the executable
        if nohup:
            with open(os.devnull, 'wb') as devnull:
                proc = subprocess.Popen(run_cmd, stdout=devnull, stderr=devnull, preexec_fn=os.setsid)
        else:
            proc = subprocess.Popen(run_cmd)
        
        pid = proc.pid
        print(f"{Fore.GREEN}Umfeld example '{example_name}' started with PID {pid}{Style.RESET_ALL}")
        return pid
        
    except subprocess.CalledProcessError as e:
        error_msg = f"COMPILE_ERROR: Failed to build Umfeld example '{example_name}': {e}"
        print(f"{Fore.RED}{error_msg}{Style.RESET_ALL}")
        log_message(error_msg, component="Umfeld-Build", level="ERROR", color=Fore.RED)
        return None
    except Exception as e:
        error_msg = f"BUILD_ERROR: Unexpected build error for '{example_name}': {e}"
        print(f"{Fore.RED}{error_msg}{Style.RESET_ALL}")
        log_message(error_msg, component="Umfeld-Build", level="ERROR", color=Fore.RED)
        return None
    finally:
        os.chdir(cwd)

def build_and_run_original_processing_example(example_path: str, nohup: bool) -> Optional[int]:
    """
    Build and run original Processing example using processing-java.
    Returns PID of actual Java process, not launcher script.
    """
    example_path = os.path.abspath(example_path)
    example_name = os.path.basename(example_path)
    cmd = ["processing-java", f"--sketch={example_path}", "--run"]
    
    script_proc = None
    cwd = os.getcwd()
    
    try:
        os.chdir(example_path)
        
        # Launch processing-java script
        if nohup:
            with open(os.devnull, 'wb') as devnull:
                script_proc = subprocess.Popen(cmd, stdout=devnull, stderr=devnull, preexec_fn=os.setsid)
        else:
            script_proc = subprocess.Popen(cmd)
        
        script_pid = script_proc.pid

        # Find actual Java process (child of launcher script)
        java_pid = _find_java_child_process(script_pid)
        
        if java_pid is None:
            error_msg = f"JAVA_PROCESS_ERROR: Could not find Java process for Processing example '{example_name}' (script PID {script_pid})"
            print(f"{Fore.RED}{error_msg}{Style.RESET_ALL}")
            log_message(error_msg, component="Processing-Build", level="ERROR", color=Fore.RED)
            if script_proc:
                kill_process(script_pid)
            return None
            
        print(f"{Fore.GREEN}Processing example '{example_name}' started with Java PID {java_pid}{Style.RESET_ALL}")
        return java_pid
        
    except Exception as e:
        error_msg = f"BUILD_ERROR: Failed to run Processing example '{example_name}': {e}"
        print(f"{Fore.RED}{error_msg}{Style.RESET_ALL}")
        log_message(error_msg, component="Processing-Build", level="ERROR", color=Fore.RED)
        if script_proc:
            kill_process(script_proc.pid)
        return None
    finally:
        if os.getcwd() != cwd:
            os.chdir(cwd)

def _find_java_child_process(script_pid: int) -> Optional[int]:
    """
    Find Java child process of processing-java launcher script.
    Retries for up to 3 seconds.
    """
    for _ in range(15):  # 15 * 0.2s = 3 seconds
        try:
            # Find child processes
            pgrep_cmd = ["pgrep", "-P", str(script_pid)]
            child_pids_str = subprocess.check_output(pgrep_cmd, stderr=subprocess.DEVNULL).decode().strip()
            
            for child_pid in child_pids_str.splitlines():
                try:
                    # Check if process is Java
                    comm_cmd = ["ps", "-p", child_pid, "-o", "comm="]
                    comm = subprocess.check_output(comm_cmd, stderr=subprocess.DEVNULL).decode().strip()
                    if "java" in comm:
                        return int(child_pid)
                except (subprocess.CalledProcessError, ValueError):
                    continue
        except (subprocess.CalledProcessError, ValueError):
            pass
        
        time.sleep(0.2)
    
    return None

def load_test_props() -> Dict[str, Any]:
    """
    Load test properties from JSON configuration file.
    """
    test_props_path = "test_props.json"
    if not os.path.exists(test_props_path):
        print(f"{Fore.RED}Error: {test_props_path} does not exist{Style.RESET_ALL}")
        sys.exit(1)
    
    try:
        with open(test_props_path, 'r') as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        print(f"{Fore.RED}Error decoding JSON from {test_props_path}: {e}{Style.RESET_ALL}")
        sys.exit(1)

def is_interactive(props: Dict[str, Any], project_name: str) -> List[Any]:
    """
    Check if project requires interactive testing based on properties.
    """
    if project_name not in props:
        return []
    return props[project_name]

def _get_category_from_path(path: str, root_path: str) -> str:
    """
    Extract category name from example path.
    Expected structure: root_path/MainCategory/SubCategory/project_name/
    """
    try:
        relative_path = os.path.relpath(path, root_path)
        parts = relative_path.split(os.sep)
        
        if len(parts) > 2:  # Return SubCategory if available
            return parts[1]
        elif len(parts) > 1:  # Fallback to MainCategory
            return parts[0]
    except ValueError:
        log_message(f"Cannot determine category for path: {path}", level="WARNING", color=Fore.YELLOW)
    
    return ""

def filter_projects_by_category(umfeld_lst: List[str], category: str, umfeld_root: str) -> List[str]:
    """
    Filter projects by specified category.
    """
    filtered_projects = []
    for project_path in umfeld_lst:
        project_category = _get_category_from_path(project_path, umfeld_root)
        if project_category and category.lower() in project_category.lower():
            filtered_projects.append(project_path)
    return filtered_projects

def get_app_window_dimensions(app_name: str) -> Tuple[int, int, int, int]:
    """
    Get window dimensions (x, y, width, height) for first window matching app_name.
    Supports Linux (X11) and macOS.
    """
    if sys.platform.startswith("linux"):
        try:
            output = subprocess.check_output(['wmctrl', '-lG']).decode()
            for line in output.splitlines():
                if app_name in line:
                    parts = line.split()
                    # wmctrl format: id desktop x y width height host title...
                    x, y, width, height = int(parts[2]), int(parts[3]), int(parts[4]), int(parts[5])
                    return (x, y, width, height)
            print(f"{Fore.RED}No window found with title containing '{app_name}'{Style.RESET_ALL}")
        except Exception as e:
            print(f"{Fore.RED}wmctrl error: {e}{Style.RESET_ALL}")
        return (0, 0, 0, 0)
    
    elif sys.platform == "darwin":
        try:
            script = f'''
            tell application "System Events"
                set appProc to first process whose name contains "{app_name}"
                set win to first window of appProc
                set {{"", x, y, w, h}} to position of win & size of win
                return w & "," & h
            end tell
            '''
            output = subprocess.check_output(['osascript', '-e', script]).decode().strip()
            w, h = map(int, output.split(','))
            return (0, 0, w, h)  # macOS returns size only
        except Exception as e:
            print(f"{Fore.RED}osascript error: {e}{Style.RESET_ALL}")
        return (0, 0, 0, 0)
    
    else:
        print(f"{Fore.RED}Unsupported platform for window dimension lookup{Style.RESET_ALL}")
        return (0, 0, 0, 0)
def run_mouse_action_sequence(window_rect: Tuple[int, int, int, int], actions: List[Tuple], total_duration: float = 5, steps_per_move: int = 20) -> None:
    """
    Execute sequence of mouse actions with smooth transitions.
    Starts from window center and times actions to match total_duration.
    """
    from pynput.mouse import Controller, Button
    
    mouse = Controller()
    x0, y0, w, h = window_rect

    # Start from window center
    center_x, center_y = x0 + w // 2, y0 + h // 2
    mouse.position = (center_x, center_y)
    time.sleep(0.2)  # Ensure window focus

    if not actions:
        return

    time_per_action = total_duration / len(actions)

    for action in actions:
        act_type, rel_x, rel_y = action
        target_x = x0 + rel_x
        target_y = y0 + rel_y

        start_pos_x, start_pos_y = mouse.position

        # Smooth movement to target position
        if steps_per_move > 0:
            step_duration = time_per_action / steps_per_move
            for i in range(1, steps_per_move + 1):
                t = i / steps_per_move
                interp_x = start_pos_x + (target_x - start_pos_x) * t
                interp_y = start_pos_y + (target_y - start_pos_y) * t
                mouse.position = (int(interp_x), int(interp_y))
                if step_duration > 0:
                    time.sleep(step_duration)
        
        mouse.position = (target_x, target_y)

        # Execute action
        if act_type == 'press':
            mouse.press(Button.left)
            time.sleep(0.05)
        elif act_type == 'release':
            mouse.release(Button.left)
            time.sleep(0.05)


def move_mouse_sequence(window_rect: Tuple[int, int, int, int], mouse_coords: List[Tuple[int, int]], total_duration: float = 2.0, steps_per_move: int = 20) -> None:
    """
    Move mouse smoothly through sequence of coordinates within window.
    Complete sequence takes exactly total_duration seconds.
    """
    x, y, w, h = window_rect
    mouse = Controller()
    
    if not mouse_coords or len(mouse_coords) < 2:
        return
        
    # Start at first coordinate
    prev = mouse_coords[0]
    mouse.position = (x + prev[0], y + prev[1])

    num_moves = len(mouse_coords) - 1
    step_duration = total_duration / (num_moves * steps_per_move)

    for target in mouse_coords[1:]:
        # Smooth interpolation between points
        for i in range(1, steps_per_move + 1):
            t = i / steps_per_move
            interp_x = prev[0] + (target[0] - prev[0]) * t
            interp_y = prev[1] + (target[1] - prev[1]) * t
            mouse.position = (int(x + interp_x), int(y + interp_y))
            time.sleep(step_duration)
        
        mouse.position = (x + target[0], y + target[1])
        prev = target

def record_window_video(window_rect: Tuple[int, int, int, int], duration: int, output_path: str, framerate: int = 60, verbose: bool = True) -> None:
    """
    Record window area using ffmpeg for specified duration.
    Requires ffmpeg installed and in PATH.
    """
    x, y, w, h = window_rect
    
    # Platform-specific ffmpeg commands
    if sys.platform.startswith("linux"):
        cmd = [
            "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
            "-video_size", f"{w}x{h}", "-framerate", str(framerate),
            "-f", "x11grab", "-i", f":0.0+{x},{y}",
            "-t", str(duration), output_path
        ]
    elif sys.platform == "darwin":
        cmd = [
            "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
            "-f", "avfoundation", "-framerate", str(framerate),
            "-i", "1:none", "-vf", f"crop={w}:{h}:{x}:{y}",
            "-t", str(duration), output_path
        ]
    elif sys.platform.startswith("win"):
        cmd = [
            "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
            "-f", "gdigrab", "-framerate", str(framerate),
            "-offset_x", str(x), "-offset_y", str(y),
            "-video_size", f"{w}x{h}", "-i", "desktop",
            "-t", str(duration), output_path
        ]
    else:
        print(f"{Fore.RED}Unsupported platform for screen recording{Style.RESET_ALL}")
        return

    try:
        stdout = None if verbose else subprocess.DEVNULL
        stderr = None if verbose else subprocess.DEVNULL
        subprocess.run(cmd, check=True, stdout=stdout, stderr=stderr)
        if verbose:
            print(f"{Fore.GREEN}Recording saved to {output_path}{Style.RESET_ALL}")
    except Exception as e:
        print(f"{Fore.RED}Failed to record video: {e}{Style.RESET_ALL}")

def record_window_video_async(window_rect: Tuple[int, int, int, int], duration: int, output_path: str, verbose: bool = True) -> threading.Thread:
    """
    Start video recording in separate thread to allow concurrent mouse interaction.
    Returns thread object for synchronization.
    """
    def record():
        record_window_video(window_rect, duration, output_path, verbose=verbose)
    
    thread = threading.Thread(target=record)
    thread.start()
    return thread

def get_client_area(pid: int, window_title: str, is_java_process: bool = False) -> Tuple[int, int, int, int, str]:
    """
    Finds the window geometry (x, y, w, h, win_id).
    For Java processes, it relies on window title matching due to unreliable PID reporting.
    For native processes, it verifies PID as well.
    Retries for a few seconds to allow the window to appear.
    Requires xdotool and xwininfo.

    Args:
        pid: The PID of the process that was launched.
        window_title: The expected title of the window.
        is_java_process: If True, indicates a Java process (PID verification is skipped).
    
    Returns:
        Tuple[int, int, int, int, str]: (x, y, width, height, window_id)
    """
    if not sys.platform.startswith("linux"):
        print(f"{Fore.RED}get_client_area is only supported on Linux.{Style.RESET_ALL}")
        return 0, 0, 0, 0, ""

    win_id = None
    for _ in range(15):  # Retry for 3 seconds (15 * 0.2s)
        try:
            # 1. Find all windows with the matching title.
            potential_win_ids = subprocess.check_output(
                ["xdotool", "search", "--name", window_title]
            ).decode().strip().splitlines()

            if not potential_win_ids:
                time.sleep(0.2)
                continue

            # 2. Verify the PID of the found windows (only for non-Java processes).
            #    For Java processes, we trust the title match due to unreliable PID reporting.
            if is_java_process:
                exact_match_win_id = None
                non_terminal_partial_match_win_id = None
                
                for potential_id in potential_win_ids:
                    try:
                        full_window_name = subprocess.check_output(
                            ["xdotool", "getwindowname", potential_id]
                        ).decode().strip()
                        
                        # Get window class for additional filtering
                        try:
                            window_class = subprocess.check_output(
                                ["xdotool", "getwindowclassname", potential_id]
                            ).decode().strip().lower()
                        except (subprocess.CalledProcessError, ValueError):
                            window_class = ""
                        
                        # Check if this is a terminal/shell window
                        terminal_keywords = ["terminal", "bash", "zsh", "shell", "konsole", "gnome-terminal", "xterm", "terminator", "tilix", "alacritty", "kitty"]
                        is_terminal = (
                            any(term in full_window_name.lower() for term in terminal_keywords) or
                            any(term in window_class for term in terminal_keywords) or
                            window_class in ["terminal", "gnome-terminal", "konsole", "xterm", "terminator", "tilix", "alacritty", "kitty"]
                        )

                        if full_window_name == window_title and not is_terminal: # Exact match is highest priority
                            exact_match_win_id = potential_id
                            break # Found the best possible match, no need to check further
                        elif window_title.lower() in full_window_name.lower() and not is_terminal:
                            # This is a partial match and not a terminal/shell, keep it as a fallback
                            non_terminal_partial_match_win_id = potential_id
                    except (subprocess.CalledProcessError, ValueError):
                        continue
                
                if exact_match_win_id:
                    win_id = exact_match_win_id
                elif non_terminal_partial_match_win_id:
                    win_id = non_terminal_partial_match_win_id
                else:
                    # Fallback to the first potential ID if no better candidate is found
                    win_id = potential_win_ids[0] if potential_win_ids else None
                
                if win_id:
                    break # Found a candidate, exit retry loop
            else:
                for potential_id in potential_win_ids:
                    try:
                        win_pid_str = subprocess.check_output(
                            ["xdotool", "getwindowpid", potential_id]
                        ).decode().strip()
                        
                        win_pid = int(win_pid_str)

                        # For native apps, the window PID should match the launched PID.
                        if win_pid == pid:
                            # Double check this isn't a terminal window
                            try:
                                full_window_name = subprocess.check_output(
                                    ["xdotool", "getwindowname", potential_id]
                                ).decode().strip()
                                
                                # Get window class for additional filtering
                                try:
                                    window_class = subprocess.check_output(
                                        ["xdotool", "getwindowclassname", potential_id]
                                    ).decode().strip().lower()
                                except (subprocess.CalledProcessError, ValueError):
                                    window_class = ""
                                
                                # Check if this is a terminal/shell window
                                terminal_keywords = ["terminal", "bash", "zsh", "shell", "konsole", "gnome-terminal", "xterm", "terminator", "tilix", "alacritty", "kitty"]
                                is_terminal = (
                                    any(term in full_window_name.lower() for term in terminal_keywords) or
                                    any(term in window_class for term in terminal_keywords) or
                                    window_class in ["terminal", "gnome-terminal", "konsole", "xterm", "terminator", "tilix", "alacritty", "kitty"]
                                )
                                
                                if not is_terminal:
                                    win_id = potential_id
                                    break # Found the correct native window
                            except (subprocess.CalledProcessError, ValueError):
                                # If we can't get window name/class, still use this window as fallback if it's the only match
                                if len(potential_win_ids) == 1:
                                    win_id = potential_id
                                    break
                    
                    except (subprocess.CalledProcessError, ValueError):
                        # Window might have closed, or PID is not a number.
                        continue
                
                if win_id:
                    break # Exit retry loop if we found our window

        except (subprocess.CalledProcessError, FileNotFoundError):
            # xdotool might fail if not installed or if no windows are found yet.
            time.sleep(0.2)
            continue
        
        time.sleep(0.2)

    if not win_id:
        print(f"{Fore.RED}Failed to find a verified window for title '{window_title}' (PID: {pid}, Java: {is_java_process}).{Style.RESET_ALL}")
        return 0, 0, 0, 0, ""

    # 3. Get window geometry using the verified win_id
    try:
        output = subprocess.check_output(
            ["xwininfo", "-id", win_id]
        ).decode()
        
        def extract(pattern, text, label):
            match = re.search(pattern, text)
            if not match:
                print(f"{Fore.RED}Could not find {label} in xwininfo output!{Style.RESET_ALL}")
                return None
            return int(match.group(1))
        
        x = extract(r"Absolute upper-left X:\s+(\d+)", output, "X")
        y = extract(r"Absolute upper-left Y:\s+(\d+)", output, "Y")
        w = extract(r"Width:\s+(\d+)", output, "Width")
        h = extract(r"Height:\s+(\d+)", output, "Height")
        
        if None in (x, y, w, h):
            return 0, 0, 0, 0, ""
        return x, y, w, h, win_id

    except (subprocess.CalledProcessError, FileNotFoundError, Exception) as e:
        print(f"{Fore.RED}Failed to get client area geometry for win_id {win_id}: {e}{Style.RESET_ALL}")
        return 0, 0, 0, 0, ""

def add_bottom_text_padding(video_path: str, text: str, padding: int = 60, font_size: int = 36, font_color: str = "white", fontfile: str = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", verbose: bool = True) -> None:
    """
    Adds bottom padding to a video or image and embeds the given text in the padding area.
    Overwrites the original file.
    """
    import subprocess
    import os
    
    if padding < 0:
        raise ValueError("Padding must be non-negative")

    is_image = any(video_path.lower().endswith(ext) for ext in ['.png', '.jpg', '.jpeg', '.bmp'])
    
    safe_text = text.replace("'", "''")
    
    effective_font_size = min(font_size, padding) if padding > 0 else 0
    y_value = (padding - effective_font_size) // 2
    y_expr = f"h-{padding}+{y_value}"
    
    vf = (
        f"pad=iw:ih+{padding}:0:0:color=black,"
        f"drawtext=fontfile={fontfile}:text='{safe_text}':x=10:y={y_expr}:fontsize={effective_font_size}:fontcolor={font_color}:box=0"
    )
    
    temp_path = video_path + ".tmp" + os.path.splitext(video_path)[1]

    cmd = [
        "ffmpeg",
        "-hide_banner",
        "-loglevel", "error",
        "-y",
        "-i", video_path,
        "-vf", vf,
    ]
    
    if is_image:
        cmd.extend(["-frames:v", "1"])
    else:
        cmd.extend(["-c:a", "copy"])
        
    cmd.append(temp_path)
    
    try:
        stdout = None if verbose else subprocess.DEVNULL
        stderr = None if verbose else subprocess.DEVNULL
        subprocess.run(cmd, check=True, stderr=stderr, stdout=stdout)
        os.replace(temp_path, video_path)
        if verbose:
            print(f"{Fore.GREEN}Text '{text}' added to {video_path}{Style.RESET_ALL}")
    except subprocess.CalledProcessError as e:
        error_msg = e.stderr.decode('utf-8') if e.stderr else str(e)
        print(f"{Fore.RED}FFmpeg command failed: {error_msg}{Style.RESET_ALL}")
        if os.path.exists(temp_path):
            os.remove(temp_path)
    except Exception as e:
        print(f"{Fore.RED}Failed to add text to video: {e}{Style.RESET_ALL}")
        if os.path.exists(temp_path):
            os.remove(temp_path)

def concat_videos_ffmpeg(video1: str, video2: str, output_path: str) -> None:
    """
    Concatenates two videos into one using ffmpeg concat demuxer.
    The input videos must have the same codec, resolution, and framerate.
    """
    import subprocess
    import os
    import tempfile
    
    # Create a temporary file listing the videos
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
        f.write(f"file '{os.path.abspath(video1)}'\n")
        f.write(f"file '{os.path.abspath(video2)}'\n")
        list_path = f.name
    
    cmd = [
        'ffmpeg',
        '-hide_banner',
        # '-loglevel', 'error',
        '-y',
        '-f', 'concat',
        '-safe', '0',
        '-i', list_path,
        '-c', 'copy',
        output_path
    ]
    try:
        subprocess.run(cmd, check=True, stderr=subprocess.PIPE, stdout=subprocess.PIPE)
        print(f"{Fore.GREEN}Videos concatenated to {output_path}{Style.RESET_ALL}")
    except subprocess.CalledProcessError as e:
        error_msg = e.stderr.decode('utf-8') if e.stderr else str(e)
        print(f"{Fore.RED}FFmpeg concat failed: {error_msg}{Style.RESET_ALL}")
    finally:
        if os.path.exists(list_path):
            os.remove(list_path)

def concat_videos_ffmpeg_filter(video1: str, video2: str, output_path: str, direction: str = 'vertical', verbose: bool = True) -> None:
    """
    Concatenates two videos using ffmpeg filter_complex (re-encodes for compatibility).
    direction: 'vertical' (default) or 'horizontal'
    Handles videos with or without audio streams.
    """
    import subprocess
    # Set filter for vertical or horizontal stack (video only)
    if direction == 'vertical':
        filter_str = '[0:v][1:v]vstack=inputs=2[v]'
    else:
        filter_str = '[0:v][1:v]hstack=inputs=2[v]'
    cmd = [
        'ffmpeg',
        '-hide_banner',
        '-loglevel', 'error',
        '-y',
        '-i', video1,
        '-i', video2,
        '-filter_complex', filter_str,
        '-map', '[v]',
        '-c:v', 'libx264',
        '-pix_fmt', 'yuv420p',
        '-crf', '23',
        '-preset', 'veryfast',
        output_path
    ]
    try:
        stdout = None if verbose else subprocess.DEVNULL
        stderr = None if verbose else subprocess.DEVNULL
        subprocess.run(cmd, check=True, stderr=stderr, stdout=stdout)
        if verbose:
            print(f"{Fore.GREEN}Videos concatenated ({direction}) to {output_path}{Style.RESET_ALL}")
    except subprocess.CalledProcessError as e:
        error_msg = e.stderr.decode('utf-8') if e.stderr else str(e)
        print(f"{Fore.RED}FFmpeg filter_complex concat failed: {error_msg}{Style.RESET_ALL}")

def concat_images(image1_path: str, image2_path: str, output_path: str, direction: str = 'vertical') -> None:
    """
    Concatenates two images using Pillow.
    direction: 'vertical' (default) or 'horizontal'
    """
    from PIL import Image
    try:
        img1 = Image.open(image1_path)
        img2 = Image.open(image2_path)
        
        if direction == 'vertical':
            dst = Image.new('RGB', (max(img1.width, img2.width), img1.height + img2.height))
            dst.paste(img1, (0, 0))
            dst.paste(img2, (0, img1.height))
        else:
            dst = Image.new('RGB', (img1.width + img2.width, max(img1.height, img2.height)))
            dst.paste(img1, (0, 0))
            dst.paste(img2, (img1.width, 0))
            
        dst.save(output_path)
        print(f"{Fore.GREEN}Images concatenated ({direction}) to {output_path}{Style.RESET_ALL}")
    except Exception as e:
        print(f"{Fore.RED}Failed to concatenate images: {e}{Style.RESET_ALL}")

def kill_process(pid: int) -> bool:
    """
    Kills the process with the given PID.
    """
    try:
        if sys.platform.startswith("linux") or sys.platform == "darwin":
            os.killpg(os.getpgid(pid), signal.SIGTERM)
        elif sys.platform.startswith("win"):
            subprocess.run(["taskkill", "/F", "/PID", str(pid)], check=True)
        else:
            print(f"{Fore.RED}Unsupported platform for killing process.{Style.RESET_ALL}")
    except Exception as e:
        print(f"{Fore.RED}Failed to kill process {pid}: {e}{Style.RESET_ALL}")
        return False
    return True

def send_keys_to_window(window_title: str, keys: str, delay: int = 100, total_duration: float = 5, window_rect: tuple = None) -> bool:
    """
    Focuses the window with the given title and sends the specified keys.
    Optionally moves the mouse to the center of the given window_rect before sending keys.
    - window_title: title of the window to focus (fuzzy match, first match)
    - keys: string to type (can be plain text or key names, e.g. 'a', 'Return')
    - delay: delay between keystrokes in ms (default 100, ignored if total_duration is set)
    - total_duration: if set, the total time (in seconds) to type all keys (overrides delay)
    - window_rect: (x, y, w, h) tuple; if provided, mouse will move to center before typing
    Linux: uses xdotool. macOS: uses osascript/AppleScript.
    """
    try:
        if window_rect is not None:
            try:
                from pynput.mouse import Controller
                x, y, w, h = window_rect
                mouse = Controller()
                mouse.position = (x + w // 2, y + h // 2)
                time.sleep(0.1)
            except Exception as e:
                print(f"{Fore.YELLOW}Warning: Could not move mouse to window center: {e}{Style.RESET_ALL}")
        if sys.platform.startswith("linux"):
            win_ids = subprocess.check_output([
                "xdotool", "search", "--name", window_title
            ]).decode().splitlines()
            if not win_ids:
                print(f"{Fore.RED}No window found with title '{window_title}'{Style.RESET_ALL}")
                return False
            win_id = win_ids[0]
            subprocess.run(["xdotool", "windowactivate", "--sync", win_id], check=True)
            time.sleep(0.1)
            if total_duration is not None and len(keys) > 0:
                delay_per_key = max(1, int((total_duration * 1000) / len(keys)))
            else:
                delay_per_key = delay
            for c in keys:
                subprocess.run(["xdotool", "type", "--delay", str(delay_per_key), c], check=True)
            print(f"{Fore.GREEN}Sent keys to window '{window_title}': {keys}{Style.RESET_ALL}")
            return True
        elif sys.platform == "darwin":
            # macOS: osascript/AppleScript
            script_lines = [
                'tell application "System Events"',
                f'set frontmostProcess to first process whose windows\'s name contains "{window_title}"',
                'set frontmost of frontmostProcess to true',
                'delay 0.1'
            ]
            if total_duration is not None and len(keys) > 0:
                delay_per_key = total_duration / len(keys)
                for c in keys:
                    script_lines.append(f'keystroke "{c}"')
                    script_lines.append(f'delay {delay_per_key}')
            else:
                script_lines.append(f'keystroke "{keys}"')
            script_lines.append('end tell')
            script = "\n".join(script_lines)
            subprocess.run(["osascript", "-e", script], check=True)
            print(f"{Fore.GREEN}Sent keys to window '{window_title}' (macOS): {keys}{Style.RESET_ALL}")
            return True
        else:
            print(f"{Fore.RED}send_keys_to_window not supported on this platform.{Style.RESET_ALL}")
            return False
    except Exception as e:
        print(f"{Fore.RED}Failed to send keys to window '{window_title}': {e}{Style.RESET_ALL}")
        return False

def mouse_action_sequence(window_rect: Tuple[int, int, int, int], actions: List[tuple], total_duration: float = 2.0, steps_per_move: int = 20) -> None:
    """
    Performs a sequence of mouse actions (move, click, drag) within the given window using pynput.
    Each action is a tuple:
      - ('move', x, y)
      - ('click', x, y, button='left', count=1)
      - ('drag', x1, y1, x2, y2, button='left')
    total_duration: total time for the sequence (seconds)
    steps_per_move: steps for smooth move/drag
    """
    from pynput.mouse import Controller, Button
    import time
    x, y, w, h = window_rect
    mouse = Controller()
    if not actions:
        return
    # Estimate time per action
    time_per_action = total_duration / max(1, len(actions))
    for act in actions:
        if act[0] == 'move':
            _, mx, my = act
            mouse.position = (x + mx, y + my)
            time.sleep(time_per_action)
        elif act[0] == 'click':
            _, mx, my, *rest = act
            button = Button.left
            count = 1
            if rest:
                if 'right' in rest: button = Button.right
                if isinstance(rest[-1], int): count = rest[-1]
            mouse.position = (x + mx, y + my)
            for _ in range(count):
                mouse.click(button)
                time.sleep(0.05)
            time.sleep(time_per_action)
        elif act[0] == 'drag':
            _, mx1, my1, mx2, my2, *rest = act
            button = Button.left
            if rest and 'right' in rest: button = Button.right
            mouse.position = (x + mx1, y + my1)
            mouse.press(button)
            for i in range(1, steps_per_move + 1):
                t = i / (steps_per_move + 1)
                interp_x = mx1 + (mx2 - mx1) * t
                interp_y = my1 + (my2 - my1) * t
                mouse.position = (int(x + interp_x), int(y + interp_y))
                time.sleep(time_per_action / steps_per_move)
            mouse.position = (x + mx2, y + my2)
            mouse.release(button)
            time.sleep(time_per_action)

def capture_window_image(window_rect: Tuple[int, int, int, int], output_path: str, verbose: bool = True) -> bool:
    """
    Captures a screenshot of the given window area (x, y, w, h) and saves to output_path (PNG).
    Tries ffmpeg first, falls back to pyautogui if needed.
    """
    x, y, w, h = window_rect
    import sys
    import subprocess
    try:
        if sys.platform.startswith("linux"):
            cmd = [
                "ffmpeg",
                "-hide_banner",
                "-loglevel", "error",
                "-y",
                "-f", "x11grab",
                "-video_size", f"{w}x{h}",
                "-i", f":0.0+{x},{y}",
                "-frames:v", "1",
                output_path
            ]
            stdout = None if verbose else subprocess.DEVNULL
            stderr = None if verbose else subprocess.DEVNULL
            subprocess.run(cmd, check=True, stdout=stdout, stderr=stderr)
            return True
        elif sys.platform == "darwin":
            cmd = [
                "ffmpeg",
                "-hide_banner",
                "-loglevel", "error",
                "-y",
                "-f", "avfoundation",
                "-i", "1:none",
                "-vf", f"crop={w}:{h}:{x}:{y}",
                "-frames:v", "1",
                output_path
            ]
            stdout = None if verbose else subprocess.DEVNULL
            stderr = None if verbose else subprocess.DEVNULL
            subprocess.run(cmd, check=True, stdout=stdout, stderr=stderr)
            return True
        elif sys.platform.startswith("win"):
            cmd = [
                "ffmpeg",
                "-hide_banner",
                "-loglevel", "error",
                "-y",
                "-f", "gdigrab",
                "-framerate", "1",
                "-offset_x", str(x),
                "-offset_y", str(y),
                "-video_size", f"{w}x{h}",
                "-i", "desktop",
                "-frames:v", "1",
                output_path
            ]
            stdout = None if verbose else subprocess.DEVNULL
            stderr = None if verbose else subprocess.DEVNULL
            subprocess.run(cmd, check=True, stdout=stdout, stderr=stderr)
            return True
    except Exception as e:
        log_message(f"ffmpeg screenshot failed: {e}", level="ERROR", color=Fore.RED)
    # Fallback: pyautogui
    try:
        import pyautogui
        img = pyautogui.screenshot(region=(x, y, w, h))
        img.save(output_path)
        return True
    except Exception as e:
        log_message(f"pyautogui screenshot failed: {e}", level="ERROR", color=Fore.RED)
        return False

def generate_random_mouse_moves(x: int, y: int, w: int, h: int, amount: int) -> list:
    """
    Generates a list of ('move', x, y) tuples with random coordinates within the given rectangle (x, y, w, h).
    The returned coordinates are relative to the top-left of the rectangle (not absolute screen coords).
    This output is directly compatible as input for mouse_action_sequence().
    """
    moves = []
    for _ in range(amount):
        rx = random.randint(0, max(0, w - 1))
        ry = random.randint(0, max(0, h - 1))
        moves.append(('move', rx, ry))
    return moves

def generate_random_mouse_actions(x: int, y: int, w: int, h: int, amount: int, include_click: bool = False, include_drag: bool = False, seed: str = None) -> list:
    """
    Generates a list of random mouse actions within the given rectangle (x, y, w, h).
    Actions can include 'move', 'press', and 'release' depending on the switches.
    The returned coordinates are relative to the top-left of the rectangle.
    Output is compatible with mouse_action_sequence().
    If seed is provided, the random sequence will be deterministic for that seed.
    """
    rnd = random.Random(seed) if seed is not None else random
    actions = []
    
    # Determine the possible action types based on flags
    possible_actions = ['move']
    if include_click:
        possible_actions.append('click')
    if include_drag:
        possible_actions.append('drag')

    for _ in range(amount):
        action_type = rnd.choice(possible_actions)

        if action_type == 'move':
            rx = rnd.randint(0, max(0, w - 1))
            ry = rnd.randint(0, max(0, h - 1))
            actions.append(('move', rx, ry))
        elif action_type == 'click':
            rx = rnd.randint(0, max(0, w - 1))
            ry = rnd.randint(0, max(0, h - 1))
            actions.append(('press', rx, ry))
            actions.append(('release', rx, ry))
        elif action_type == 'drag':
            rx1 = rnd.randint(0, max(0, w - 1))
            ry1 = rnd.randint(0, max(0, h - 1))
            rx2 = rnd.randint(0, max(0, w - 1))
            ry2 = rnd.randint(0, max(0, h - 1))
            actions.append(('press', rx1, ry1))
            # Add intermediate move for the drag
            actions.append(('move', rx2, ry2))
            actions.append(('release', rx2, ry2))
            
    return actions

