"""Prompt Template & Custom Instruction service (Day 15).

Applies predefined production templates and user-provided custom instructions
to an existing Day 13/Day 14 generated prompt.

Templates only reorganize or rephrase information already present in the
source prompt. Custom instructions are pattern-matched into safe structural
changes (ordering, compaction) and are never copied into the prompt text,
so they cannot introduce unsupported factual information.
"""

import re
from collections import Counter
from typing import Optional

from app.services import prompt_refinement_service as prs
from app.services.advanced_prompt_service import (
    AdvancedPromptService,
    DEFAULT_NEGATIVE_PROMPT,
)

VALID_TEMPLATES = {
    "cinematic_story",
    "ai_video",
    "commercial_ad",
    "social_media",
    "documentary",
}

TEMPLATE_PREFIX = {
    "cinematic_story": "Cinematic story: ",
    "ai_video": "AI video prompt: ",
    "commercial_ad": "Commercial presentation: ",
    "social_media": "Social media video: ",
    "documentary": "Documentary: ",
}

TEMPLATE_JOIN = {
    "cinematic_story": ". ",
    "commercial_ad": ", ",
    "social_media": ", ",
    "documentary": ". ",
}

TEMPLATE_ORDER = {
    "cinematic_story": [
        "Subject", "Profile", "Action", "Environment", "Objects",
        "Camera perspective", "Shot type", "Camera movement",
        "Lighting", "Color palette", "Color", "Visual style",
        "Audio language", "Audio text", "Composition",
    ],
    "ai_video": [
        "Subject", "Profile", "Action", "Environment", "Objects",
        "Camera perspective", "Shot type", "Camera movement",
        "Lighting", "Color palette", "Color", "Visual style",
        "Composition", "Audio language", "Audio text",
    ],
    "commercial_ad": [
        "Visual style", "Composition",
        "Subject", "Profile", "Action", "Environment", "Objects",
        "Camera perspective", "Shot type", "Camera movement",
        "Lighting", "Color palette", "Color",
        "Audio language", "Audio text",
    ],
    "social_media": [
        "Subject", "Profile", "Action", "Composition", "Visual style",
        "Environment", "Objects",
        "Camera perspective", "Shot type", "Camera movement",
        "Lighting", "Color palette", "Color",
        "Audio language", "Audio text",
    ],
    "documentary": [
        "Environment", "Objects", "Subject", "Profile", "Action",
        "Camera perspective", "Shot type", "Camera movement",
        "Lighting", "Audio language", "Audio text",
        "Color palette", "Color", "Visual style", "Composition",
    ],
}

CINEMATIC_WRAPPERS = {
    "subject": "Featuring {v}",
    "profile": "Featuring {v}",
    "action": "{v}",
    "environment": "Set in {v}",
}

_COMPACT_WORDS = ("concise", "shorten", "shorter", "brief", "compact", "succinct")

_AI_VIDEO_WORDS = ("ai video", "video generator", "ai-generated", "ai generated")

_FRONT_KEYWORDS = [
    (("camera movement", "camera perspective", "camera angle", "camera", "shot"),
     ["Camera perspective", "Shot type", "Camera movement"]),
    (("lighting", "light"), ["Lighting"]),
    (("color palette", "color", "colour", "palette"),
     ["Color palette", "Color"]),
    (("subject", "character"), ["Subject", "Profile"]),
    (("action",), ["Action"]),
    (("environment", "setting", "location", "background"),
     ["Environment", "Objects"]),
    (("audio", "sound", "speech", "transcription", "dialogue"),
     ["Audio language", "Audio text"]),
    (("composition", "framing"), ["Composition"]),
    (("visual style", "style"), ["Visual style"]),
]

_CANONICAL = {name.lower(): name for name in prs._LABEL_NAMES}

_LABEL_CLAUSE_RE = re.compile(
    r"^("
    + "|".join(
        re.escape(n) for n in sorted(prs._LABEL_NAMES, key=len, reverse=True)
    )
    + r")\s*:\s*(.+)$",
    re.IGNORECASE,
)

_FRONT_RE = re.compile(
    r"(?:focus on|emphasize|highlight|prioritize)\s+(?:the\s+)?([a-z ]+)"
)


class PromptTemplateService:
    """Applies production templates and custom instructions to a prompt.

    All transformations preserve the factual content of the source prompt.
    No video information is ever fabricated.
    """

    def __init__(self):
        self.advanced_service = AdvancedPromptService()

    def apply_template(
        self,
        source_prompt: str = "",
        template: str = "cinematic_story",
        intelligence: Optional[dict] = None,
        custom_instruction: str = "",
        negative_prompt: Optional[str] = None,
    ) -> dict:
        """Apply a production template and optional custom instruction.

        Args:
            source_prompt: Existing generated/refined prompt.
            template: One of the five supported template names.
            intelligence: Optional Day 12 intelligence dict; used to
                generate a source prompt when source_prompt is empty.
            custom_instruction: Optional user instruction (pattern-matched
                into safe structural changes only).
            negative_prompt: Optional negative prompt to carry through.

        Returns:
            Dict with 'template', 'source_prompt', 'custom_instruction',
            'prompt', 'negative_prompt', and 'preserved_information' keys.

        Raises:
            ValueError: On invalid template or malformed input.
        """
        if not isinstance(template, str) or template not in VALID_TEMPLATES:
            raise ValueError(
                "Invalid template. Must be one of: "
                + ", ".join(sorted(VALID_TEMPLATES))
            )
        if custom_instruction is None:
            custom_instruction = ""
        if not isinstance(custom_instruction, str):
            raise ValueError("custom_instruction must be a string.")
        if not isinstance(source_prompt, str):
            raise ValueError("source_prompt must be a string.")
        if intelligence is not None and not isinstance(intelligence, dict):
            raise ValueError("intelligence must be a dict.")

        source = source_prompt
        if not source.strip() and isinstance(intelligence, dict):
            generated = self.advanced_service.generate_prompt(
                intelligence=intelligence, style="cinematic"
            )
            source = generated["prompt"]

        if not source.strip():
            prompt = source
            preserved = True
        else:
            clauses = self._parse(source)
            if not clauses:
                prompt = source
                preserved = True
            else:
                compact, front_labels = self._instruction_flags(custom_instruction)
                ordered = self._order(clauses, template, front_labels)
                prompt = self._render(template, ordered, compact)
                preserved = self._is_preserved(source, prompt)
                if not preserved:
                    prompt = source
                    preserved = True

        if isinstance(negative_prompt, str) and negative_prompt.strip():
            negative = negative_prompt
        else:
            negative = DEFAULT_NEGATIVE_PROMPT

        return {
            "template": template,
            "source_prompt": source,
            "custom_instruction": custom_instruction,
            "prompt": prompt,
            "negative_prompt": negative,
            "preserved_information": preserved,
        }

    def _parse(self, source: str) -> list:
        """Parse the source prompt into ordered (label, value) clauses."""
        clauses = []
        for segment in source.split(";"):
            segment = segment.strip()
            if not segment:
                continue
            for clause in prs.CLAUSE_BOUNDARY.split(segment):
                clause = clause.strip().rstrip(".").strip()
                if not clause:
                    continue
                match = _LABEL_CLAUSE_RE.match(clause)
                if match:
                    canonical = _CANONICAL.get(
                        match.group(1).strip().lower(), match.group(1).strip()
                    )
                    clauses.append((canonical, match.group(2).strip().rstrip(".").strip()))
                else:
                    clauses.append((None, clause))
        return clauses

    def _instruction_flags(self, instruction: str):
        """Map a custom instruction to safe structural changes."""
        text = instruction.lower()
        compact = any(word in text for word in _COMPACT_WORDS)
        if any(word in text for word in _AI_VIDEO_WORDS):
            compact = True

        front_labels = None
        match = _FRONT_RE.search(text)
        if match:
            key = match.group(1).strip()
            for keywords, labels in _FRONT_KEYWORDS:
                if any(key == k or key.startswith(k) or k in key for k in keywords):
                    front_labels = labels
                    break
        return compact, front_labels

    def _order(self, clauses: list, template: str, front_labels) -> list:
        order = TEMPLATE_ORDER[template]

        def sort_key(item):
            label = item[0]
            if label is None:
                return (2, 0)
            try:
                return (0, order.index(label))
            except ValueError:
                return (1, 0)

        ordered = sorted(clauses, key=sort_key)
        if front_labels:
            front = [c for c in ordered if c[0] in front_labels]
            rest = [c for c in ordered if c[0] not in front_labels]
            ordered = front + rest
        return ordered

    def _render(self, template: str, ordered: list, compact: bool) -> str:
        prefix = TEMPLATE_PREFIX[template]

        if compact or template == "ai_video":
            body = ", ".join(value for _, value in ordered)
        elif template == "cinematic_story":
            pieces = []
            for label, value in ordered:
                if label is None:
                    pieces.append(value)
                else:
                    wrapper = CINEMATIC_WRAPPERS.get(label.lower())
                    pieces.append(wrapper.format(v=value) if wrapper else f"{label}: {value}")
            body = TEMPLATE_JOIN[template].join(pieces)
        else:
            pieces = [
                f"{label}: {value}" if label is not None else value
                for label, value in ordered
            ]
            body = TEMPLATE_JOIN[template].join(pieces)

        prompt = (prefix + body).strip()
        if prompt and not prompt.endswith("."):
            prompt += "."
        return prompt

    def _tokens(self, text: str) -> list:
        return re.findall(r"[a-z0-9]+", text.lower())

    def _is_preserved(self, source: str, prompt: str) -> bool:
        source_tokens = [
            t for t in self._tokens(source) if t not in prs.LABEL_TOKENS
        ]
        prompt_tokens = [
            t for t in self._tokens(prompt) if t not in prs.LABEL_TOKENS
        ]
        return not (Counter(source_tokens) - Counter(prompt_tokens))
