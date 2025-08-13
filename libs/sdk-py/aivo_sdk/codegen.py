"""
AIVO Python SDK - Code Generation Script
S1-15 Contract & SDK Integration

Generates Python client code from OpenAPI specifications.
"""

import subprocess
import sys
import os
from pathlib import Path


def run_command(cmd: str, cwd: str = None) -> None:
    """Run a shell command and check for errors"""
    print(f"Running: {cmd}")
    result = subprocess.run(cmd, shell=True, cwd=cwd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"Error running command: {cmd}")
        print(f"stdout: {result.stdout}")
        print(f"stderr: {result.stderr}")
        sys.exit(1)
    print(f"Success: {result.stdout}")


def main():
    """Main code generation function"""
    project_root = Path(__file__).parent.parent.parent
    api_specs_dir = project_root / "docs" / "api" / "rest"
    output_dir = Path(__file__).parent / "clients"
    
    # Ensure output directory exists
    output_dir.mkdir(exist_ok=True)
    
    # List of services to generate clients for
    services = [
        "auth",
        "user", 
        "assessment",
        "learner",
        "notification",
        "search",
        "orchestrator"
    ]
    
    for service in services:
        spec_file = api_specs_dir / f"{service}.yaml"
        if not spec_file.exists():
            print(f"Warning: Spec file not found: {spec_file}")
            continue
            
        print(f"Generating client for {service} service...")
        
        # Generate client using openapi-generator
        cmd = (
            f"openapi-generator generate "
            f"-i {spec_file} "
            f"-g python "
            f"-o {output_dir / service} "
            f"--package-name aivo_sdk.clients.{service} "
            f"--additional-properties=packageVersion=1.0.0"
        )
        
        try:
            run_command(cmd)
            print(f"Generated {service} client successfully")
        except Exception as e:
            print(f"Failed to generate {service} client: {e}")
            continue
    
    print("Code generation completed!")


if __name__ == "__main__":
    main()
