"""Advanced Production Prompt Generation service (Day 13).

Converts the unified Video Intelligence from Day 12 into a detailed,
production-ready AI video-generation prompt with scene awareness.

Reuses Day 12 intelligence data and existing PromptGenerationService.
Never fabricates information not present in the intelligence data.
"""

from typing import Optional

from app.services.prompt_service import PromptGenerationService

VALID_STYLES = {"cinematic", "realistic", "commercial"}

DEFAULT_NEGATIVE_PROMPT = (
    "blurry, low quality, distorted anatomy, unwanted text, watermark"
)


class AdvancedPromptService:
    """Generates production-ready AI video prompts from unified intelligence data.

    Consumes the unified Video Intelligence object from Day 12 and produces
    a structured prompt with sections for subject, action, environment, camera,
    lighting, visual style, color, audio, and composition.

    The engine does NOT fabricate visual details.
    It only transforms existing intelligence data into coherent prose.
    """

    def __init__(self):
        self.prompt_service = PromptGenerationService()

    def generate_prompt(
        self,
        intelligence: dict,
        style: str = "cinematic",
    ) -> dict:
        """Generate a production-ready prompt from unified intelligence.

        Args:
            intelligence: Unified Video Intelligence dict from Day 12.
                Contains: video_filename, duration_seconds, visual, scenes,
                subjects, audio.
            style: One of 'cinematic', 'realistic', 'commercial'.

        Returns:
            Dict with 'video_filename', 'style', 'prompt', 'negative_prompt',
            and 'sections' keys.

        Raises:
            ValueError: If style is invalid.
        """
        if style not in VALID_STYLES:
            raise ValueError(
                f"Invalid style. Must be one of: {', '.join(sorted(VALID_STYLES))}"
            )

        visual = intelligence.get("visual", {})
        scenes = intelligence.get("scenes", {})
        subjects_data = intelligence.get("subjects", {})
        audio = intelligence.get("audio", {})

        sections = self._build_sections(visual, scenes, subjects_data, audio, style)

        prompt = self._build_prompt(sections, style)

        negative_prompt = self._build_negative_prompt(visual, sections)

        return {
            "video_filename": intelligence.get("video_filename", ""),
            "style": style,
            "prompt": prompt,
            "negative_prompt": negative_prompt,
            "sections": sections,
        }

    def _build_sections(
        self, visual, scenes, subjects_data, audio, style
    ) -> dict:
        """Build the sections dict from intelligence data."""
        subjects = visual.get("subjects", [])
        actions = visual.get("actions", [])
        environment = visual.get("environment", "")
        camera = visual.get("camera", {})
        lighting = visual.get("lighting", "")
        visual_style = visual.get("visual_style", "")
        color_palette = visual.get("color_palette", [])
        objects = visual.get("objects", [])
        profiles = subjects_data.get("profiles", [])
        timeline = scenes.get("timeline", [])

        subject_text = self._format_subjects(subjects, profiles)
        action_text = self._format_actions(actions)
        environment_text = self._format_environment(environment, objects)
        camera_text = self._format_camera(camera)
        lighting_text = self._format_lighting(lighting, color_palette)
        visual_style_text = self._format_visual_style(visual_style, style)
        color_text = self._format_color(color_palette)
        audio_text = self._format_audio(audio)
        composition_text = self._format_composition(
            camera, timeline, style, subjects, visual_style
        )

        return {
            "subject": subject_text,
            "action": action_text,
            "environment": environment_text,
            "camera": camera_text,
            "lighting": lighting_text,
            "visual_style": visual_style_text,
            "color": color_text,
            "audio": audio_text,
            "composition": composition_text,
        }

    def _format_subjects(self, subjects: list, profiles: list) -> str:
        parts = []
        if subjects:
            parts.append(f"Subject{'s' if len(subjects) > 1 else ''}: {', '.join(subjects)}")
        for profile in profiles:
            desc = profile.get("description", "")
            if desc and desc not in subjects:
                parts.append(f"Profile: {desc}")
        return " ".join(parts) if parts else ""

    def _format_actions(self, actions: list) -> str:
        if not actions:
            return ""
        return f"Action: {', '.join(actions)}"

    def _format_environment(self, environment: str, objects: list) -> str:
        parts = []
        if environment:
            parts.append(f"Environment: {environment}")
        if objects:
            parts.append(f"Objects: {', '.join(objects)}")
        return " ".join(parts) if parts else ""

    def _format_camera(self, camera: dict) -> str:
        parts = []
        perspective = camera.get("perspective", "")
        shot_type = camera.get("shot_type", "")
        movement = camera.get("movement", "")
        if perspective:
            parts.append(f"Camera perspective: {perspective}")
        if shot_type:
            parts.append(f"Shot type: {shot_type}")
        if movement:
            parts.append(f"Camera movement: {movement}")
        return " ".join(parts) if parts else ""

    def _format_lighting(self, lighting: str, color_palette: list) -> str:
        parts = []
        if lighting:
            parts.append(f"Lighting: {lighting}")
        if color_palette:
            parts.append(f"Color palette: {', '.join(color_palette)}")
        return " ".join(parts) if parts else ""

    def _format_visual_style(self, visual_style: str, style: str) -> str:
        if not visual_style:
            return f"Visual style: {style}"
        return f"Visual style: {visual_style}"

    def _format_color(self, color_palette: list) -> str:
        if not color_palette:
            return ""
        return f"Color: {', '.join(color_palette)}"

    def _format_audio(self, audio: dict) -> str:
        if not audio.get("has_audio"):
            return ""
        parts = []
        transcription = audio.get("transcription", {})
        language = transcription.get("language")
        text = transcription.get("text", "")
        if language:
            parts.append(f"Audio language: {language}")
        if text:
            parts.append(f"Audio text: {text[:200]}")
        return " ".join(parts) if parts else ""

    def _format_composition(
        self, camera: dict, timeline: list, style: str, subjects: list, visual_style: str
    ) -> str:
        parts = []
        if camera.get("shot_type") or camera.get("perspective"):
            parts.append(f"Composition: {camera.get('shot_type', camera.get('perspective', ''))} shot")
        if timeline:
            parts.append(f"Scene progression across {len(timeline)} scenes")
        if style == "cinematic" and (camera.get("shot_type") or camera.get("perspective") or subjects):
            parts.append("cinematic composition")
        return " ".join(parts) if parts else ""

    def _build_prompt(self, sections: dict, style: str) -> str:
        """Build the natural-language prompt from sections."""
        parts = []
        for key in ["subject", "action", "environment", "camera", "lighting", "visual_style", "color", "audio", "composition"]:
            val = sections.get(key, "")
            if val:
                parts.append(val)

        if not parts:
            return self._default_prompt(style)

        prompt = "; ".join(parts)
        prompt = self._append_style_wording(prompt, style)
        if not prompt.endswith("."):
            prompt += "."
        return prompt

    def _append_style_wording(self, prompt: str, style: str) -> str:
        """Ensure the selected style influences the prompt wording."""
        style_terms = {
            "cinematic": "cinematic composition",
            "realistic": "realistic presentation",
            "commercial": "commercial presentation",
        }
        term = style_terms[style]
        if term not in prompt.lower():
            prompt = f"{prompt}, {term}"
        return prompt

    def _build_negative_prompt(self, visual: dict, sections: dict) -> str:
        """Generate a conservative generic negative prompt."""
        negatives = []
        if visual.get("subjects") or visual.get("objects"):
            negatives.append("distorted anatomy")
        negatives.extend(["blurry", "low quality", "unwanted text", "watermark"])
        return ", ".join(negatives)

    def _default_prompt(self, style: str) -> str:
        if style == "cinematic":
            return "A cinematic scene awaiting detailed visual content."
        elif style == "realistic":
            return "A realistic scene awaiting detailed visual content."
        elif style == "commercial":
            return "A polished commercial scene awaiting detailed visual content."
        return "A scene awaiting detailed visual content."
