import os
import sys
import subprocess
import time
import signal
from enum import Enum, auto
from rapidfuzz import process
import json
from colorama import Fore, Style
from pynput.mouse import Controller
import random
import re
import threading
from typing import Optional, List, Tuple, Dict, Any
from PIL import Image
from datetime import datetime
from contextlib import contextmanager

# --- Centralized Logging System ---
_log_file_path = None
_ansi_escape = re.compile(r'\x1b\[([0-9]{1,2}(;[0-9]{1,2})*)?[mGK]')

def setup_logging(log_file_path: str):
    """Initializes the centralized logging system."""
    global _log_file_path
    _log_file_path = log_file_path

def log_message(message: str, component: str = "General", level: str = "INFO", color: str = None):
    """
    Logs a message to both the console and the configured log file.
    """
    # 1. Format for Console (with color)
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    console_message = f"[{timestamp}] [{level}] [{component}] {message}"
    if color:
        print(f"{color}{console_message}{Style.RESET_ALL}")
    else:
        print(console_message)

    # 2. Format for File (no color)
    if _log_file_path:
        clean_message = _ansi_escape.sub('', message)
        file_message = f"[{timestamp}] [{level}] [{component}] {clean_message}\n"
        with open(_log_file_path, "a") as f:
            f.write(file_message)

@contextmanager
def time_logger(operation_name: str, component: str = "Timer", project_name: str = None):
    """컨텍스트 매니저로 작업 시간 측정 및 로깅"""
    start_time = time.time()
    log_message(f"Started {operation_name}" + (f" for {project_name}" if project_name else ""),
                component=component, color=Fore.BLUE)
    try:
        yield
    finally:
        duration = time.time() - start_time
        log_message(f"Completed {operation_name} in {duration:.2f}s" + (f" for {project_name}" if project_name else ""),
                    component=component, color=Fore.GREEN)

class InteractiveType(Enum):
    MOUSE_RANDOM = auto()
    MOUSE_CLICK = auto()
    MOUSE_DRAG = auto()
    KEYBOARD = auto()

def get_all_umfeld_processing_examples(root: str) -> List[str]:
    result = []
    for r, _, _ in os.walk(root):
        if r.count(os.sep) - root.count(os.sep) == 2 and "template" not in r:
            result.append(r)
    return result

def get_all_original_processing_examples(root: str) -> List[str]:
    return get_all_umfeld_processing_examples(root) # Same logic

def build_and_run_umfeld_processing_example(example_path: str, nohup: bool, verbose: bool = True) -> Optional[int]:
    example_path = os.path.abspath(example_path)
    example_name = os.path.basename(example_path)
    build_dir = os.path.join(example_path, "build")
    
    log_message(f"Building at: {example_path}", component="Umfeld-Build", color=Fore.CYAN)
    
    build_cmd = f"cmake -S {example_path} -B {build_dir} -DCMAKE_BUILD_TYPE=Debug"
    make_cmd = f"make -C {build_dir} -j32"
    run_cmd = [os.path.join(build_dir, example_name)]
    
    try:
        if not os.path.exists(build_dir):
            os.makedirs(build_dir)
        
        stdout = None if verbose else subprocess.DEVNULL
        stderr = None if verbose else subprocess.DEVNULL
        
        subprocess.run(build_cmd, shell=True, check=True, stdout=stdout, stderr=stderr, cwd=build_dir)
        subprocess.run(make_cmd, shell=True, check=True, stdout=stdout, stderr=stderr)
        
        log_message(f"Running executable: {' '.join(run_cmd)}", component="Umfeld-Run", color=Fore.GREEN)
        
        proc = subprocess.Popen(run_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, preexec_fn=os.setsid) if nohup else subprocess.Popen(run_cmd)
        
        log_message(f"Started with PID {proc.pid}.", component="Umfeld-Run", color=Fore.GREEN)
        return proc.pid
        
    except subprocess.CalledProcessError as e:
        log_message(f"Failed to build or run '{example_name}': {e}", component="Umfeld-Run", level="ERROR", color=Fore.RED)
        return None
    except Exception as e:
        log_message(f"An unexpected error occurred for '{example_name}': {e}", component="Umfeld-Run", level="ERROR", color=Fore.RED)
        return None

def build_and_run_original_processing_example(example_path: str, nohup: bool) -> Optional[int]:
    example_path = os.path.abspath(example_path)
    example_name = os.path.basename(example_path)
    cmd = ["processing-java", f"--sketch={example_path}", "--run"]
    
    log_message(f"Running with processing-java at: {example_path}", component="Processing-Run", color=Fore.CYAN)

    try:
        proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, preexec_fn=os.setsid) if nohup else subprocess.Popen(cmd)
        script_pid = proc.pid

        java_pid = None
        for _ in range(15): # Retry for 3 seconds
            try:
                pgrep_cmd = ["pgrep", "-P", str(script_pid)]
                child_pids_str = subprocess.check_output(pgrep_cmd, stderr=subprocess.DEVNULL).decode().strip()
                for child_pid in child_pids_str.splitlines():
                    try:
                        comm_cmd = ["ps", "-p", child_pid, "-o", "comm="]
                        comm = subprocess.check_output(comm_cmd, stderr=subprocess.DEVNULL).decode().strip()
                        if "java" in comm:
                            java_pid = int(child_pid)
                            break
                    except (subprocess.CalledProcessError, ValueError):
                        continue
                if java_pid:
                    break
            except (subprocess.CalledProcessError, ValueError):
                time.sleep(0.2)
        
        if java_pid is None:
            log_message(f"Could not find child Java process for script PID {script_pid}", component="Processing-Run", level="ERROR", color=Fore.RED)
            kill_process(script_pid)
            return None
            
        log_message(f"Started with Java PID {java_pid}.", component="Processing-Run", color=Fore.GREEN)
        return java_pid
        
    except Exception as e:
        log_message(f"Failed to run '{example_name}': {e}", component="Processing-Run", level="ERROR", color=Fore.RED)
        return None

def load_test_props() -> Dict[str, Any]:
    test_props_path = "test_props.json"
    if not os.path.exists(test_props_path):
        log_message(f"{test_props_path} does not exist.", component="Init", level="ERROR", color=Fore.RED)
        sys.exit(1)
    
    with open(test_props_path, 'r') as f:
        try:
            return json.load(f)
        except json.JSONDecodeError as e:
            log_message(f"Error decoding JSON from {test_props_path}: {e}", component="Init", level="ERROR", color=Fore.RED)
            sys.exit(1)

def is_interactive(props: Dict[str, Any], project_name: str) -> List[Any]:
    if project_name not in props:
        log_message(f"Project '{project_name}' not found in test_props.json.", component="Config", level="WARNING", color=Fore.YELLOW)
        return []
    return props[project_name]

def _get_category_from_path(path: str, root_path: str) -> str:
    try:
        relative_path = os.path.relpath(path, root_path)
        parts = relative_path.split(os.sep)
        if len(parts) > 2: return parts[1]
        if len(parts) > 1: return parts[0]
    except ValueError:
        pass
    return ""

def fuzzy_match_pairs(umfeld_lst: List[str], original_lst: List[str], umfeld_root: str, original_root: str) -> dict:
    pairs = {}
    original_categorized = {}

    def normalize_name(name):
        return name.replace('_', '').replace(' ', '').lower()

    for example_path in original_lst:
        category = _get_category_from_path(example_path, original_root)
        if category:
            if category not in original_categorized:
                original_categorized[category] = []
            original_categorized[category].append(example_path)

    for umfeld_example_path in umfeld_lst:
        umfeld_project_name = os.path.basename(umfeld_example_path)
        umfeld_category = _get_category_from_path(umfeld_example_path, umfeld_root)

        if umfeld_category and umfeld_category in original_categorized:
            category_choices_paths = original_categorized[umfeld_category]
            category_choices_names = [os.path.basename(p) for p in category_choices_paths]
            normalized_umfeld_name = normalize_name(umfeld_project_name)
            
            length_matched_choices = [n for n in category_choices_names if len(normalize_name(n)) == len(normalized_umfeld_name)]

            best_match_name = None
            if length_matched_choices:
                # Use a dictionary to match against normalized names but retrieve original names
                choices_dict = {name: normalize_name(name) for name in length_matched_choices}
                result = process.extractOne(normalized_umfeld_name, choices_dict)
                # When using a dict, result is (value, score, key)
                if result:
                    _, _, best_match_name = result
            
            if not best_match_name:
                # Fallback to matching against all names in the category
                result = process.extractOne(umfeld_project_name, category_choices_names)
                # When using a list, result is (choice, score, index)
                if result:
                    best_match_name, _, _ = result

            if best_match_name:
                pairs[umfeld_project_name] = best_match_name
            else:
                log_message(f"No match found for '{umfeld_project_name}' in category '{umfeld_category}'", component="Match", level="WARNING", color=Fore.YELLOW)
        else:
            log_message(f"No category '{umfeld_category}' for '{umfeld_project_name}'", component="Match", level="WARNING", color=Fore.YELLOW)
    return pairs

def run_mouse_action_sequence(window_rect, actions, total_duration=5, steps_per_move=20):
    from pynput.mouse import Controller, Button
    mouse = Controller()
    x0, y0, w, h = window_rect
    mouse.position = (x0 + w // 2, y0 + h // 2)
    time.sleep(0.2)

    if not actions: return
    time_per_action = total_duration / len(actions)

    for act_type, rel_x, rel_y in actions:
        target_x, target_y = x0 + rel_x, y0 + rel_y
        start_pos_x, start_pos_y = mouse.position

        if steps_per_move > 0:
            step_duration = time_per_action / steps_per_move
            for i in range(1, steps_per_move + 1):
                t = i / steps_per_move
                mouse.position = (int(start_pos_x + (target_x - start_pos_x) * t), int(start_pos_y + (target_y - start_pos_y) * t))
                if step_duration > 0: time.sleep(step_duration)
        
        mouse.position = (target_x, target_y)
        if act_type == 'press': mouse.press(Button.left); time.sleep(0.05)
        elif act_type == 'release': mouse.release(Button.left); time.sleep(0.05)

def record_window_video_async(window_rect: Tuple[int, int, int, int], duration: int, output_path: str, verbose: bool = True) -> threading.Thread:
    def record():
        x, y, w, h = window_rect
        platform_cmd = []
        if sys.platform.startswith("linux"):
            platform_cmd = ["-video_size", f"{w}x{h}", "-framerate", "60", "-f", "x11grab", "-i", f":0.0+{x},{y}"]
        # Add other platforms if needed...
        else:
            log_message("Unsupported platform for screen recording.", component="Record", level="ERROR", color=Fore.RED)
            return

        cmd = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y"] + platform_cmd + ["-t", str(duration), output_path]
        
        try:
            subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception as e:
            log_message(f"Failed to record video: {e}", component="Record", level="ERROR", color=Fore.RED)

    t = threading.Thread(target=record)
    t.start()
    return t

def get_client_area(pid: int, window_title: str, is_java_process: bool = False) -> Tuple[int, int, int, int, Optional[str]]:
    if not sys.platform.startswith("linux"):
        log_message("get_client_area is only supported on Linux.", component="Window", level="ERROR", color=Fore.RED)
        return 0, 0, 0, 0, None

    win_id = None
    for _ in range(15):
        try:
            potential_ids = subprocess.check_output(["xdotool", "search", "--name", window_title]).decode().strip().splitlines()
            if not potential_ids: time.sleep(0.2); continue

            if is_java_process:
                for pot_id in potential_ids:
                    name = subprocess.check_output(["xdotool", "getwindowname", pot_id]).decode().strip()
                    if window_title.lower() in name.lower() and "terminal" not in name.lower():
                        win_id = pot_id
                        break
                if not win_id: win_id = potential_ids[0]
            else: # Native process: verify PID
                for pot_id in potential_ids:
                    if pid == int(subprocess.check_output(["xdotool", "getwindowpid", pot_id]).decode().strip()):
                        win_id = pot_id
                        break
            if win_id: break
        except (subprocess.CalledProcessError, FileNotFoundError):
            time.sleep(0.2)
    
    if not win_id:
        log_message(f"Failed to find window for title '{window_title}' (PID: {pid}, Java: {is_java_process})", component="Window", level="ERROR", color=Fore.RED)
        return 0, 0, 0, 0, None

    try:
        output = subprocess.check_output(["xwininfo", "-id", win_id]).decode()
        x = int(re.search(r"Absolute upper-left X:\s+(\d+)", output).group(1))
        y = int(re.search(r"Absolute upper-left Y:\s+(\d+)", output).group(1))
        w = int(re.search(r"Width:\s+(\d+)", output).group(1))
        h = int(re.search(r"Height:\s+(\d+)", output).group(1))
        return x, y, w, h, win_id
    except Exception as e:
        log_message(f"Failed to get geometry for win_id {win_id}: {e}", component="Window", level="ERROR", color=Fore.RED)
        return 0, 0, 0, 0, None

def add_bottom_text_padding(video_path: str, text: str, padding: int = 50, verbose: bool = True):
    is_image = any(video_path.lower().endswith(ext) for ext in ['.png', '.jpg', '.jpeg', '.bmp'])
    safe_text = text.replace("'", "''")
    font_size = min(36, padding)
    y_expr = f"h-{padding}+{(padding - font_size) // 2}"
    vf = f"pad=iw:ih+{padding}:0:0:color=black,drawtext=fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf:text='{safe_text}':x=10:y={y_expr}:fontsize={font_size}:fontcolor=white:box=0"
    
    temp_path = video_path + ".tmp" + os.path.splitext(video_path)[1]
    cmd = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", video_path, "-vf", vf]
    if is_image: cmd.extend(["-frames:v", "1"])
    else: cmd.extend(["-c:a", "copy"])
    cmd.append(temp_path)
    
    try:
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        os.replace(temp_path, video_path)
    except Exception as e:
        log_message(f"FFmpeg command failed while adding text: {e}", component="ffmpeg", level="ERROR", color=Fore.RED)
        if os.path.exists(temp_path): os.remove(temp_path)

def concat_videos_ffmpeg_filter(video1: str, video2: str, output_path: str, verbose: bool = True):
    filter_str = '[0:v][1:v]vstack=inputs=2[v]'
    cmd = ['ffmpeg', '-hide_banner', '-loglevel', 'error', '-y', '-i', video1, '-i', video2, '-filter_complex', filter_str, '-map', '[v]', '-c:v', 'libx264', '-crf', '23', '-preset', 'veryfast', output_path]
    try:
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception as e:
        log_message(f"FFmpeg filter_complex concat failed: {e}", component="ffmpeg", level="ERROR", color=Fore.RED)

def concat_images(image1_path: str, image2_path: str, output_path: str):
    try:
        img1, img2 = Image.open(image1_path), Image.open(image2_path)
        dst = Image.new('RGB', (max(img1.width, img2.width), img1.height + img2.height))
        dst.paste(img1, (0, 0))
        dst.paste(img2, (0, img1.height))
        dst.save(output_path)
    except Exception as e:
        log_message(f"Failed to concatenate images: {e}", component="Image", level="ERROR", color=Fore.RED)

def kill_process(pid: int) -> bool:
    try:
        os.killpg(os.getpgid(pid), signal.SIGTERM)
        log_message(f"Killed process group with PGID {os.getpgid(pid)}.", component="Teardown", color=Fore.YELLOW)
        return True
    except Exception as e:
        log_message(f"Failed to kill process {pid}: {e}", component="Teardown", level="WARNING", color=Fore.YELLOW)
        return False

def send_keys_to_window(win_id: str, keys: str, total_duration: float = 5, window_rect: tuple = None):
    try:
        if window_rect:
            mouse = Controller()
            mouse.position = (window_rect[0] + window_rect[2] // 2, window_rect[1] + window_rect[3] // 2)
            time.sleep(0.1)

        subprocess.run(["xdotool", "windowactivate", "--sync", win_id], check=True)
        time.sleep(0.1)
        
        delay_per_key = max(1, int((total_duration * 1000) / len(keys))) if keys else 0
        for c in keys:
            subprocess.run(["xdotool", "type", "--delay", str(delay_per_key), c], check=True)
        return True
    except Exception as e:
        log_message(f"Failed to send keys to window ID '{win_id}': {e}", component="Interact", level="ERROR", color=Fore.RED)
        return False

def capture_window_image(window_rect: Tuple[int, int, int, int], output_path: str, verbose: bool = True) -> bool:
    x, y, w, h = window_rect
    try:
        cmd = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-f", "x11grab", "-video_size", f"{w}x{h}", "-i", f":0.0+{x},{y}", "-frames:v", "1", output_path]
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return True
    except Exception as e:
        log_message(f"ffmpeg screenshot failed: {e}", component="Capture", level="WARNING", color=Fore.YELLOW)
    
    try: # Fallback to pyautogui
        import pyautogui
        pyautogui.screenshot(region=(x, y, w, h)).save(output_path)
        return True
    except Exception as e:
        log_message(f"pyautogui screenshot failed: {e}", component="Capture", level="ERROR", color=Fore.RED)
        return False

def generate_random_mouse_actions(w: int, h: int, amount: int, include_click: bool, include_drag: bool, seed: str) -> list:
    rnd = random.Random(seed)
    actions = []
    action_types = ['move']
    if include_click: action_types.append('click')
    if include_drag: action_types.append('drag')

    for _ in range(amount):
        action_type = rnd.choice(action_types)
        rx1, ry1 = rnd.randint(0, max(0, w - 1)), rnd.randint(0, max(0, h - 1))
        if action_type == 'move':
            actions.append(('move', rx1, ry1))
        elif action_type == 'click':
            actions.append(('press', rx1, ry1))
            actions.append(('release', rx1, ry1))
        elif action_type == 'drag':
            rx2, ry2 = rnd.randint(0, max(0, w - 1)), rnd.randint(0, max(0, h - 1))
            actions.append(('press', rx1, ry1))
            actions.append(('move', rx2, ry2))
            actions.append(('release', rx2, ry2))
    return actions
