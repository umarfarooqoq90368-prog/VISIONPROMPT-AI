from abc import ABC, abstractmethod
from typing import Optional


class ShotBoundaryProvider(ABC):
    """Abstract base class for shot boundary detection providers.

    Subclasses implement `compare()` to compare two frame images
    and `infer_shot_type()` to classify the transition type.
    """

    @property
    @abstractmethod
    def model_name(self) -> str:
        """Return the provider/model identifier."""
        ...

    @abstractmethod
    def compare(
        self,
        frame_path_a: str,
        frame_path_b: str,
    ) -> float:
        """Compute a visual difference score between two frames.

        Args:
            frame_path_a: Path to the first frame image.
            frame_path_b: Path to the second frame image.

        Returns:
            A float in [0, 1] where 0 = identical, 1 = completely different.
        """
        ...

    def infer_shot_type(
        self,
        prev_score: float,
        curr_score: float,
        prev_change_score: Optional[float] = None,
    ) -> str:
        """Infer the transition type from consecutive comparison scores.

        Default implementation uses simple rules; subclasses may override.

        Args:
            prev_score: Comparison score between the frame before the previous
                and the previous frame.
            curr_score: Comparison score between the previous frame and the
                current frame.
            prev_change_score: The change score from before prev_score, if available.

        Returns:
            One of: "cut", "fade", "dissolve", "unknown", "None".
        """
        if prev_change_score is not None and prev_change_score < 0.25:
            return "cut"
        if abs(curr_score - prev_change_score or 0) < 0.05:
            return "unknown"
        return "dissolve"


def get_shot_provider(name: str = "heuristic") -> ShotBoundaryProvider:
    """Create a shot boundary provider by name.

    Args:
        name: Provider name. Currently only 'heuristic' is supported.

    Returns:
        An instance of the requested ShotBoundaryProvider.

    Raises:
        ValueError: If the provider name is not recognized.
    """
    if name == "heuristic":
        from app.ai.shot_providers import HeuristicShotProvider

        return HeuristicShotProvider()
    raise ValueError(f"Unknown shot provider: {name}")