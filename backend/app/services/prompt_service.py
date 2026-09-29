from typing import Optional


class PromptGenerationService:
    """Generates production-ready AI video prompts from structured video analysis.

    Accepts the structured analysis output from VideoAnalysisService
    and produces a natural-language prompt suitable for AI video-generation tools.

    The engine does NOT fabricate visual details.
    It only transforms existing analysis data into coherent prose.
    """

    VALID_STYLES = {"cinematic", "realistic", "commercial"}

    def __init__(self):
        pass

    def generate_prompt(
        self,
        analysis: dict,
        style: str = "cinematic",
    ) -> dict:
        """Generate a video prompt from structured analysis.

        Args:
            analysis: Structured video analysis dict containing:
                video_filename, frames_analyzed, analysis (with subjects, actions,
                environment, camera, lighting, visual_style, color_palette, objects),
                frame_observations
            style: One of 'cinematic', 'realistic', 'commercial'.

        Returns:
            Dict with 'prompt' and 'negative_prompt' keys.

        Raises:
            ValueError: If style is invalid.
        """
        if style not in self.VALID_STYLES:
            raise ValueError(
                f"Invalid style. Must be one of: {', '.join(sorted(self.VALID_STYLES))}"
            )

        analysis_data = analysis.get("analysis", {})
        frame_observations = analysis.get("frame_observations", [])

        prompt = self._build_prompt(analysis_data, style, frame_observations)

        return {
            "prompt": prompt,
            "negative_prompt": None,
            "style": style,
        }

    def _build_prompt(
        self, analysis: dict, style: str, frame_observations: list = None
    ) -> str:
        """Build a natural-language prompt from analysis data."""
        if frame_observations is None:
            frame_observations = []

        subjects = analysis.get("subjects", [])
        actions = analysis.get("actions", [])
        environment = analysis.get("environment", "")
        camera = analysis.get("camera", {})
        lighting = analysis.get("lighting", "")
        visual_style = analysis.get("visual_style", "")
        color_palette = analysis.get("color_palette", [])
        objects = analysis.get("objects", [])

        parts = []

        subject_text = self._format_subjects(subjects)
        if subject_text:
            parts.append(subject_text)

        action_text = self._format_actions(actions)
        if action_text:
            parts.append(action_text)

        env_text = self._format_environment(environment, objects)
        if env_text:
            parts.append(env_text)

        camera_text = self._format_camera(camera)
        if camera_text:
            parts.append(camera_text)

        if style == "cinematic" and (camera_text or subject_text or action_text):
            parts.append("cinematic composition")

        light_text = self._format_lighting(lighting, color_palette)
        if light_text:
            parts.append(light_text)

        style_text = self._format_visual_style(visual_style, style)
        if style_text:
            parts.append(style_text)

        temporal_text = self._format_temporal(frame_observations)
        if temporal_text:
            parts.append(temporal_text)

        return self._join_prompt_parts(parts, style)

    def _format_subjects(self, subjects: list) -> str:
        if not subjects:
            return ""
        return f"Subject{'s' if len(subjects) > 1 else ''} {' and '.join(subjects)}"

    def _format_actions(self, actions: list) -> str:
        if not actions:
            return ""
        return f"Actions include {', '.join(actions)}"

    def _format_environment(self, environment: str, objects: list) -> str:
        parts = []
        if environment:
            parts.append(f"set in {environment}")
        if objects:
            parts.append(f"with {' and '.join(objects)}")
        return ", ".join(parts) if parts else ""

    def _format_camera(self, camera: dict) -> str:
        parts = []
        perspective = camera.get("perspective", "")
        shot_type = camera.get("shot_type", "")
        movement = camera.get("movement", "")

        if perspective or shot_type or movement:
            camera_parts = []
            if perspective:
                camera_parts.append(f"{perspective} perspective")
            if shot_type:
                camera_parts.append(f"{shot_type}")
            if movement:
                camera_parts.append(f"with {movement}")
            if camera_parts:
                parts.append("Captured through " + ", ".join(camera_parts))

        return ", ".join(parts) if parts else ""

    def _format_lighting(self, lighting: str, color_palette: list) -> str:
        parts = []
        if lighting:
            parts.append(lighting)
        if color_palette:
            parts.append(f"with a color palette of {', '.join(color_palette)}")
        return ", ".join(parts) if parts else ""

    def _format_visual_style(self, visual_style: str, style: str) -> str:
        if not visual_style:
            return f"{style} presentation"
        return visual_style

    def _format_temporal(self, frame_observations: list) -> str:
        if len(frame_observations) <= 1:
            return ""
        return f"Temporal progression across {len(frame_observations)} frames"

    def _join_prompt_parts(self, parts: list, style: str) -> str:
        filtered = [p.strip() for p in parts if p.strip()]

        if not filtered:
            return self._default_prompt(style)

        prompt = filtered[0]
        for part in filtered[1:]:
            if part.startswith("Subject"):
                prompt += f", {part.lower()}"
            elif part.startswith("Actions"):
                prompt += f". {part}"
            elif part.startswith("Set"):
                prompt += f", {part}"
            elif part.startswith("Captured"):
                prompt += f". {part}"
            elif part.startswith("Temporal"):
                prompt += f". {part}"
            elif part == "cinematic composition":
                prompt += f" with {part}"
            else:
                prompt += f", {part}"

        if not prompt.endswith("."):
            prompt += "."

        prompt = prompt[0].upper() + prompt[1:]

        return prompt

    def _default_prompt(self, style: str) -> str:
        if style == "cinematic":
            return "A cinematic scene awaiting detailed visual content."
        elif style == "realistic":
            return "A realistic scene awaiting detailed visual content."
        elif style == "commercial":
            return "A polished commercial scene awaiting detailed visual content."
        return "A scene awaiting detailed visual content."
