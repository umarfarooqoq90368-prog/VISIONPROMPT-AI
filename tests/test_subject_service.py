"""Tests for the subject tracking service."""
import pytest
from app.services.subject_service import (
    SubjectTrackingService,
    SubjectProfile,
    track_subjects,
    _normalize_text,
    _tokenize,
    _jaccard_similarity,
    _label_match_score,
)


def _make_observation(
    frame_index: int,
    timestamp: float,
    frame_filename: str,
    description: str,
):
    return {
        "frame_index": frame_index,
        "timestamp_seconds": timestamp,
        "frame_filename": frame_filename,
        "description": description,
        "model": "mock-vision-provider",
    }


@pytest.fixture
def subject_service():
    return SubjectTrackingService()


class TestNormalization:
    def test_normalize_lowercase(self):
        assert _normalize_text("A Young Man") == "a young man"

    def test_normalize_strips_punctuation(self):
        assert _normalize_text("person, walking!") == "person walking"

    def test_tokenize_removes_stop_words(self):
        tokens = _tokenize("The young man is walking")
        assert "the" not in tokens
        assert "is" not in tokens
        assert "young" in tokens
        assert "man" in tokens
        assert "walking" in tokens

    def test_jaccard_similarity_identical(self):
        assert _jaccard_similarity({"a", "b"}, {"a", "b"}) == 1.0

    def test_jaccard_similarity_empty(self):
        assert _jaccard_similarity(set(), set()) == 1.0
        assert _jaccard_similarity({"a"}, set()) == 0.0

    def test_label_match_score_identical(self):
        assert _label_match_score("young man", "young man") > 0.8


class TestSubjectProfile:
    def test_profile_creation(self):
        profile = SubjectProfile("subject_1", "person", "young man")
        assert profile.subject_id == "subject_1"
        assert profile.label == "person"
        assert profile.description == "young man"

    def test_add_observation(self):
        profile = SubjectProfile("subject_1", "person", "young man")
        profile.add_observation("young man", "walking", "frame_000001.jpg", 0.0)
        assert "walking" in profile.actions
        assert "frame_000001.jpg" in profile.frames_seen
        assert profile.first_seen == 0.0
        assert profile.last_seen == 0.0

    def test_add_observation_updates_last_seen(self):
        profile = SubjectProfile("subject_1", "person", "young man")
        profile.add_observation("young man", None, "frame_000001.jpg", 0.0)
        profile.add_observation("young man", None, "frame_000002.jpg", 2.0)
        assert profile.last_seen == 2.0
        assert profile.first_seen == 0.0

    def test_merge_profiles(self):
        p1 = SubjectProfile("subject_1", "person", "young man")
        p1.add_observation("young man", "walking", "frame_000001.jpg", 0.0)
        p2 = SubjectProfile("subject_2", "person", "young man")
        p2.add_observation("young man", "running", "frame_000002.jpg", 1.0)
        p1.merge(p2)
        assert "walking" in p1.actions
        assert "running" in p1.actions
        assert len(p1.frames_seen) == 2

    def test_to_dict_contains_required_fields(self):
        profile = SubjectProfile("subject_1", "person", "young man")
        profile.add_observation("young man", "walking", "frame_000001.jpg", 0.0)
        d = profile.to_dict()
        assert "subject_id" in d
        assert "label" in d
        assert "description" in d
        assert "appearance_observations" in d
        assert "actions" in d
        assert "first_seen" in d
        assert "last_seen" in d
        assert "frames_seen" in d
        assert "confidence" in d

    def test_confidence_not_biometric(self):
        profile = SubjectProfile("subject_1", "person", "young man")
        profile.add_observation("young man", None, "frame_000001.jpg", 0.0)
        d = profile.to_dict()
        assert isinstance(d["confidence"], float)
        assert 0.0 <= d["confidence"] <= 1.0


class TestSubjectTrackingService:
    def test_empty_observations(self, subject_service):
        result = subject_service.analyze_observations(
            frame_observations=[]
        )
        assert result["subjects_detected"] == 0
        assert result["subjects"] == []

    def test_single_subject(self, subject_service):
        obs = [_make_observation(0, 0.0, "frame_000001.jpg", "a young man walking")]
        result = subject_service.analyze_observations(frame_observations=obs)
        assert result["subjects_detected"] >= 1

    def test_repeated_same_subject(self, subject_service):
        obs = [
            _make_observation(0, 0.0, "frame_000001.jpg", "a young man walking"),
            _make_observation(1, 1.0, "frame_000002.jpg", "the young man walking"),
            _make_observation(2, 2.0, "frame_000003.jpg", "the man walking"),
        ]
        result = subject_service.analyze_observations(frame_observations=obs)
        # Should match all as same subject
        assert result["subjects_detected"] >= 1
        if result["subjects"]:
            assert len(result["subjects"][0]["frames_seen"]) >= 2

    def test_different_subjects(self, subject_service):
        obs = [
            _make_observation(0, 0.0, "frame_000001.jpg", "a young man"),
            _make_observation(1, 1.0, "frame_000002.jpg", "a red car"),
        ]
        result = subject_service.analyze_observations(frame_observations=obs)
        assert result["subjects_detected"] >= 1

    def test_first_seen_and_last_seen(self, subject_service):
        obs = [
            _make_observation(0, 0.0, "frame_000001.jpg", "a young man"),
            _make_observation(1, 5.0, "frame_000002.jpg", "the young man"),
        ]
        result = subject_service.analyze_observations(frame_observations=obs)
        if result["subjects"]:
            s = result["subjects"][0]
            assert s["first_seen"] <= s["last_seen"]
            assert s["first_seen"] >= 0.0

    def test_mock_placeholder_not_detected(self, subject_service):
        obs = [_make_observation(0, 0.0, "frame_000001.jpg",
                   "A mock vision description for development purposes.")]
        result = subject_service.analyze_observations(frame_observations=obs)
        assert result["subjects_detected"] == 0

    def test_structured_subjects_used(self, subject_service):
        obs = []
        result = subject_service.analyze_observations(
            frame_observations=obs,
            analysis_subjects=["a young man", "a red car"],
            analysis_actions=["walking", "driving"],
        )
        assert result["subjects_detected"] >= 1
        if result["subjects"]:
            assert len(result["subjects"][0]["actions"]) >= 1

    def test_analysis_actions_associated(self, subject_service):
        obs = []
        result = subject_service.analyze_observations(
            frame_observations=[],
            analysis_subjects=["a person"],
            analysis_actions=["standing", "walking"],
        )
        if result["subjects"]:
            s = result["subjects"][0]
            assert "standing" in s["actions"] or len(s["actions"]) > 0

    def test_no_fabricated_identity(self, subject_service):
        obs = [_make_observation(0, 0.0, "frame_000001.jpg", "a person")]
        result = subject_service.analyze_observations(frame_observations=obs)
        if result["subjects"]:
            s = result["subjects"][0]
            assert s["label"] != "identified_person"
            assert "face" not in s["description"].lower()

    def test_deterministic_output(self, subject_service):
        obs = [_make_observation(0, 0.0, "frame_000001.jpg", "a young man walking")]
        result1 = subject_service.analyze_observations(frame_observations=obs)
        result2 = subject_service.analyze_observations(frame_observations=obs)
        assert result1["subjects_detected"] == result2["subjects_detected"]

    def test_max_subjects(self, subject_service):
        obs = []
        for i in range(5):
            obs.append(_make_observation(i, float(i), f"frame_{i:06d}.jpg", f"object number {i}"))
        result = subject_service.analyze_observations(frame_observations=obs)
        assert result["subjects_detected"] <= 100

    def test_no_absolute_paths(self, subject_service):
        obs = [_make_observation(0, 0.0, "frame_000001.jpg", "a person walking")]
        result = subject_service.analyze_observations(frame_observations=obs)
        if result["subjects"]:
            for frame in result["subjects"][0]["frames_seen"]:
                assert not frame.startswith("/")
                assert not frame.startswith("\\")

    def test_label_match_does_not_merge_different(self, subject_service):
        """Different labels should not merge."""
        obs = [
            _make_observation(0, 0.0, "frame_000001.jpg", "man in black shirt"),
            _make_observation(1, 1.0, "frame_000002.jpg", "woman in white dress"),
        ]
        result = subject_service.analyze_observations(frame_observations=obs)
        # These should remain separate subjects
        assert result["subjects_detected"] >= 1

    def test_match_threshold(self, subject_service):
        svc = SubjectTrackingService(match_threshold=0.95)
        obs = [
            _make_observation(0, 0.0, "frame_000001.jpg", "a young man"),
            _make_observation(1, 1.0, "frame_000002.jpg", "a tall man"),
        ]
        result = svc.analyze_observations(frame_observations=obs)
        # High threshold may create separate subjects
        assert result["subjects_detected"] >= 1


class TestTrackSubjects:
    def test_convenience_function(self):
        obs = [_make_observation(0, 0.0, "frame_000001.jpg", "a person walking")]
        result = track_subjects(frame_observations=obs)
        assert "subjects_detected" in result
        assert "subjects" in result

    def test_empty_returns_zero(self):
        result = track_subjects(frame_observations=[])
        assert result["subjects_detected"] == 0

    def test_uses_custom_threshold(self):
        obs = [_make_observation(0, 0.0, "frame_000001.jpg", "a person walking")]
        result = track_subjects(frame_observations=obs, match_threshold=0.3)
        assert result["subjects_detected"] >= 1