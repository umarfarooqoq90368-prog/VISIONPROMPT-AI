"""Subject tracking and profiling from frame observations.

Uses heuristic text-based matching to identify recurring subjects
across frame observations. Does NOT perform facial recognition or
biometric identification.

Architecture:
    Frame Observations
         ↓
    Subject Extraction
         ↓
    Heuristic Matching
         ↓
    Subject Profile Building
         ↓
    Structured Subject Timeline
"""

import re
from pathlib import Path
from typing import Optional

from app.core.config import settings

DEFAULT_MATCH_THRESHOLD = 0.60
MAX_SUBJECTS = 100


def _normalize_text(text: str) -> str:
    """Normalize text for comparison: lowercase, strip punctuation."""
    text = text.lower().strip()
    text = re.sub(r'[^\w\s]', '', text)
    text = re.sub(r'\s+', ' ', text)
    return text.strip()


def _tokenize(text: str) -> set[str]:
    """Tokenize text into meaningful words."""
    normalized = _normalize_text(text)
    stop_words = {
        "the", "a", "an", "is", "are", "was", "were", "be", "been",
        "being", "have", "has", "had", "do", "does", "did", "will",
        "would", "could", "should", "may", "might", "shall", "can",
        "this", "that", "these", "those", "it", "its", "in", "on",
        "at", "to", "for", "of", "with", "by", "from", "and", "or",
        "but", "not", "no", "so", "if", "then", "than", "too",
        "very", "just", "about", "up", "out", "all", "any", "each",
        "every", "some", "such", "only", "own", "same", "other",
        "also", "new", "more", "most", "many", "much", "well",
        "back", "even", "still", "way", "use", "used",
    }
    words = normalized.split()
    return {w for w in words if w not in stop_words and len(w) > 1}


def _jaccard_similarity(set1: set[str], set2: set[str]) -> float:
    """Calculate Jaccard similarity between two word sets."""
    if not set1 and not set2:
        return 1.0
    if not set1 or not set2:
        return 0.0
    intersection = set1 & set2
    union = set1 | set2
    return len(intersection) / len(union) if union else 0.0


def _label_match_score(desc1: str, desc2: str) -> float:
    """Calculate a normalized match score between two descriptions.

    Uses token overlap and normalized text similarity.
    """
    norm1 = _normalize_text(desc1)
    norm2 = _normalize_text(desc2)

    if not norm1 and not norm2:
        return 1.0
    if not norm1 or not norm2:
        return 0.0

    # Direct label equality
    if norm1 == norm2:
        return 0.90

    tokens1 = _tokenize(desc1)
    tokens2 = _tokenize(desc2)

    token_sim = _jaccard_similarity(tokens1, tokens2)

    # Also check substring containment for key phrases
    words1 = set(norm1.split())
    words2 = set(norm2.split())
    containment = len(words1 & words2) / max(len(words1), len(words2), 1)

    # Weighted combination
    return round(0.5 * token_sim + 0.3 * containment + 0.2 * (
        1.0 if norm1[:20] == norm2[:20] else 0.0
    ), 4)


class SubjectProfile:
    """Represents a tracked subject across multiple frame observations."""

    def __init__(self, subject_id: str, label: str, description: str):
        self.subject_id = subject_id
        self.label = label
        self.description = description
        self.appearance_observations: list[str] = []
        self.actions: list[str] = []
        self.frames_seen: list[str] = []
        self.first_seen: Optional[float] = None
        self.last_seen: Optional[float] = None
        self._observations: list[str] = []

    def add_observation(
        self,
        description: str,
        action: Optional[str],
        frame_filename: str,
        timestamp: float,
    ):
        """Add an observation to this subject profile."""
        self._observations.append(description)
        if description and description not in self.appearance_observations:
            self.appearance_observations.append(description)
        if action and action not in self.actions:
            self.actions.append(action)
        if frame_filename not in self.frames_seen:
            self.frames_seen.append(frame_filename)

        if self.first_seen is None or timestamp < self.first_seen:
            self.first_seen = timestamp
        if self.last_seen is None or timestamp > self.last_seen:
            self.last_seen = timestamp

    def merge(self, other: "SubjectProfile"):
        """Merge another profile into this one."""
        for desc in other._observations:
            if desc not in self._observations:
                self._observations.append(desc)
                if desc not in self.appearance_observations:
                    self.appearance_observations.append(desc)
        for action in other.actions:
            if action not in self.actions:
                self.actions.append(action)
        for frame in other.frames_seen:
            if frame not in self.frames_seen:
                self.frames_seen.append(frame)
        if other.first_seen is not None and (self.first_seen is None or other.first_seen < self.first_seen):
            self.first_seen = other.first_seen
        if other.last_seen is not None and (self.last_seen is None or other.last_seen > self.last_seen):
            self.last_seen = other.last_seen

    def to_dict(self) -> dict:
        """Convert to serializable dict."""
        confidence = self._calculate_confidence()
        return {
            "subject_id": self.subject_id,
            "label": self.label,
            "description": self.description,
            "appearance_observations": self.appearance_observations,
            "actions": self.actions,
            "first_seen": round(self.first_seen, 4) if self.first_seen is not None else 0.0,
            "last_seen": round(self.last_seen, 4) if self.last_seen is not None else 0.0,
            "frames_seen": self.frames_seen,
            "confidence": confidence,
        }

    def _calculate_confidence(self) -> float:
        """Calculate heuristic confidence based on observation count.

        Represents observation matching confidence, NOT identity recognition.
        """
        if not self._observations:
            return 0.0
        # More observations and consistent descriptions increase confidence
        unique_descriptions = len(set(self._observations))
        observation_count = len(self._observations)
        base = min(observation_count * 0.15, 0.60)
        consistency = 1.0 if unique_descriptions <= 3 else 0.85
        return round(min(base * consistency + 0.30, 0.95), 4)


class SubjectTrackingService:
    """Tracks recurring subjects across frame observations using heuristics.

    Does NOT perform facial recognition or biometric identification.
    Uses text-based description matching as a heuristic.
    """

    def __init__(
        self,
        match_threshold: float = DEFAULT_MATCH_THRESHOLD,
        max_subjects: int = MAX_SUBJECTS,
    ):
        self.match_threshold = match_threshold
        self.max_subjects = max_subjects
        self._subjects: list[SubjectProfile] = []

    def analyze_observations(
        self,
        frame_observations: list[dict],
        analysis_subjects: list[str] = None,
        analysis_actions: list[str] = None,
    ) -> dict:
        """Analyze frame observations and build subject profiles.

        Args:
            frame_observations: List of observation dicts with
                'frame_index', 'timestamp_seconds', 'frame_filename',
                'description', 'model'.
            analysis_subjects: Subject labels from structured analysis.
            analysis_actions: Action labels from structured analysis.

        Returns:
            Dict with subject tracking results.
        """
        if analysis_subjects is None:
            analysis_subjects = []
        if analysis_actions is None:
            analysis_actions = []

        self._subjects = []

        # If structured analysis has subjects, use them directly
        if analysis_subjects:
            for i, subj in enumerate(analysis_subjects, start=1):
                profile = SubjectProfile(
                    subject_id=f"subject_{i}",
                    label=self._infer_label(subj),
                    description=subj,
                )
                # Try to associate actions
                for action in analysis_actions:
                    profile.actions.append(action)
                self._subjects.append(profile)

            return self._build_result()

        # Extract subjects from frame observations
        for obs in frame_observations:
            self._process_observation(obs)

        # If no subjects found, return empty
        if not self._subjects:
            return self._build_result()

        return self._build_result()

    def _process_observation(self, obs: dict):
        """Process a single frame observation to extract subjects."""
        description = obs.get("description", "")
        timestamp = obs.get("timestamp_seconds", 0.0)
        frame_filename = obs.get("frame_filename", "")

        if not description or description.strip() == "":
            return

        # Check if description is a placeholder/mock observation
        if "mock vision description" in description.lower():
            return

        # Extract candidate subject from description
        candidate_label = self._extract_candidate_subject(description)
        if not candidate_label:
            return

        # Try to match existing subject
        matched = False
        for subject in self._subjects:
            score = _label_match_score(subject.description, candidate_label)
            if score >= self.match_threshold:
                action = self._extract_action(description)
                subject.add_observation(
                    description=candidate_label,
                    action=action,
                    frame_filename=frame_filename,
                    timestamp=timestamp,
                )
                matched = True
                break

        if not matched and len(self._subjects) < self.max_subjects:
            action = self._extract_action(description)
            new_profile = SubjectProfile(
                subject_id=f"subject_{len(self._subjects) + 1}",
                label=self._infer_label(candidate_label),
                description=candidate_label,
            )
            new_profile.add_observation(
                description=candidate_label,
                action=action,
                frame_filename=frame_filename,
                timestamp=timestamp,
            )
            self._subjects.append(new_profile)

    def _extract_candidate_subject(self, description: str) -> Optional[str]:
        """Extract a candidate subject label from a description.

        Returns None for mock/placeholder descriptions.
        """
        if not description or "mock vision" in description.lower():
            return None

        # Simple heuristic: look for common subject patterns
        patterns = [
            r'(?:a |an |the |this |that )([a-z]+(?: [a-z]+)*)',
            r'^([A-Z][a-z]+(?: [a-z]+)*)',
        ]
        for pattern in patterns:
            match = re.search(pattern, description)
            if match:
                candidate = match.group(1).strip()
                if len(candidate) > 2:
                    return candidate

        # Fallback: use first meaningful word
        words = description.split()
        for word in words:
            clean = re.sub(r'[^\w]', '', word).strip()
            if len(clean) > 2 and clean.lower() not in {
                "a", "the", "an", "is", "are", "was", "were"
            }:
                return clean

        return None

    def _extract_action(self, description: str) -> Optional[str]:
        """Extract an action verb from description."""
        if not description or "mock vision" in description.lower():
            return None

        action_words = [
            "walking", "running", "standing", "sitting", "jumping",
            "opening", "closing", "looking", "talking", "moving",
            "holding", "wearing", "wearing", "driving", "riding",
            "entering", "exiting", "flying", "swimming",
        ]
        desc_lower = description.lower()
        for action in action_words:
            if action in desc_lower:
                return action
        return None

    def _infer_label(self, description: str) -> str:
        """Infer a generic label from a description."""
        if not description:
            return "unknown"
        desc_lower = description.lower()
        indicators = {
            "person": ["man", "woman", "young", "old", "person"],
            "vehicle": ["car", "truck", "bike", "bus", "train"],
            "animal": ["dog", "cat", "bird", "horse", "animal"],
            "object": ["box", "table", "chair", "bottle", "book"],
        }
        for label, keywords in indicators.items():
            for kw in keywords:
                if kw in desc_lower:
                    return label
        return "unknown"

    def _build_result(self) -> dict:
        """Build the final subject tracking result."""
        profiles = []
        for i, subject in enumerate(self._subjects[:self.max_subjects], start=1):
            subject.subject_id = f"subject_{i}"
            profiles.append(subject.to_dict())

        return {
            "subjects_detected": len(profiles),
            "subjects": profiles,
            "match_threshold": self.match_threshold,
        }


def track_subjects(
    frame_observations: list[dict],
    analysis_subjects: list[str] = None,
    analysis_actions: list[str] = None,
    match_threshold: float = DEFAULT_MATCH_THRESHOLD,
) -> dict:
    """Convenience function to track subjects from observations.

    Args:
        frame_observations: List of frame observation dicts.
        analysis_subjects: Subject labels from structured analysis.
        analysis_actions: Action labels from structured analysis.
        match_threshold: Heuristic matching threshold (0.0-1.0).

    Returns:
        Dict with subjects_detected and subjects list.
    """
    service = SubjectTrackingService(match_threshold=match_threshold)
    return service.analyze_observations(
        frame_observations=frame_observations,
        analysis_subjects=analysis_subjects,
        analysis_actions=analysis_actions,
    )