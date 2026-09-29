#!/usr/bin/env python
"""Manual test script for the Vision AI service.

This script finds an existing extracted frame and sends it for analysis.
Requires a configured vision provider (not the mock).

Usage:
    cd backend
    python -m scripts.test_vision
"""
import os
import sys
import glob

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.ai.providers import get_vision_provider
from app.services.vision_service import VisionService


def main():
    # Find an existing frame
    frame_files = glob.glob("storage/frames/*/frame_*.jpg")
    if not frame_files:
        print("No extracted frames found. Run frame extraction first.")
        print("Example: POST /api/videos/{stored_filename}/frames/extract")
        return

    frame_path = frame_files[0]
    print(f"Found frame: {frame_path}")

    # Get the configured provider
    from app.core.config import settings
    print(f"Configured provider: {settings.vision_provider}")

    if settings.vision_provider == "mock":
        print("WARNING: Mock provider is configured.")
        print("To use a real model, set VISION_PROVIDER=qwen2vl in .env")
        print("and install the required dependencies.")

    provider = get_vision_provider(settings.vision_provider)
    service = VisionService(provider)

    print(f"Model: {provider.model_name}")
    print("\nRunning analysis...")

    try:
        result = service.analyze_frame(frame_path)
        print("\nVISION MODEL RESULT:")
        print("-" * 40)
        print(result["description"])
        print("-" * 40)
        print(f"Model: {result['model']}")
    except FileNotFoundError:
        print("Error: Frame image not found.")
    except RuntimeError as e:
        print(f"Error: {e}")
    except Exception as e:
        print(f"Unexpected error: {e}")


if __name__ == "__main__":
    main()
