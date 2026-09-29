import os
from typing import Optional

from app.ai.vision_provider import VisionProvider
from app.core.config import settings


DEFAULT_PROMPT = (
    "Describe this image in detail for an AI video reconstruction system. "
    "Identify the main subjects, their appearance, actions, environment, objects, "
    "composition, camera perspective, lighting, colors, visual style, and any "
    "clearly visible text. Do not invent details that are not visible."
)


class MockVisionProvider(VisionProvider):
    """Mock vision provider for development and testing.

    Returns a fixed description regardless of the input image.
    Replace with a real provider (e.g., Qwen2VLProvider) for production inference.
    """

    @property
    def model_name(self) -> str:
        return "mock-vision-provider"

    def describe_image(self, image_path: str, prompt: Optional[str] = None) -> str:
        if not os.path.isfile(image_path):
            raise FileNotFoundError(f"Image not found: {image_path}")

        return (
            "A mock vision description for development purposes. "
            "The configured model is not yet active. "
            "To enable real inference, configure a Qwen2.5-VL provider "
            "or another VisionProvider subclass."
        )


class Qwen2VLProvider(VisionProvider):
    """Real vision provider using the Qwen2.5-VL model.

    Requires:
    * torch
    * transformers
    * accelerate (recommended)
    * The Qwen2.5-VL model weights downloaded locally.

    The model is loaded lazily on the first call to describe_image().
    This avoids allocating large amounts of memory during application startup.
    """

    _instance: Optional["Qwen2VLProvider"] = None
    _processor = None
    _model = None

    def __init__(self):
        super().__init__()
        self._model_name = getattr(settings, "vision_model_name", "Qwen2.5-VL")
        self._device = self._select_device()
        self._loaded = False

    @staticmethod
    def _select_device() -> str:
        """Select the best available device for inference.

        Prefers CUDA GPU if available, falls back to CPU.
        """
        try:
            import torch
            if torch.cuda.is_available():
                return "cuda"
        except ImportError:
            pass
        return "cpu"

    def _lazy_load_model(self):
        """Load the Qwen2.5-VL model and processor lazily.

        This method is called on the first describe_image() call.
        Raises clear RuntimeError if dependencies are missing.
        """
        if self._loaded:
            return

        try:
            import torch
        except ImportError:
            raise RuntimeError(
                "Qwen2VLProvider requires torch but it is not installed. "
                "Install torch to enable real Qwen2.5-VL inference."
            )

        try:
            from transformers import AutoProcessor, AutoModelForVision2Seq
        except ImportError:
            raise RuntimeError(
                "Qwen2VLProvider requires transformers but it is not installed. "
                "Install transformers to enable real Qwen2.5-VL inference."
            )

        try:
            model_id = self._model_name
            self._processor = AutoProcessor.from_pretrained(model_id)
            self._model = AutoModelForVision2Seq.from_pretrained(
                model_id, device_map=self._device
            )
            self._loaded = True
        except Exception as e:
            raise RuntimeError(
                f"Failed to load Qwen2.5-VL model '{model_id}': {str(e)}. "
                "Ensure the model identifier is correct and the model weights "
                "are accessible."
            )

    @property
    def model_name(self) -> str:
        return self._model_name

    def describe_image(self, image_path: str, prompt: Optional[str] = None) -> str:
        """Analyze an image and return a natural-language description.

        Args:
            image_path: Path to the JPEG frame file.
            prompt: Optional custom analysis prompt. Uses default if None.

        Returns:
            A textual description of the image contents.

        Raises:
            FileNotFoundError: If the image does not exist.
            ValueError: If the image path is invalid or outside frame storage.
            RuntimeError: If the model fails to analyze the image.
        """
        if not os.path.isfile(image_path):
            raise FileNotFoundError(f"Image not found: {image_path}")

        self._lazy_load_model()

        use_prompt = prompt or DEFAULT_PROMPT

        try:
            from PIL import Image
            image = Image.open(image_path).convert("RGB")
        except Exception as e:
            raise ValueError(f"Invalid image file '{image_path}': {str(e)}")

        try:
            inputs = self._processor(images=image, text=use_prompt, return_tensors="pt")
            if self._device == "cuda":
                inputs = {k: v.to("cuda") for k, v in inputs.items()}

            generated_ids = self._model.generate(**inputs, max_new_tokens=512)
            generated_text = self._processor.batch_decode(
                generated_ids, skip_special_tokens=True
            )[0]
        except Exception as e:
            raise RuntimeError(
                f"Qwen2.5-VL inference failed for image '{image_path}': {str(e)}"
            )

        return generated_text.strip()


def get_vision_provider(provider_name: str = "mock") -> VisionProvider:
    """Create a vision provider by name.

    Args:
        provider_name: 'mock', 'qwen2vl', or a custom provider class name.

    Returns:
        An instance of the requested VisionProvider.
    """
    if provider_name == "mock":
        return MockVisionProvider()
    if provider_name == "qwen2vl":
        return Qwen2VLProvider()
    raise ValueError(f"Unknown vision provider: {provider_name}")
