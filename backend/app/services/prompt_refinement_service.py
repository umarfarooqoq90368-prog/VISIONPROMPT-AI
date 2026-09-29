"""Prompt Refinement service (Day 14).

Refines an existing Day 13 generated production prompt while preserving the
factual information extracted from the video.

Supports six operations: refine, shorten, expand, cinematic, realistic,
commercial. Deterministic output. Never fabricates characters, objects,
locations, actions, camera movement, lighting, colors, dialogue, or sounds.
"""

import re
from typing import Optional

from app.services.advanced_prompt_service import DEFAULT_NEGATIVE_PROMPT

VALID_OPERATIONS = {
    "refine",
    "shorten",
    "expand",
    "cinematic",
    "realistic",
    "commercial",
}

STYLE_OPERATIONS = {"cinematic", "realistic", "commercial"}

STYLE_TERMS = {
    "cinematic": "cinematic composition",
    "realistic": "realistic presentation",
    "commercial": "commercial presentation",
}

DEFAULT_PROMPT_PREFIXES = {
    "cinematic": "cinematic",
    "realistic": "realistic",
    "commercial": "polished commercial",
}

_LABEL_NAMES = [
    "Camera perspective",
    "Shot type",
    "Camera movement",
    "Color palette",
    "Visual style",
    "Audio language",
    "Audio text",
    "Subject",
    "Profile",
    "Action",
    "Environment",
    "Objects",
    "Lighting",
    "Color",
    "Composition",
]

LABEL_PATTERN = re.compile(
    r"\b(?:" + "|".join(re.escape(n) for n in _LABEL_NAMES) + r")\s*:",
    re.IGNORECASE,
)

CLAUSE_BOUNDARY = re.compile(
    r"(?=(?:"
    + "|".join(
        re.escape(n) for n in sorted(_LABEL_NAMES, key=len, reverse=True)
    )
    + r")\s*:)"
)

LABEL_TOKENS = {
    "subject",
    "profile",
    "action",
    "environment",
    "objects",
    "camera",
    "perspective",
    "shot",
    "type",
    "movement",
    "lighting",
    "color",
    "palette",
    "visual",
    "style",
    "audio",
    "language",
    "text",
    "composition",
}

STYLE_TOKENS = {
    "cinematic",
    "realistic",
    "commercial",
    "composition",
    "presentation",
    "polished",
}


class PromptRefinementService:
    """Refines an existing generated prompt without altering its facts.

    All operations are deterministic and preserve the factual content of
    the source prompt. Style operations only rephrase style wording.
    """

    def refine(
        self,
        source_prompt: str,
        operation: str,
        negative_prompt: Optional[str] = None,
    ) -> dict:
        """Apply a refinement operation to an existing prompt.

        Args:
            source_prompt: Existing Day 13 generated prompt.
            operation: One of 'refine', 'shorten', 'expand', 'cinematic',
                'realistic', 'commercial'.
            negative_prompt: Optional negative prompt to carry through.

        Returns:
            Dict with 'operation', 'source_prompt', 'refined_prompt',
            'negative_prompt', and 'preserved_information' keys.

        Raises:
            ValueError: If the operation is invalid or the source is malformed.
        """
        if not isinstance(operation, str) or operation not in VALID_OPERATIONS:
            raise ValueError(
                "Invalid operation. Must be one of: "
                + ", ".join(sorted(VALID_OPERATIONS))
            )
        if not isinstance(source_prompt, str):
            raise ValueError("source_prompt must be a string.")

        source = source_prompt

        if not source.strip():
            refined = source
        elif operation == "refine":
            refined = self._refine_text(source)
        elif operation == "shorten":
            refined = self._shorten_text(source)
        elif operation == "expand":
            refined = self._expand_text(source)
        else:
            refined = self._apply_style(source, operation)

        preserved = self._is_preserved(source, refined, operation)
        if not preserved:
            refined = source
            preserved = True

        if isinstance(negative_prompt, str) and negative_prompt.strip():
            negative = negative_prompt
        else:
            negative = DEFAULT_NEGATIVE_PROMPT

        return {
            "operation": operation,
            "source_prompt": source,
            "refined_prompt": refined,
            "negative_prompt": negative,
            "preserved_information": preserved,
        }

    def _refine_text(self, source: str) -> str:
        """Restructure the source into clean sentences (same words)."""
        sentences = []
        for segment in source.split(";"):
            segment = segment.strip().rstrip(".").strip()
            if not segment:
                continue
            segment = segment[0].upper() + segment[1:]
            sentences.append(segment)
        if not sentences:
            return source.strip()
        return ". ".join(sentences) + "."

    def _shorten_text(self, source: str) -> str:
        """Produce a concise version, dropping labels, keeping all facts."""
        text = LABEL_PATTERN.sub(", ", source)
        parts = []
        for segment in text.split(";"):
            segment = re.sub(r"\s+", " ", segment)
            segment = re.sub(r"\s*,\s*", ", ", segment)
            segment = re.sub(r",\s*,+", ",", segment)
            segment = segment.strip().strip(",").strip()
            if segment:
                parts.append(segment)
        if not parts:
            return source.strip()
        refined = ", ".join(parts)
        if not refined.endswith("."):
            refined += "."
        return refined

    def _expand_text(self, source: str) -> str:
        """Split compound segments into individual detailed sentences."""
        sentences = []
        for segment in source.split(";"):
            segment = segment.strip()
            if not segment:
                continue
            for clause in CLAUSE_BOUNDARY.split(segment):
                clause = clause.strip().rstrip(".").strip()
                if not clause:
                    continue
                clause = clause[0].upper() + clause[1:]
                sentences.append(clause)
        if not sentences:
            return source.strip()
        return ". ".join(sentences) + "."

    def _apply_style(self, source: str, style: str) -> str:
        """Apply style wording without inventing visual details."""
        text = source
        for term in STYLE_TERMS.values():
            text = re.sub(r",?\s*" + re.escape(term), "", text, flags=re.IGNORECASE)

        style_names = "|".join(sorted(STYLE_TERMS))
        text = re.sub(
            r"(Visual style:\s*)(" + style_names + r")\b",
            r"\g<1>" + style,
            text,
            flags=re.IGNORECASE,
        )
        text = re.sub(
            r"\bA (cinematic|realistic|polished commercial) scene\b",
            "A " + DEFAULT_PROMPT_PREFIXES[style] + " scene",
            text,
            flags=re.IGNORECASE,
        )
        text = re.sub(r"\s+", " ", text).strip()

        if not text:
            return STYLE_TERMS[style] + "."

        term = STYLE_TERMS[style]
        if term not in text.lower():
            if text.endswith("."):
                text = text[:-1].rstrip()
            text = f"{text}, {term}."
        elif not text.endswith("."):
            text += "."
        return text

    def _tokens(self, text: str) -> list:
        return re.findall(r"[a-z0-9]+", text.lower())

    def _is_preserved(self, source: str, refined: str, operation: str) -> bool:
        source_tokens = self._tokens(source)
        refined_tokens = self._tokens(refined)
        if operation == "shorten":
            source_tokens = [t for t in source_tokens if t not in LABEL_TOKENS]
            refined_tokens = [t for t in refined_tokens if t not in LABEL_TOKENS]
        elif operation in STYLE_OPERATIONS:
            source_tokens = [t for t in source_tokens if t not in STYLE_TOKENS]
            refined_tokens = [t for t in refined_tokens if t not in STYLE_TOKENS]
        return source_tokens == refined_tokens
