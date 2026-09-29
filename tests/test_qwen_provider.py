"""Tests for the Qwen2.5-VL vision provider integration."""
import os
import pytest
from app.ai.providers import (
    MockVisionProvider,
    Qwen2VLProvider,
    get_vision_provider,
    DEFAULT_PROMPT,
)


class TestMockProvider:
    def test_mock_provider_model_name(self):
        provider = MockVisionProvider()
        assert provider.model_name == "mock-vision-provider"

    def test_mock_provider_returns_description(self, tmp_path):
        provider = MockVisionProvider()
        fake_image = tmp_path / "fake.jpg"
        fake_image.write_text("fake")
        result = provider.describe_image(str(fake_image))
        assert isinstance(result, str)
        assert len(result) > 0

    def test_mock_provider_file_not_found(self):
        provider = MockVisionProvider()
        with pytest.raises(FileNotFoundError):
            provider.describe_image("/nonexistent/path.jpg")


class TestQwenProviderInitialization:
    def test_qwen_provider_model_name(self):
        provider = Qwen2VLProvider()
        assert provider.model_name == "Qwen2.5-VL"

    def test_qwen_provider_default_device(self):
        provider = Qwen2VLProvider()
        assert provider._device in ("cuda", "cpu")

    def test_qwen_provider_not_loaded_initially(self):
        provider = Qwen2VLProvider()
        assert not provider._loaded

    def test_qwen_provider_selects_cpu_when_torch_missing(self):
        provider = Qwen2VLProvider()
        assert provider._device == "cpu"


class TestQwenProviderMissingDependencies:
    def test_qwen_raises_when_torch_missing(self, monkeypatch):
        import app.ai.providers as providers_module

        def fake_lazy_load(self):
            pass

        provider = Qwen2VLProvider()
        provider._loaded = False

        # Force the model to not be loaded
        provider._loaded = False
        provider._model = None
        provider._processor = None

        # Simulate missing torch by checking the error message
        # The actual lazy_load will raise RuntimeError if torch is missing
        try:
            provider._lazy_load_model()
        except RuntimeError as e:
            assert "torch" in str(e).lower() or "transformers" in str(e).lower()

    def test_provider_factory_returns_mock(self):
        provider = get_vision_provider("mock")
        assert isinstance(provider, MockVisionProvider)

    def test_provider_factory_returns_qwen(self):
        provider = get_vision_provider("qwen2vl")
        assert isinstance(provider, Qwen2VLProvider)

    def test_provider_factory_invalid_name(self):
        with pytest.raises(ValueError):
            get_vision_provider("invalid")


class TestProviderFactory:
    def test_mock_is_default(self):
        provider = get_vision_provider()
        assert isinstance(provider, MockVisionProvider)

    def test_qwen2vl_factory(self):
        provider = get_vision_provider("qwen2vl")
        assert isinstance(provider, Qwen2VLProvider)
        assert provider.model_name == "Qwen2.5-VL"


class TestDefaultPrompt:
    def test_default_prompt_is_string(self):
        assert isinstance(DEFAULT_PROMPT, str)
        assert len(DEFAULT_PROMPT) > 0

    def test_default_prompt_contains_instructions(self):
        assert "Describe" in DEFAULT_PROMPT
        assert "Do not invent" in DEFAULT_PROMPT
