from abc import ABC, abstractmethod
from typing import Optional


class VisionProvider(ABC):
    """Abstract base class for vision-language model providers.

    Subclasses implement describe_image() to send an image to a
    vision model and return a textual description.

    This abstraction allows switching between providers:
    * MockVisionProvider        — for development/testing
    * Qwen2VLProvider           — for local Qwen2.5-VL inference
    * ExternalAPIVisionProvider — for cloud-based vision APIs
    """

    @property
    @abstractmethod
    def model_name(self) -> str:
        """Return the model identifier."""
        ...

    @abstractmethod
    def describe_image(self, image_path: str, prompt: Optional[str] = None) -> str:
        """Analyze an image and return a text description.

        Args:
            image_path: Path to the image file.
            prompt: Optional custom prompt. Uses default if None.

        Returns:
            A textual description of the image contents.

        Raises:
            FileNotFoundError: If the image does not exist.
            RuntimeError: If the provider fails to analyze the image.
        """
        ...
