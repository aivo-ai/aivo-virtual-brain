#!/usr/bin/env python3
"""
YAML Validator Script
Validates YAML files and reports syntax errors
"""

import yaml
import sys
import os
from pathlib import Path

def validate_yaml_file(filepath):
    """Validate a single YAML file"""
    try:
        with open(filepath, 'r', encoding='utf-8') as file:
            content = file.read()
            # Handle multi-document YAML files
            documents = yaml.safe_load_all(content)
            # Force evaluation of all documents
            list(documents)
        return True, None
    except yaml.YAMLError as e:
        return False, str(e)
    except Exception as e:
        return False, f"Error reading file: {e}"

def find_yaml_files(directory):
    """Find all YAML files in directory, excluding Helm templates"""
    yaml_files = []
    for ext in ['*.yaml', '*.yml']:
        yaml_files.extend(Path(directory).rglob(ext))
    
    # Filter out Helm templates which contain Go template syntax
    filtered_files = []
    for yaml_file in yaml_files:
        file_str = str(yaml_file)
        # Skip Helm template files
        if '/templates/' in file_str or '\\templates\\' in file_str:
            if '/charts/' in file_str or '\\charts\\' in file_str:
                continue
            # Also skip infra/helm templates
            if '/helm/' in file_str or '\\helm\\' in file_str:
                continue
        filtered_files.append(yaml_file)
    
    return filtered_files

def main():
    if len(sys.argv) > 1:
        target = sys.argv[1]
    else:
        target = '.'
    
    errors_found = 0
    files_checked = 0
    
    if os.path.isfile(target):
        # Single file
        yaml_files = [Path(target)]
    else:
        # Directory
        yaml_files = find_yaml_files(target)
    
    for yaml_file in sorted(yaml_files):
        files_checked += 1
        is_valid, error = validate_yaml_file(yaml_file)
        
        if not is_valid:
            errors_found += 1
            print(f"ERROR {yaml_file}: {error}")
        else:
            print(f"OK {yaml_file}")
    
    print(f"\nSummary: {files_checked} files checked, {errors_found} errors found")
    
    if errors_found > 0:
        sys.exit(1)

if __name__ == "__main__":
    main()
