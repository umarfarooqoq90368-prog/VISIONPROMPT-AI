from typing import Optional

from app.ai.providers import (
    DEFAULT_PROMPT,
    get_vision_provider,
    MockVisionProvider,
    Qwen2VLProvider,
    VisionProvider,
)
from app.core.config import settings


class VisionService:
    """Service layer for AI vision analysis.

    Depends on a VisionProvider abstraction, allowing switching between
    mock providers for development and real models for production.
    """

    def __init__(self, provider: Optional[VisionProvider] = None):
        self.provider = provider or get_vision_provider(settings.vision_provider)

    def analyze_frame(self, frame_path: str, prompt: Optional[str] = None) -> dict:
        """Analyze a frame image and return a description.

        Args:
            frame_path: Path to the JPEG frame file.
            prompt: Optional custom analysis prompt.

        Returns:
            Dict with 'description', 'model', and 'success' keys.

        Raises:
            FileNotFoundError: If the frame does not exist.
            RuntimeError: If the provider fails to analyze the image.
        """
        if not self._is_valid_image_path(frame_path):
            raise ValueError("Invalid frame path.")

        if not self._is_in_frame_storage(frame_path):
            raise ValueError("Frame is outside the allowed frame storage.")

        description = self.provider.describe_image(frame_path, prompt or DEFAULT_PROMPT)

        return {
            "description": description,
            "model": self.provider.model_name,
            "success": True,
        }

    def _is_valid_image_path(self, frame_path: str) -> bool:
        """Check if the frame path has a valid image extension."""
        valid_extensions = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}
        return any(frame_path.lower().endswith(ext) for ext in valid_extensions)

    def _is_in_frame_storage(self, frame_path: str) -> bool:
        """Verify the frame is inside the frame storage directory."""
        from pathlib import Path

        frame_path = Path(frame_path).resolve()
        storage_root = Path("storage/frames").resolve()
        try:
            frame_path.relative_to(storage_root)
            return True
        except ValueError:
            return False
