"""Quality-Guided Prompt Improvement service (Day 22).

A deterministic improvement layer on top of the Day 21 Prompt Quality
Analyzer. The flow is:

    existing prompt -> PromptQualityService -> missing/weak dimensions
                    -> deterministic guidance -> improved prompt

This is NOT an LLM feature. No external AI/API/model is called; there
are no network, filesystem, or database operations.

No-fabrication rule (critical):

The service NEVER invents video facts (no people, locations, objects,
actions, colors, camera moves, lighting, or audio that were not already
present in the source prompt). It only appends neutral, bracketed
improvement instructions such as:

    [Specify lighting characteristics if known]

These placeholders are instructions for the user, NOT claims about the
video. The original prompt is always preserved byte-for-byte at the
start of the improved prompt.

Determinism:

Same input prompt -> identical output. No timestamps, randomness,
locale, or environment dependence.
"""

from app.services.prompt_quality_service import (
    DIMENSIONS,
    WEAK_SCORE,
)

IMPROVEMENT_HEADER = "Enhancement Guidance:"

GUIDANCE = {
    "subject": (
        "[Clarify the main subject and relevant visual characteristics "
        "if known]"
    ),
    "action": "[Clarify the subject's action or movement if known]",
    "environment": "[Specify the environment or setting if known]",
    "camera": (
        "[Specify shot type, perspective, framing, or camera movement "
        "if known]"
    ),
    "lighting": "[Specify lighting characteristics if known]",
    "visual_style": (
        "[Specify the visual style or rendering characteristics if known]"
    ),
    "color": "[Specify dominant colors or color treatment if known]",
    "composition": (
        "[Specify framing, subject placement, depth, or composition "
        "if known]"
    ),
    "audio": (
        "[Specify dialogue, ambience, music, or sound effects if known]"
    ),
}


class PromptImprovementService:
    """Deterministic quality-guided prompt improvement (Day 22)."""

    def __init__(self, quality_service):
        self.quality_service = quality_service

    def improve_prompt(self, prompt) -> dict:
        """Improve one prompt's coverage without fabricating facts.

        Raises:
            ValueError: When the prompt is not a string or is empty/
            whitespace-only.
        """
        if not isinstance(prompt, str):
            raise ValueError("prompt must be a string.")
        if not prompt.strip():
            raise ValueError("prompt must not be empty.")

        quality_before = self.quality_service.analyze_prompt(prompt)["quality"]

        improvements = []
        guided_dimensions = []
        for dim in DIMENSIONS:
            entry = quality_before["dimensions"][dim]
            if not entry["present"]:
                reason = "missing"
            elif entry["score"] == WEAK_SCORE:
                reason = "weak"
            else:
                continue
            improvements.append({
                "dimension": dim,
                "reason": reason,
                "guidance": GUIDANCE[dim],
            })
            guided_dimensions.append(dim)

        if improvements:
            improved_prompt = (
                f"{prompt}\n\n{IMPROVEMENT_HEADER}\n"
                + "\n".join(item["guidance"] for item in improvements)
            )
        else:
            improved_prompt = prompt

        quality_after = self.quality_service.analyze_prompt(
            improved_prompt
        )["quality"]

        return {
            "source_prompt": prompt,
            "improved_prompt": improved_prompt,
            "quality_before": quality_before,
            "quality_after": quality_after,
            "improvement_applied": bool(improvements),
            "improvements": improvements,
            "preserved_information": improved_prompt.startswith(prompt),
            "guidance_added": bool(guided_dimensions),
            "guided_dimensions": guided_dimensions,
        }
