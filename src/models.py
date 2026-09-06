"""Shared data structures for profile matching."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class MatchResult:
	"""Deterministic result returned by the opportunity matcher."""

	eligibility_status: str
	match_score: int
	reasons: list[str] = field(default_factory=list)
	missing_requirements: list[str] = field(default_factory=list)
	uncertain_requirements: list[str] = field(default_factory=list)

	def to_dict(self) -> dict[str, Any]:
		"""Return the result in the public JSON-friendly shape."""
		return {
			"eligibility_status": self.eligibility_status,
			"match_score": self.match_score,
			"reasons": self.reasons,
			"missing_requirements": self.missing_requirements,
			"uncertain_requirements": self.uncertain_requirements,
		}

