#!/usr/bin/env python3
"""
HTML Report Generator for Umfeld vs Processing Comparison Results

Generates a comprehensive HTML report from the output files produced by main.py,
including source code analysis for notes, FIXMEs, and unimplemented features.
"""

import os
import sys
import argparse
import json
import re
import html
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from pathlib import Path
import glob

# Import project discovery functions from utils
from utils import get_all_umfeld_processing_examples

try:
    from PIL import Image
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False
    print("Warning: PIL not available. Image metadata extraction will be limited.")

try:
    import cv2
    CV2_AVAILABLE = True
except ImportError:
    CV2_AVAILABLE = False
    print("Warning: OpenCV not available. Video metadata extraction will be limited.")


@dataclass
class ProjectResult:
    """Data class to hold information about a single project's results"""
    project_name: str
    category: str
    umfeld_file: Optional[str] = None
    processing_file: Optional[str] = None
    comparison_file: Optional[str] = None
    project_path: Optional[str] = None
    status: str = "unknown"  # success, build_failed, window_failed, concat_failed, unknown
    file_type: str = "unknown"
    metadata: Dict = field(default_factory=dict)
    notes: List[str] = field(default_factory=list)
    fixmes: List[str] = field(default_factory=list)
    unimplementeds: List[str] = field(default_factory=list)
    log_errors: List[str] = field(default_factory=list)
    log_warnings: List[str] = field(default_factory=list)
    log_failures: List[str] = field(default_factory=list)
    compile_errors: List[str] = field(default_factory=list)
    window_errors: List[str] = field(default_factory=list)
    concat_errors: List[str] = field(default_factory=list)

    def __post_init__(self):
        # Status is now determined by log analysis and file existence
        if self.comparison_file and os.path.exists(self.comparison_file):
            self.status = "success"
        elif self.compile_errors:
            self.status = "build_failed"
        elif self.window_errors:
            self.status = "window_failed"
        elif self.concat_errors:
            self.status = "concat_failed"
        else:
            self.status = "unknown"

        if self.comparison_file:
            self.file_type = "video" if self.comparison_file.lower().endswith(('.mp4', '.avi', '.mov')) else "image"

    @property
    def has_issues(self) -> bool:
        return bool(self.notes or self.fixmes or self.unimplementeds or self.log_errors or self.log_warnings or self.log_failures or self.compile_errors or self.window_errors or self.concat_errors)


def extract_metadata(file_path: str) -> Dict:
    """Extract metadata from image or video file"""
    if not os.path.exists(file_path):
        return {}
    
    metadata = {}
    try:
        stat = os.stat(file_path)
        metadata['file_size'] = format_file_size(stat.st_size)
        metadata['created_at'] = datetime.fromtimestamp(stat.st_mtime).strftime('%Y-%m-%d %H:%M:%S')
        
        if file_path.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp')):
            if PIL_AVAILABLE:
                try:
                    with Image.open(file_path) as img:
                        metadata['dimensions'] = f"{img.width}x{img.height}"
                        metadata['file_type'] = f"{img.format} Image"
                except Exception:
                    metadata['file_type'] = "Image"
            else:
                metadata['file_type'] = "Image"
                
        elif file_path.lower().endswith(('.mp4', '.avi', '.mov')):
            if CV2_AVAILABLE:
                try:
                    cap = cv2.VideoCapture(file_path)
                    if cap.isOpened():
                        fps = cap.get(cv2.CAP_PROP_FPS)
                        frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
                        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                        
                        if fps > 0:
                            duration = frame_count / fps
                            metadata['duration'] = f"{duration:.1f}s"
                        metadata['dimensions'] = f"{width}x{height}"
                        metadata['file_type'] = "MP4 Video"
                    cap.release()
                except Exception:
                    metadata['file_type'] = "Video"
            else:
                metadata['file_type'] = "Video"
    except Exception as e:
        print(f"Warning: Could not extract metadata from {file_path}: {e}")
    return metadata


def format_file_size(bytes_size: int) -> str:
    """Convert bytes to human readable format"""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if bytes_size < 1024.0:
            return f"{bytes_size:.1f} {unit}"
        bytes_size /= 1024.0
    return f"{bytes_size:.1f} TB"


def get_category_from_path(project_path: str, root_dir: str) -> str:
    """Extract category from project path"""
    try:
        rel_path = os.path.relpath(project_path, root_dir)
        parts = rel_path.split(os.sep)
        return "/".join(parts[:2]) if len(parts) >= 2 else parts[0]
    except ValueError:
        return "Unknown"


def analyze_source_code(project_path: str) -> Tuple[List[str], List[str], List[str]]:
    """Analyze source files for notes, fixmes, and unimplemented tags."""
    notes, fixmes, unimplementeds = [], [], []
    source_files = glob.glob(os.path.join(project_path, "**", "*.cpp"), recursive=True) + \
                   glob.glob(os.path.join(project_path, "**", "*.h"), recursive=True)

    note_pattern = re.compile(r'/\*+\s*\n\s*note:(.*?)\*/', re.DOTALL | re.IGNORECASE)
    keyword_pattern = re.compile(r'.*(unimplemented|fixme).*', re.IGNORECASE)

    for file_path in source_files:
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            for match in note_pattern.finditer(content):
                note_text = match.group(1).strip()
                notes.append(f"**Note from {os.path.basename(file_path)}:**\n```\n{note_text}\n```")

            lines = content.splitlines()
            for i, line in enumerate(lines):
                if keyword_pattern.search(line):
                    context_start = max(0, i - 3)
                    context_end = min(len(lines), i + 4)
                    context = "\n".join(lines[context_start:context_end])
                    
                    if "unimplemented" in line.lower():
                        unimplementeds.append(f"**Unimplemented in {os.path.basename(file_path)} (line {i+1}):**\n```cpp\n{context}\n```")
                    if "fixme" in line.lower():
                        fixmes.append(f"**FIXME in {os.path.basename(file_path)} (line {i+1}):**\n```cpp\n{context}\n```")

        except Exception as e:
            print(f"Warning: Could not analyze source file {file_path}: {e}")
            
    return notes, fixmes, unimplementeds


def collect_all_results(root_dir: str, include_logs: bool = False) -> Dict[str, ProjectResult]:
    """Collect results for all projects, including failed ones"""
    results = {}
    
    # Get all Umfeld projects (same logic as main.py)
    all_projects = get_all_umfeld_processing_examples(root_dir)
    
    # Look for comparison files in the comparison directory
    comparison_dir = Path(os.path.dirname(os.path.abspath(__file__))) / "comparison"
    comparison_files_dict = {}
    
    if comparison_dir.exists():
        comparison_files = list(comparison_dir.glob("comparison-*.png")) + list(comparison_dir.glob("comparison-*.mp4"))
        for comp_file in comparison_files:
            if comp_file.name.startswith("comparison-"):
                project_name = comp_file.name[11:].rsplit('.', 1)[0]
                comparison_files_dict[project_name] = comp_file
    
    # Process all projects (both successful and failed)
    for project_path in all_projects:
        project_name = os.path.basename(project_path)
        
        # Check if there's a comparison file for this project
        comp_file = comparison_files_dict.get(project_name)
        comparison_file_path = str(comp_file) if comp_file else None
        
        # Get category from project path
        category = get_category_from_path(project_path, root_dir)
        
        # Extract metadata if comparison file exists
        metadata = {}
        if comp_file:
            metadata = extract_metadata(str(comp_file))
        
        # Analyze source code
        notes, fixmes, unimplementeds = analyze_source_code(project_path)
        
        # Analyze log files if requested
        log_errors, log_warnings, log_failures = [], [], []
        compile_errors, window_errors, concat_errors = [], [], []
        if include_logs:
            log_errors, log_warnings, log_failures, compile_errors, window_errors, concat_errors = analyze_log_files(project_name)
        
        results[project_name] = ProjectResult(
            project_name=project_name,
            category=category,
            umfeld_file=None,  # Individual files are deleted after concatenation
            processing_file=None,
            comparison_file=comparison_file_path,
            project_path=project_path,
            metadata=metadata,
            notes=notes,
            fixmes=fixmes,
            unimplementeds=unimplementeds,
            log_errors=log_errors,
            log_warnings=log_warnings,
            log_failures=log_failures,
            compile_errors=compile_errors,
            window_errors=window_errors,
            concat_errors=concat_errors
        )
    return results


def analyze_log_files(project_name: str) -> Tuple[List[str], List[str], List[str], List[str], List[str], List[str]]:
    """Analyze log files for errors, warnings, failures, and specific error types for a specific project"""
    errors, warnings, failures = [], [], []
    compile_errors, window_errors, concat_errors = [], [], []
    
    # Find the most recent log file
    script_dir = os.path.dirname(os.path.abspath(__file__))
    log_files = glob.glob(os.path.join(script_dir, "run_log_*.txt"))
    
    if not log_files:
        return errors, warnings, failures, compile_errors, window_errors, concat_errors
    
    # Use the most recent log file
    most_recent_log = max(log_files, key=os.path.getmtime)
    
    try:
        with open(most_recent_log, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        
        lines = content.splitlines()
        project_section = False
        
        for i, line in enumerate(lines):
            # Check if we're in the relevant project section
            if f"Processing project: '{project_name}'" in line:
                project_section = True
                continue
            elif "Processing project:" in line and project_section:
                # We've moved to the next project
                break
            elif "--- Test Run Finished ---" in line:
                break
                
            if project_section:
                # Look for specific error types first
                if "COMPILE_ERROR:" in line:
                    compile_errors.append(f"**Compile Error in {project_name}:**\\n```\\n{line.strip()}\\n```")
                elif "BUILD_ERROR:" in line:
                    compile_errors.append(f"**Build Error in {project_name}:**\\n```\\n{line.strip()}\\n```")
                elif "WINDOW_NOT_FOUND:" in line:
                    window_errors.append(f"**Window Detection Error in {project_name}:**\\n```\\n{line.strip()}\\n```")
                elif "CONCAT_ERROR:" in line:
                    concat_errors.append(f"**Concatenation Error in {project_name}:**\\n```\\n{line.strip()}\\n```")
                elif "CONCAT_SKIP:" in line:
                    concat_errors.append(f"**Concatenation Skipped in {project_name}:**\\n```\\n{line.strip()}\\n```")
                # Then look for general ERROR level messages
                elif "[ERROR]" in line or "level=\"ERROR\"" in line:
                    # Get some context around the error
                    context_start = max(0, i - 1)
                    context_end = min(len(lines), i + 2)
                    context_lines = lines[context_start:context_end]
                    error_context = "\\n".join(context_lines)
                    errors.append(f"**General Error in {project_name}:**\\n```\\n{error_context}\\n```")
                
                # Look for WARNING level messages
                elif "[WARNING]" in line or "level=\"WARNING\"" in line:
                    warnings.append(f"**Warning in {project_name}:**\\n```\\n{line.strip()}\\n```")
                
                # Look for failure indicators
                elif any(fail_word in line.lower() for fail_word in ["failed", "failure", "could not", "unable to", "timeout"]):
                    failures.append(f"**Failure in {project_name}:**\\n```\\n{line.strip()}\\n```")
                    
    except Exception as e:
        print(f"Warning: Could not analyze log file {most_recent_log}: {e}")
    
    return errors, warnings, failures, compile_errors, window_errors, concat_errors


def count_interactives(json_path: str) -> int:
    """Count interactive projects from test_props.json"""
    if not os.path.exists(json_path):
        print(f"Warning: {json_path} not found. Cannot count interactive projects.")
        return 0
    try:
        with open(json_path, 'r') as f:
            data = json.load(f)
        
        interactive_count = 0
        for props in data.values():
            if isinstance(props, list) and props and props[0] != "animation":
                interactive_count += 1
        return interactive_count
    except Exception as e:
        print(f"Error reading or parsing {json_path}: {e}")
        return 0


class HTMLReportGenerator:
    """Generate HTML report from project results"""
    
    def __init__(self, args):
        self.args = args
        self.report_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    def generate_full_report(self, results: Dict[str, ProjectResult], interactive_count: int) -> str:
        if self.args.category:
            results = {k: v for k, v in results.items() if v.category == self.args.category}
            if not results:
                return "<h1>No results found for specified category.</h1>"

        issue_projects = {k: v for k, v in results.items() if v.has_issues}
        failed_projects = {k: v for k, v in results.items() if v.status != "success"}
        successful_projects = {k: v for k, v in results.items() if v.status == "success"}

        html_content = self.generate_html_header()
        html_content += "<div class=\"report-container\">"
        html_content += self.generate_summary_section(results, issue_projects, interactive_count)
        
        # Generate Table of Contents
        html_content += self.generate_toc(results, issue_projects)

        # Generate failed projects sections
        if failed_projects:
            build_failed = {k: v for k, v in failed_projects.items() if v.status == "build_failed"}
            window_failed = {k: v for k, v in failed_projects.items() if v.status == "window_failed"}
            concat_failed = {k: v for k, v in failed_projects.items() if v.status == "concat_failed"}
            unknown_failed = {k: v for k, v in failed_projects.items() if v.status == "unknown"}
            
            if build_failed:
                html_content += self.generate_table_section("🔨 Build/Compile Failures", build_failed, section_id="section-build-failed")
            if window_failed:
                html_content += self.generate_table_section("🪟 Window Detection Failures", window_failed, section_id="section-window-failed")
            if concat_failed:
                html_content += self.generate_table_section("🔗 Concatenation Failures", concat_failed, section_id="section-concat-failed")
            if unknown_failed:
                html_content += self.generate_table_section("❓ Unknown Failures", unknown_failed, section_id="section-unknown-failed")

        # Generate issues section for projects with code issues
        if issue_projects:
            html_content += self.generate_table_section("🚩 Projects with Code Issues", issue_projects, section_id="section-issues")
        
        # Generate successful projects by categories
        if successful_projects:
            html_content += f'<h2 id="section-successful">✅ Successful Projects</h2>'
            categories = {}
            for name, result in successful_projects.items():
                categories.setdefault(result.category, {})[name] = result
                
            for category in sorted(categories.keys()):
                html_content += self.generate_table_section(f"📂 {category}", categories[category], is_category=True, section_id=f"section-{category.replace('/', '-')}")
            
        html_content += "</div>"
        html_content += self.generate_html_footer()
        return html_content

    def generate_html_header(self) -> str:
        return f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>{self.args.title}</title>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/prism/1.29.0/themes/prism-tomorrow.min.css">
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Oxygen-Sans, Ubuntu, Cantarell, "Helvetica Neue", sans-serif; background-color: #f0f2f5; color: #333; }}
        .report-container {{ max-width: 1400px; margin: 2em auto; background: #fff; padding: 2em; border-radius: 8px; box-shadow: 0 4px 8px rgba(0,0,0,0.05); }}
        h1, h2 {{ color: #111; border-bottom: 1px solid #eaecef; padding-bottom: 0.3em; }}
        details {{ border: 1px solid #ddd; border-radius: 5px; margin-bottom: 1em; }}
        summary {{ font-weight: bold; padding: 1em; cursor: pointer; background-color: #f7f7f7; list-style-position: inside; }}
        table {{ border-collapse: collapse; width: 100%; table-layout: fixed; }}
        th, td {{ border: 1px solid #ddd; padding: 10px; text-align: left; vertical-align: top; word-wrap: break-word; }}
        th {{ background-color: #f2f2f2; }}
        tr {{ height: 40px; }}
        th:nth-child(1) {{ width: 25%; }}
        th:nth-child(2) {{ width: 10%; }}
        th:nth-child(3) {{ width: 65%; }}
        .tooltip {{ position: relative; display: inline-block; }}
        .tooltip .tooltip-content {{
            visibility: hidden; width: 320px; background-color: black; color: #fff;
            text-align: center; border-radius: 6px; padding: 5px;
            position: absolute; z-index: 1; bottom: 125%; left: 50%; margin-left: -160px;
            opacity: 0; transition: opacity 0.3s;
        }}
        .tooltip:hover .tooltip-content {{ visibility: visible; opacity: 1; }}
        .tooltip-content img, .tooltip-content video {{ max-width: 100%; height: auto; }}
        .modal {{ display: none; position: fixed; z-index: 1000; left: 0; top: 0; width: 100%; height: 100%; overflow: auto; background-color: rgba(0,0,0,0.85); }}
        .modal-content {{ margin: auto; display: block; max-width: 90%; max-height: 90%; position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%); }}
        .close {{ position: absolute; top: 15px; right: 35px; color: #f1f1f1; font-size: 40px; font-weight: bold; transition: 0.3s; }}
        .close:hover, .close:focus {{ color: #bbb; text-decoration: none; cursor: pointer; }}
        td details {{ border: none; margin: 0; }}
        td summary {{ padding: 0; background: none; font-weight: normal; display: inline-block; width: auto; cursor: pointer; }}
        td summary:hover {{ background-color: #8B0000; color: #fff; border-radius: 3px; padding: 2px 4px; }}
        td details[open] summary {{ margin-bottom: 8px; }}
        td summary:before {{ content: "▼ "; }}
        td details[open] summary:before {{ content: "▲ "; }}
        pre {{ background-color: #f6f8fa; border: 1px solid #ddd; border-radius: 4px; padding: 10px; white-space: pre-wrap; font-family: SFMono-Regular, Consolas, 'Liberation Mono', Menlo, monospace; font-size: 13px; }}
        strong {{ color: #111; }}
        /* Link and Hover Highlighting */
        a:hover, .tooltip a:hover {{
            background-color: #8B0000; /* Dark Red */
            color: #fff; /* Ensure text is readable on dark background */
            border-radius: 3px;
            padding: 2px 4px;
            text-decoration: none;
        }}
        .project-category-link {{
            font-size: 0.8em;
            color: #666;
            margin-left: 5px;
        }}
        .project-category-link a {{
            color: #007bff; /* Default link color */
            text-decoration: none;
        }}
        .project-category-link a:hover {{
            background-color: #8B0000; /* Dark Red */
            color: #fff; /* Ensure text is readable on dark background */
            border-radius: 3px;
            padding: 2px 4px;
            text-decoration: none;
        }}
        .toc ul {{
            list-style-type: none;
            padding: 0;
        }}
        .toc li {{
            margin-bottom: 5px;
        }}
        .toc a {{
            text-decoration: none;
            color: #007bff;
        }}
        .toc a:hover {{
            background-color: #8B0000;
            color: #fff;
            border-radius: 3px;
            padding: 2px 4px;
        }}
    </style>
</head>
<body>
    <h1>{self.args.title}</h1>
    <p><em>Generated on: {self.report_time}</em></p>
"""

    def generate_summary_section(self, results: Dict, issue_projects: Dict, interactive_count: int) -> str:
        total = len(results)
        
        # Count by status
        successful = sum(1 for r in results.values() if r.status == "success")
        build_failed = sum(1 for r in results.values() if r.status == "build_failed")
        window_failed = sum(1 for r in results.values() if r.status == "window_failed")
        concat_failed = sum(1 for r in results.values() if r.status == "concat_failed")
        unknown_failed = sum(1 for r in results.values() if r.status == "unknown")
        
        # Count source code issues
        unimplemented_count = sum(1 for r in issue_projects.values() if r.unimplementeds)
        fixme_count = sum(1 for r in issue_projects.values() if r.fixmes)
        
        return f"""
    <h2>📊 Executive Summary</h2>
    <ul>
        <li><strong>Total Projects:</strong> {total}</li>
        <li><strong>✅ Successful:</strong> {successful}</li>
        <li><strong>🔨 Build Failures:</strong> {build_failed}</li>
        <li><strong>🪟 Window Failures:</strong> {window_failed}</li>
        <li><strong>🔗 Concat Failures:</strong> {concat_failed}</li>
        <li><strong>❓ Unknown Issues:</strong> {unknown_failed}</li>
        <li><strong>Unimplemented Features:</strong> {unimplemented_count}</li>
        <li><strong>FIXME Items:</strong> {fixme_count}</li>
        <li><strong>Interactive Projects:</strong> {interactive_count}</li>
    </ul>
"""

    def generate_toc(self, results: Dict[str, ProjectResult], issue_projects: Dict[str, ProjectResult]) -> str:
        toc_html = "<h2>Table of Contents</h2><div class=\"toc\"><ul>"
        
        # Add failed projects sections
        failed_projects = {k: v for k, v in results.items() if v.status != "success"}
        if failed_projects:
            build_failed = sum(1 for r in failed_projects.values() if r.status == "build_failed")
            window_failed = sum(1 for r in failed_projects.values() if r.status == "window_failed") 
            concat_failed = sum(1 for r in failed_projects.values() if r.status == "concat_failed")
            unknown_failed = sum(1 for r in failed_projects.values() if r.status == "unknown")
            
            if build_failed > 0:
                toc_html += f'<li><a href="#section-build-failed">🔨 Build/Compile Failures ({build_failed} projects)</a></li>'
            if window_failed > 0:
                toc_html += f'<li><a href="#section-window-failed">🪟 Window Detection Failures ({window_failed} projects)</a></li>'
            if concat_failed > 0:
                toc_html += f'<li><a href="#section-concat-failed">🔗 Concatenation Failures ({concat_failed} projects)</a></li>'
            if unknown_failed > 0:
                toc_html += f'<li><a href="#section-unknown-failed">❓ Unknown Failures ({unknown_failed} projects)</a></li>'
        
        # Add issues section to TOC if applicable
        if issue_projects:
            toc_html += f'<li><a href="#section-issues">🚩 Projects with Code Issues ({len(issue_projects)} projects)</a></li>'

        # Add successful projects by categories
        successful_projects = {k: v for k, v in results.items() if v.status == "success"}
        if successful_projects:
            toc_html += f'<li><a href="#section-successful">✅ Successful Projects ({len(successful_projects)} projects)</a><ul>'
            categories = sorted(list(set(r.category for r in successful_projects.values())))
            for category in categories:
                category_id = f"section-{category.replace('/', '-')}"
                count = sum(1 for r in successful_projects.values() if r.category == category)
                toc_html += f'<li><a href="#{category_id}">📂 {category} ({count} projects)</a></li>'
            toc_html += '</ul></li>'
        
        toc_html += "</ul></div>"
        return toc_html

    def generate_table_section(self, title: str, projects: Dict[str, ProjectResult], is_category: bool = False, section_id: str = None) -> str:
        section_tag = f'<h2 id="{section_id}">{title}</h2>' if section_id else f'<h2>{title}</h2>'
        
        table_rows = ""
        for project in sorted(projects.values(), key=lambda p: p.project_name):
            comp_link = self.generate_comparison_link(project)
            notes_content = self.generate_notes_content(project)
            
            project_name_cell = project.project_name
            if not is_category and project.category: # Add category link for issue projects
                category_id = f"section-{project.category.replace('/', '-')}"
                project_name_cell += f'<div class="project-category-link">cat: <a href="#{category_id}">{project.category}</a></div>'

            table_rows += f"<tr><td>{project_name_cell}</td><td>{comp_link}</td><td>{notes_content}</td></tr>"
        
        table_html = f"""
        <table>
            <thead><tr><th>Project</th><th>Comparison</th><th>Notes</th></tr></thead>
            <tbody>{table_rows}</tbody>
        </table>
"""

        if is_category:
            return f"<details open><summary>{section_tag.replace('h2', 'span')}</summary>{table_html}</details>"
        else:
            return f"{section_tag}{table_html}"

    def generate_comparison_link(self, project: ProjectResult) -> str:
        if not project.comparison_file or not os.path.exists(project.comparison_file):
            # Show status-specific messages for failed projects
            if project.status == "build_failed":
                return "🔨 Build Failed"
            elif project.status == "window_failed":
                return "🪟 Window Not Found"
            elif project.status == "concat_failed":
                return "🔗 Concat Failed"
            else:
                return "❓ Unknown Issue"
        
        # Calculate relative path from HTML output file to comparison file
        html_output_dir = os.path.dirname(os.path.abspath(self.args.output))
        rel_path = os.path.relpath(project.comparison_file, html_output_dir)
        media_tag = f'<img src="{rel_path}" alt="Preview">' if project.file_type == 'image' else f'<video src="{rel_path}" autoplay muted loop></video>'

        return f'''
<div class="tooltip">
    <a href="#" onclick="openModal('{rel_path}', '{project.file_type}'); return false;">View</a>
    <div class="tooltip-content">{media_tag}</div>
</div>
'''

    def format_note(self, note_text: str) -> str:
        match = re.match(r'\*\*(.*?):\*\*\n```(cpp|c)?\n(.*?)\n```', note_text, re.DOTALL)
        if match:
            title, lang, code = match.groups()
            lang_class = f'language-{lang}' if lang else ''
            escaped_code = html.escape(code.strip())
            return f"<div><strong>{title.strip()}:</strong><pre><code class=\"{lang_class}\">{escaped_code}</code></pre></div>"
        return f"<p>{html.escape(note_text)}</p>" # Fallback

    def generate_notes_content(self, project: ProjectResult) -> str:
        if not project.has_issues:
            return "✔️"
        
        content = ""
        
        # Group issues by type
        issue_groups = [
            ("Source Code Issues", project.notes + project.fixmes + project.unimplementeds),
            ("Build/Compile Issues", project.compile_errors),
            ("Window Detection Issues", project.window_errors),
            ("Concatenation Issues", project.concat_errors),
            ("General Log Issues", project.log_errors + project.log_warnings + project.log_failures)
        ]
        
        for group_title, group_issues in issue_groups:
            if group_issues:
                content += f"<h4>{group_title}</h4>"
                for note in group_issues:
                    content += self.format_note(note)
        
        total_issues = sum(len(group[1]) for group in issue_groups)
        return f"<details><summary>Details ({total_issues})</summary>{content}</details>"

    def generate_html_footer(self) -> str:
        return '''
    <div id="myModal" class="modal">
        <span class="close" onclick="closeModal()">&times;</span>
        <div id="modal-content-container"></div>
    </div>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/prism/1.29.0/prism.min.js"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/prism/1.29.0/components/prism-cpp.min.js"></script>
    <script>
        var modal = document.getElementById('myModal');
        var modalContentContainer = document.getElementById('modal-content-container');

        function openModal(src, type) {
            modalContentContainer.innerHTML = '';
            var element = type === 'image' ? document.createElement('img') : document.createElement('video');
            element.src = src;
            element.className = 'modal-content';
            if (type === 'video') {
                element.controls = true;
                element.autoplay = true;
            }
            modalContentContainer.appendChild(element);
            modal.style.display = "block";
            Prism.highlightAll(); // Highlight code in modal
        }

        function closeModal() {
            modal.style.display = "none";
            modalContentContainer.innerHTML = '';
        }

        window.onclick = function(event) {
            if (event.target == modal) closeModal();
        }
        document.addEventListener('keydown', function(event) {
            if (event.key === "Escape") closeModal();
        });

        // Initial highlighting for content not in modal
        document.addEventListener('DOMContentLoaded', (event) => {
            Prism.highlightAll();
        });
    </script>
</body>
</html>
'''


def main():
    parser = argparse.ArgumentParser(description="Generate HTML report from Umfeld vs Processing comparison results")
    parser.add_argument("--input-dir", type=str, default="../Processing/", 
                       help="Root directory containing result files (default: ../Processing/)")
    parser.add_argument("--output", type=str, 
                       default="index.html",
                       help="Output HTML file name")
    parser.add_argument("--title", type=str, default="Umfeld vs Processing Comparison Report",
                       help="Report title")
    parser.add_argument("--category", type=str,
                       help="Generate report for specific category only")
    parser.add_argument("--props-file", type=str, default="test_props.json",
                       help="Path to test_props.json for interactive project counting")
    parser.add_argument("--include-logs", action="store_true",
                       help="Include log file analysis (errors, warnings, failures) in the report")
    
    args = parser.parse_args()
    
    print(f"🔍 Collecting results from: {os.path.abspath(args.input_dir)}")
    results = collect_all_results(args.input_dir, include_logs=args.include_logs)
    
    if not results:
        print("❌ No results found! Make sure you've run main.py first.")
        sys.exit(1)
        
    print(f"📊 Found {len(results)} projects.")
    
    interactive_count = count_interactives(args.props_file)
    print(f"    - {interactive_count} interactive projects identified.")
    
    if args.include_logs:
        log_issues_count = sum(1 for r in results.values() if r.log_errors or r.log_warnings or r.log_failures)
        compile_issues_count = sum(1 for r in results.values() if r.compile_errors)
        window_issues_count = sum(1 for r in results.values() if r.window_errors) 
        concat_issues_count = sum(1 for r in results.values() if r.concat_errors)
        print(f"    - {compile_issues_count} projects with compile/build issues found.")
        print(f"    - {window_issues_count} projects with window detection issues found.")
        print(f"    - {concat_issues_count} projects with concatenation issues found.")
        print(f"    - {log_issues_count} projects with other log issues found.")

    # Generate failed projects list
    failed_projects = [r for r in results.values() if r.status != "success"]
    if failed_projects:
        failed_list_path = os.path.abspath("failed_projects.txt")
        with open(failed_list_path, 'w', encoding='utf-8') as f:
            for project in sorted(failed_projects, key=lambda p: p.project_name):
                f.write(f"{project.project_path}\n")
        print(f"📝 Failed projects list generated: {failed_list_path} ({len(failed_projects)} projects)")

    print(f"📋 Generating report...")
    generator = HTMLReportGenerator(args)
    report_content = generator.generate_full_report(results, interactive_count)
    
    output_path = os.path.abspath(args.output)
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(report_content)
    
    print(f"✅ Report generated: {output_path}")
    print(f"📖 Open the HTML file in your browser to view.")


if __name__ == "__main__":
    main()
