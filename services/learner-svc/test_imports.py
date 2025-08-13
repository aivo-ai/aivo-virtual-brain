#!/usr/bin/env python3
"""
Test script to verify that all imports work correctly
"""
import sys
print(f"Python executable: {sys.executable}")

try:
    from fastapi import APIRouter
    print("✅ FastAPI APIRouter imported successfully")
except ImportError as e:
    print(f"❌ FastAPI import failed: {e}")

try:
    from datetime import datetime
    print("✅ datetime imported successfully")
except ImportError as e:
    print(f"❌ datetime import failed: {e}")

try:
    from app.routers.health import router
    print("✅ Health router imported successfully")
except ImportError as e:
    print(f"❌ Health router import failed: {e}")

print("All import tests completed!")
