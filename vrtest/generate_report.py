#!/usr/bin/env python3
"""
Markdown Report Generator for Umfeld vs Processing Comparison Results

Generates a comprehensive markdown report from the output files produced by main.py
"""

import os
import sys
import argparse
import json
import re
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from pathlib import Path
import glob

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
    status: str = "unknown"  # "success", "partial", "failed"
    file_type: str = "unknown"  # "image", "video"
    metadata: Dict = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}
        
        # Determine status
        if self.comparison_file and os.path.exists(self.comparison_file):
            self.status = "success"
        elif self.umfeld_file or self.processing_file:
            self.status = "partial"
        else:
            self.status = "failed"
        
        # Determine file type
        if self.comparison_file:
            self.file_type = "video" if self.comparison_file.lower().endswith(('.mp4', '.avi', '.mov')) else "image"


def extract_metadata(file_path: str) -> Dict:
    """Extract metadata from image or video file"""
    if not os.path.exists(file_path):
        return {}
    
    metadata = {}
    
    try:
        # Basic file info
        stat = os.stat(file_path)
        metadata['file_size'] = format_file_size(stat.st_size)
        metadata['created_at'] = datetime.fromtimestamp(stat.st_mtime).strftime('%Y-%m-%d %H:%M:%S')
        
        # File type specific metadata
        if file_path.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp')):
            if PIL_AVAILABLE:
                try:
                    with Image.open(file_path) as img:
                        metadata['dimensions'] = f"{img.width}x{img.height}"
                        metadata['file_type'] = f"{img.format} Image"
                except Exception as e:
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
                except Exception as e:
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
        if len(parts) >= 2:
            return f"{parts[0]}/{parts[1]}"
        elif len(parts) >= 1:
            return parts[0]
    except ValueError:
        pass
    return "Unknown"


def collect_all_results(root_dir: str) -> Dict[str, ProjectResult]:
    """Collect all result files and organize by project"""
    results = {}
    root_path = Path(root_dir)
    
    # Find all comparison files as they indicate completed projects
    comparison_files = list(root_path.rglob("comparison-*.png")) + list(root_path.rglob("comparison-*.mp4"))
    
    for comp_file in comparison_files:
        # Extract project name from comparison file
        filename = comp_file.name
        if filename.startswith("comparison-"):
            project_name = filename[11:].rsplit('.', 1)[0]  # Remove "comparison-" prefix and extension
            
            project_dir = comp_file.parent
            category = get_category_from_path(str(project_dir), root_dir)
            
            # Look for individual files - try multiple naming patterns
            umfeld_file = None
            processing_file = None
            
            for ext in ['.png', '.mp4']:
                # Try exact match first
                umfeld_path = project_dir / f"umfeld_{project_name}{ext}"
                if umfeld_path.exists():
                    umfeld_file = str(umfeld_path)
                
                # Look for processing file - it might have different capitalization
                # Search for any processing_*.ext file in the same directory
                processing_pattern = f"processing_*{ext}"
                processing_matches = list(project_dir.glob(processing_pattern))
                if processing_matches:
                    processing_file = str(processing_matches[0])  # Take the first match
            
            # Extract metadata from comparison file
            metadata = extract_metadata(str(comp_file))
            
            results[project_name] = ProjectResult(
                project_name=project_name,
                category=category,
                umfeld_file=umfeld_file,
                processing_file=processing_file,
                comparison_file=str(comp_file),
                project_path=str(project_dir),
                metadata=metadata
            )
    
    return results


def parse_log_file(log_path: str) -> Dict:
    """Parse log file for execution details and errors"""
    log_info = {
        'start_time': None,
        'end_time': None,
        'total_duration': None,
        'errors': [],
        'project_timings': {}
    }
    
    if not os.path.exists(log_path):
        return log_info
    
    try:
        with open(log_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        for line in lines:
            line = line.strip()
            
            # Extract start time
            if "Test Run Started" in line:
                match = re.search(r'\[(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\]', line)
                if match:
                    log_info['start_time'] = match.group(1)
            
            # Extract end time
            elif "Test Run Finished" in line:
                match = re.search(r'\[(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\]', line)
                if match:
                    log_info['end_time'] = match.group(1)
            
            # Extract total duration
            elif "Total script execution time:" in line:
                match = re.search(r'(\d+\.\d+)s', line)
                if match:
                    log_info['total_duration'] = f"{match.group(1)}s"
            
            # Extract errors
            elif "[ERROR]" in line:
                log_info['errors'].append(line)
            
            # Extract project timings
            elif "Total processing time:" in line:
                match = re.search(r'\[.*?\] \[.*?\] \[(\w+)-Total\].*?(\d+\.\d+)s', line)
                if match:
                    project_type, duration = match.groups()
                    # Would need project name from context - simplified for now
    
    except Exception as e:
        print(f"Warning: Could not parse log file {log_path}: {e}")
    
    return log_info


class MarkdownReportGenerator:
    """Generate markdown report from project results"""
    
    def __init__(self, args):
        self.args = args
        self.report_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        self.vscode_friendly = getattr(args, 'vscode_friendly', False)
    
    def generate_full_report(self, results: Dict[str, ProjectResult], log_info: Dict = None) -> str:
        """Generate complete markdown report"""
        sections = [
            self.generate_header(),
            self.generate_summary_section(results),
            self.generate_category_table(results),
            self.generate_visual_section(results),
            self.generate_failed_section(results),
            self.generate_execution_details(log_info) if log_info else ""
        ]
        
        return "\n\n".join(filter(None, sections))
    
    def generate_header(self) -> str:
        """Generate report header"""
        return f"""# {self.args.title}
*Generated on: {self.report_time}*"""
    
    def generate_summary_section(self, results: Dict[str, ProjectResult]) -> str:
        """Generate executive summary"""
        total = len(results)
        successful = sum(1 for r in results.values() if r.status == "success")
        partial = sum(1 for r in results.values() if r.status == "partial")
        failed = sum(1 for r in results.values() if r.status == "failed")
        
        images = sum(1 for r in results.values() if r.file_type == "image")
        videos = sum(1 for r in results.values() if r.file_type == "video")
        
        success_rate = (successful / total * 100) if total > 0 else 0
        partial_rate = (partial / total * 100) if total > 0 else 0
        failed_rate = (failed / total * 100) if total > 0 else 0
        
        image_rate = (images / total * 100) if total > 0 else 0
        video_rate = (videos / total * 100) if total > 0 else 0
        
        return f"""## 📊 Executive Summary
- **Total Projects**: {total}
- **Successful Comparisons**: {successful} ({success_rate:.1f}%)
- **Partial Results**: {partial} ({partial_rate:.1f}%)
- **Failed Projects**: {failed} ({failed_rate:.1f}%)
- **Static Screenshots**: {images} ({image_rate:.1f}%)
- **Interactive Videos**: {videos} ({video_rate:.1f}%)"""
    
    def generate_category_table(self, results: Dict[str, ProjectResult]) -> str:
        """Generate results organized by category"""
        # Group by category
        categories = {}
        for result in results.values():
            if result.category not in categories:
                categories[result.category] = []
            categories[result.category].append(result)
        
        sections = ["## 📂 Results by Category"]
        
        for category in sorted(categories.keys()):
            projects = sorted(categories[category], key=lambda x: x.project_name)
            sections.append(f"\n### {category} ({len(projects)} projects)")
            
            # Generate table
            table_lines = [
                "| Project | Umfeld | Processing | Comparison | Status |",
                "|---------|--------|------------|------------|--------|"
            ]
            
            for project in projects:
                umfeld_status = "✅" if project.umfeld_file and os.path.exists(project.umfeld_file) else "❌"
                processing_status = "✅" if project.processing_file and os.path.exists(project.processing_file) else "❌"
                
                if project.comparison_file and os.path.exists(project.comparison_file):
                    comparison_link = f"[View]({os.path.abspath(project.comparison_file)})"
                    status_icon = "✅ Success"
                elif project.status == "partial":
                    comparison_link = "⚠️ Partial"
                    status_icon = "⚠️ Partial"
                else:
                    comparison_link = "❌ Failed"
                    status_icon = "❌ Failed"
                
                table_lines.append(
                    f"| {project.project_name} | {umfeld_status} | {processing_status} | {comparison_link} | {status_icon} |"
                )
            
            sections.append("\n".join(table_lines))
        
        return "\n".join(sections)
    
    def generate_visual_section(self, results: Dict[str, ProjectResult]) -> str:
        """Generate visual results section with embedded media"""
        sections = ["## 🖼️ Visual Results"]
        
        # Only show successful projects with comparison files
        successful_projects = [r for r in results.values() if r.status == "success" and r.comparison_file]
        successful_projects.sort(key=lambda x: (x.category, x.project_name))
        
        for project in successful_projects:
            sections.append(f"\n### {project.category}/{project.project_name}")
            
            # Add project info
            info_lines = [f"**Type**: {project.file_type.title()}"]
            
            if project.metadata:
                if 'dimensions' in project.metadata:
                    info_lines.append(f"**Dimensions**: {project.metadata['dimensions']}")
                if 'duration' in project.metadata:
                    info_lines.append(f"**Duration**: {project.metadata['duration']}")
                if 'file_size' in project.metadata:
                    info_lines.append(f"**Size**: {project.metadata['file_size']}")
            
            sections.append(" | ".join(info_lines))
            
            # Embed media with absolute path
            abs_path = os.path.abspath(project.comparison_file)
            sections.append(self.embed_media(abs_path, project.file_type))
            
            # Add individual results if available
            individual_sections = []
            if project.umfeld_file and os.path.exists(project.umfeld_file):
                umfeld_abs = os.path.abspath(project.umfeld_file)
                individual_sections.append(f"**Umfeld**: {self.embed_media(umfeld_abs, project.file_type, inline=False)}")
            
            if project.processing_file and os.path.exists(project.processing_file):
                processing_abs = os.path.abspath(project.processing_file)
                individual_sections.append(f"**Processing**: {self.embed_media(processing_abs, project.file_type, inline=False)}")
            
            if individual_sections:
                sections.append("\n**Individual Results:**")
                sections.extend(individual_sections)
        
        return "\n".join(sections)
    
    def embed_media(self, file_path: str, file_type: str, inline: bool = True) -> str:
        """Generate HTML/markdown for embedding media"""
        if file_type == "video":
            if inline:
                if self.vscode_friendly:
                    # VSCode-friendly version - only links
                    return f"🎥 **[▶️ Play Video]({file_path})** (Click to open in external player)"
                else:
                    # Standard HTML5 video with fallback
                    return f"""<video controls width="600" style="max-width: 100%;">
  <source src="{file_path}" type="video/mp4">
  🎥 <strong><a href="{file_path}">▶️ Click here to play video</a></strong> (VSCode users: click link to open in external player)
</video>

**VSCode Users:** Click this link to play → 🎥 **[▶️ Play Video]({file_path})**"""
            else:
                return f"[🎥 View Video]({file_path})"
        else:
            # Image
            if inline:
                return f"![Comparison Result]({file_path})"
            else:
                return f"[View Image]({file_path})"
    
    def generate_failed_section(self, results: Dict[str, ProjectResult]) -> str:
        """Generate section for failed projects"""
        failed_projects = [r for r in results.values() if r.status in ["failed", "partial"]]
        
        if not failed_projects:
            return ""
        
        sections = ["## ❌ Failed & Partial Results"]
        
        for project in sorted(failed_projects, key=lambda x: (x.status, x.project_name)):
            status_emoji = "⚠️" if project.status == "partial" else "❌"
            sections.append(f"\n### {status_emoji} {project.project_name} ({project.category})")
            
            details = []
            if project.umfeld_file and os.path.exists(project.umfeld_file):
                details.append("✅ Umfeld version generated")
            else:
                details.append("❌ Umfeld version failed")
            
            if project.processing_file and os.path.exists(project.processing_file):
                details.append("✅ Processing version generated")
            else:
                details.append("❌ Processing version failed")
            
            if not project.comparison_file or not os.path.exists(project.comparison_file):
                details.append("❌ Comparison not generated")
            
            sections.extend(f"- {detail}" for detail in details)
        
        return "\n".join(sections)
    
    def generate_execution_details(self, log_info: Dict) -> str:
        """Generate execution details section"""
        if not log_info:
            return ""
        
        sections = ["## 📝 Execution Details"]
        
        if log_info.get('start_time'):
            sections.append(f"- **Start Time**: {log_info['start_time']}")
        if log_info.get('end_time'):
            sections.append(f"- **End Time**: {log_info['end_time']}")
        if log_info.get('total_duration'):
            sections.append(f"- **Total Duration**: {log_info['total_duration']}")
        
        if self.args.include_logs and hasattr(self.args, 'log_file') and self.args.log_file:
            log_abs_path = os.path.abspath(self.args.log_file)
            sections.append(f"- **Log File**: [View Log]({log_abs_path})")
        
        if log_info.get('errors'):
            sections.append(f"\n### Recent Errors ({len(log_info['errors'])} found)")
            for error in log_info['errors'][-5:]:  # Show last 5 errors
                # Clean up the error message
                clean_error = re.sub(r'\[.*?\]', '', error).strip()
                sections.append(f"- {clean_error}")
        
        return "\n".join(sections)


def find_latest_log_file(script_dir: str) -> Optional[str]:
    """Find the most recent log file"""
    log_pattern = os.path.join(script_dir, "run_log_*.txt")
    log_files = glob.glob(log_pattern)
    
    if log_files:
        # Return the most recently modified log file
        return max(log_files, key=os.path.getmtime)
    
    return None


def main():
    parser = argparse.ArgumentParser(description="Generate markdown report from Umfeld vs Processing comparison results")
    parser.add_argument("--input-dir", type=str, default="../Processing/", 
                       help="Root directory containing result files (default: ../Processing/)")
    parser.add_argument("--output", type=str, 
                       default=f"comparison_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md",
                       help="Output markdown file name")
    parser.add_argument("--title", type=str, default="Umfeld vs Processing Comparison Report",
                       help="Report title")
    parser.add_argument("--include-logs", action="store_true",
                       help="Include log file analysis in the report")
    parser.add_argument("--log-file", type=str,
                       help="Specific log file to analyze (auto-detect if not specified)")
    parser.add_argument("--category", type=str,
                       help="Generate report for specific category only")
    parser.add_argument("--vscode-friendly", action="store_true",
                       help="Generate VSCode markdown preview-friendly report (video links instead of HTML5 video tags)")
    
    args = parser.parse_args()
    
    print(f"🔍 Collecting results from: {os.path.abspath(args.input_dir)}")
    
    # Collect all results
    results = collect_all_results(args.input_dir)
    
    if not results:
        print("❌ No results found! Make sure you've run main.py first.")
        sys.exit(1)
    
    # Filter by category if specified
    if args.category:
        filtered_results = {k: v for k, v in results.items() if v.category == args.category}
        if not filtered_results:
            print(f"❌ No results found for category '{args.category}'")
            available_categories = sorted(set(r.category for r in results.values()))
            print(f"Available categories: {', '.join(available_categories)}")
            sys.exit(1)
        results = filtered_results
        print(f"📂 Filtered to category '{args.category}': {len(results)} projects")
    
    print(f"📊 Found {len(results)} projects:")
    success_count = sum(1 for r in results.values() if r.status == "success")
    partial_count = sum(1 for r in results.values() if r.status == "partial")
    failed_count = sum(1 for r in results.values() if r.status == "failed")
    print(f"   ✅ {success_count} successful, ⚠️ {partial_count} partial, ❌ {failed_count} failed")
    
    # Parse log file if requested
    log_info = None
    if args.include_logs:
        log_file = args.log_file
        if not log_file:
            log_file = find_latest_log_file(os.path.dirname(os.path.abspath(__file__)))
        
        if log_file and os.path.exists(log_file):
            print(f"📝 Analyzing log file: {log_file}")
            log_info = parse_log_file(log_file)
            args.log_file = log_file
        elif args.include_logs:
            print("⚠️ No log file found, skipping log analysis")
    
    # Generate report
    print(f"📋 Generating report...")
    generator = MarkdownReportGenerator(args)
    report_content = generator.generate_full_report(results, log_info)
    
    # Save report
    output_path = os.path.abspath(args.output)
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(report_content)
    
    print(f"✅ Report generated: {output_path}")
    print(f"📖 View with: markdown viewer or convert to HTML")


if __name__ == "__main__":
    main()