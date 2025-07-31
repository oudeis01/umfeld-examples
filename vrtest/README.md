# Umfeld - Processing Visual Test Runner (Linux Only)

## ⚠️ Requirements & Installation

This project is designed for Linux environments only.


### 0. What it does
- Builds and runs Umfeld-Processing and the counterpart Processing examples.
- Records(5sec)/captures the output of each example.
- Creates a concatenated video/image of all succeeded examples.
- Stores the results in the respective Umfeld example directories.

### 1. Python & Pip
- Python 3.8+
- pip (Python package manager)

### 2. Python Dependencies
Install all required Python packages:

```bash
pip install -r requirements.txt
```

### 3. System Dependencies
The following system tools are required:
- `ffmpeg`
- `wmctrl`
- `x11-utils`
- `xclip`
- `processing-java`

Install on Ubuntu/Debian:
```bash
sudo apt update
sudo apt install ffmpeg wmctrl x11-utils xclip
```

Install on Arch Linux:
```bash
sudo pacman -S ffmpeg wmctrl xorg-xprop xclip
```




## Usage

### 1. Prepare Example Directories
- Place your Umfeld Processing examples in a directory (default: `../Processing/`)
- Place original Processing examples in a directory (default: `/opt/processing/modes/java/examples/`) (not sure if it is the standard location in any platform though)
- Ensure `test_props.json` is present in this directory.

### 2. Run the Script

```bash
python main.py
```

- You will be prompted to confirm the example directories.
- To run a specific project by name:

```bash
python main.py --project <project_name>
## example
python main.py --project "conditionals_1"
```

- Please know that the project name is intended to be the same as I named it inside the `Processing/` directory. In general, the names are similar to the original Processing examples but they are all `lowercase` and `_` is put between words. e.g. `MouseSignals` becomes `mouse_signals`.

- To specify custom directories:

```bash
python main.py --umfeld_example_dir <umfeld_dir> --processing_example_dir <processing_dir>
```

- To run all the projects in a specific category:

```bash
python main.py --category <category_name>
## example
python main.py --category Basics/Image
```

- You cannot combine `--project` and `--category` options. Use one or the other.

```bash
python main.py --category Basics/Image
python main.py --project brightness
python main.py --project "conditionals_1" --umfeld_example_dir <umfeld_dir> --processing_example_dir <processing_dir>
```


### 3. Output
- Logs are saved as `run_log_YYYYMMDD_HHMMSS.txt` in this directory.
- Video/image results and comparison files are saved in each example's directory.

### 4. Generate a Markdown Report
- To generate a Markdown report of the results, run:

```bash
python generate_report.py
```

- I found it better to have a single page report rather than opening multiple files.

## Notes
- Not sure how to call it, I thought of it similar to the visual regression testing, though doesn't make sense to do such test in creative coding.
- Only tested on Linux/X11. macOS/Windows support is partial or mostly unimplemented.