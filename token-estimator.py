#!/usr/bin/env python3
"""
Token Estimation Script for Code Files
Estimates the total token count for all files in a directory to help plan uploads to LLM context windows.
"""

"""
# Analyze current directory with default 200k token limit
python token_estimator.py .

# Analyze specific directory
python token_estimator.py /path/to/your/project

# Specify custom token limit
python token_estimator.py /path/to/your/project --limit 100000

# Set maximum file size to process (default is 10MB)
python token_estimator.py /path/to/your/project --max-file-size 5
"""


import os
import sys
from pathlib import Path
from collections import defaultdict
import argparse

# Token estimation multipliers by file extension
TOKEN_MULTIPLIERS = {
    '.py': 15,      # Python
    '.js': 18,      # JavaScript
    '.jsx': 18,     # React
    '.ts': 18,      # TypeScript
    '.tsx': 18,     # TypeScript React
    '.java': 22,    # Java
    '.c': 20,       # C
    '.cpp': 20,     # C++
    '.cs': 22,      # C#
    '.go': 16,      # Go
    '.rs': 18,      # Rust
    '.rb': 16,      # Ruby
    '.php': 20,     # PHP
    '.swift': 20,   # Swift
    '.kt': 22,      # Kotlin
    '.html': 12,    # HTML
    '.css': 12,     # CSS
    '.scss': 12,    # SCSS
    '.json': 15,    # JSON
    '.xml': 15,     # XML
    '.yaml': 12,    # YAML
    '.yml': 12,     # YAML
    '.md': 10,      # Markdown
    '.txt': 8,      # Plain text
    '.sh': 15,      # Shell scripts
    '.sql': 15,     # SQL
}

# Common directories to skip
SKIP_DIRS = {
    '.git', '__pycache__', 'node_modules', '.idea', '.vscode', 
    'venv', 'env', '.env', 'dist', 'build', 'target', '.next',
    'coverage', '.pytest_cache', '.mypy_cache', 'vendor'
}

# Binary file extensions to skip
SKIP_EXTENSIONS = {
    '.pyc', '.pyo', '.so', '.dll', '.dylib', '.exe', '.bin',
    '.jpg', '.jpeg', '.png', '.gif', '.ico', '.svg', '.webp',
    '.mp3', '.mp4', '.avi', '.mov', '.wav', '.flac',
    '.zip', '.tar', '.gz', '.rar', '.7z',
    '.pdf', '.doc', '.docx', '.xls', '.xlsx',
    '.db', '.sqlite', '.sqlite3'
}

def estimate_tokens(char_count, file_extension=None):
    """Estimate token count from character count."""
    # Base estimation: 1 token ≈ 3.5 characters
    base_tokens = char_count / 3.5
    
    # Apply language-specific multiplier if available
    if file_extension and file_extension.lower() in TOKEN_MULTIPLIERS:
        lines = char_count / 80  # Rough estimate of lines (80 chars per line)
        return int(lines * TOKEN_MULTIPLIERS[file_extension.lower()])
    
    # Default estimation with 1.2x multiplier for safety
    return int(base_tokens * 1.2)

def should_skip_file(file_path):
    """Check if file should be skipped."""
    # Skip hidden files
    if file_path.name.startswith('.'):
        return True
    
    # Skip binary files
    if file_path.suffix.lower() in SKIP_EXTENSIONS:
        return True
    
    return False

def format_size(size_bytes):
    """Format byte size to human readable format."""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.1f} TB"

def analyze_directory(directory_path, max_file_size_mb=10):
    """Analyze all files in directory and estimate tokens."""
    directory = Path(directory_path)
    
    if not directory.exists():
        print(f"Error: Directory '{directory}' does not exist.")
        return
    
    if not directory.is_dir():
        print(f"Error: '{directory}' is not a directory.")
        return
    
    stats = {
        'total_chars': 0,
        'total_tokens': 0,
        'total_files': 0,
        'skipped_files': 0,
        'errors': 0,
        'by_extension': defaultdict(lambda: {'files': 0, 'chars': 0, 'tokens': 0}),
        'largest_files': []
    }
    
    max_size_bytes = max_file_size_mb * 1024 * 1024
    
    print(f"Analyzing directory: {directory.absolute()}")
    print(f"Skipping files larger than {max_file_size_mb}MB")
    print("-" * 80)
    
    # Walk through directory
    for root, dirs, files in os.walk(directory):
        # Skip certain directories
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        
        root_path = Path(root)
        
        for file_name in files:
            file_path = root_path / file_name
            
            if should_skip_file(file_path):
                stats['skipped_files'] += 1
                continue
            
            try:
                # Check file size
                file_size = file_path.stat().st_size
                if file_size > max_size_bytes:
                    stats['skipped_files'] += 1
                    print(f"Skipping large file: {file_path.relative_to(directory)} ({format_size(file_size)})")
                    continue
                
                # Read file content
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                    char_count = len(content)
                    
                    # Estimate tokens
                    tokens = estimate_tokens(char_count, file_path.suffix)
                    
                    # Update statistics
                    stats['total_chars'] += char_count
                    stats['total_tokens'] += tokens
                    stats['total_files'] += 1
                    
                    ext_stats = stats['by_extension'][file_path.suffix.lower() or '.no_ext']
                    ext_stats['files'] += 1
                    ext_stats['chars'] += char_count
                    ext_stats['tokens'] += tokens
                    
                    # Track largest files
                    relative_path = file_path.relative_to(directory)
                    stats['largest_files'].append({
                        'path': str(relative_path),
                        'chars': char_count,
                        'tokens': tokens,
                        'size': file_size
                    })
                    
            except Exception as e:
                stats['errors'] += 1
                print(f"Error reading {file_path.relative_to(directory)}: {e}")
    
    # Sort largest files by token count
    stats['largest_files'].sort(key=lambda x: x['tokens'], reverse=True)
    stats['largest_files'] = stats['largest_files'][:20]  # Keep top 20
    
    return stats

def print_report(stats, token_limit=200000):
    """Print analysis report."""
    if not stats:
        return
    
    print("\n" + "=" * 80)
    print("ANALYSIS SUMMARY")
    print("=" * 80)
    
    print(f"\nTotal files analyzed: {stats['total_files']:,}")
    print(f"Files skipped: {stats['skipped_files']:,}")
    print(f"Errors encountered: {stats['errors']:,}")
    
    print(f"\nTotal characters: {stats['total_chars']:,}")
    print(f"Estimated tokens: {stats['total_tokens']:,}")
    print(f"Token limit: {token_limit:,}")
    
    percentage = (stats['total_tokens'] / token_limit) * 100
    print(f"\nUsage: {percentage:.1f}% of {token_limit:,} token limit")
    
    if stats['total_tokens'] > token_limit:
        print(f"⚠️  WARNING: Exceeds token limit by {stats['total_tokens'] - token_limit:,} tokens!")
    else:
        print(f"✓ Fits within token limit with {token_limit - stats['total_tokens']:,} tokens to spare")
    
    # File type breakdown
    print("\n" + "-" * 80)
    print("BREAKDOWN BY FILE TYPE")
    print("-" * 80)
    print(f"{'Extension':<12} {'Files':<8} {'Characters':<15} {'Est. Tokens':<15} {'% of Total'}")
    print("-" * 80)
    
    sorted_extensions = sorted(
        stats['by_extension'].items(),
        key=lambda x: x[1]['tokens'],
        reverse=True
    )
    
    for ext, ext_stats in sorted_extensions[:15]:  # Top 15 extensions
        percentage = (ext_stats['tokens'] / stats['total_tokens']) * 100 if stats['total_tokens'] > 0 else 0
        print(f"{ext:<12} {ext_stats['files']:<8} {ext_stats['chars']:<15,} {ext_stats['tokens']:<15,} {percentage:>6.1f}%")
    
    # Largest files
    if stats['largest_files']:
        print("\n" + "-" * 80)
        print("LARGEST FILES BY TOKEN COUNT")
        print("-" * 80)
        print(f"{'File Path':<50} {'Size':<10} {'Est. Tokens':<12} {'% of Total'}")
        print("-" * 80)
        
        for file_info in stats['largest_files'][:10]:  # Top 10 files
            percentage = (file_info['tokens'] / stats['total_tokens']) * 100 if stats['total_tokens'] > 0 else 0
            file_path = file_info['path']
            if len(file_path) > 47:
                file_path = "..." + file_path[-44:]
            print(f"{file_path:<50} {format_size(file_info['size']):<10} {file_info['tokens']:<12,} {percentage:>6.1f}%")

def main():
    parser = argparse.ArgumentParser(
        description='Estimate token count for all files in a directory'
    )
    parser.add_argument(
        'directory',
        help='Directory to analyze'
    )
    parser.add_argument(
        '--limit',
        type=int,
        default=200000,
        help='Token limit to compare against (default: 200000)'
    )
    parser.add_argument(
        '--max-file-size',
        type=int,
        default=10,
        help='Maximum file size in MB to process (default: 10)'
    )
    
    args = parser.parse_args()
    
    # Analyze directory
    stats = analyze_directory(args.directory, args.max_file_size)
    
    # Print report
    if stats:
        print_report(stats, args.limit)

if __name__ == "__main__":
    main()
