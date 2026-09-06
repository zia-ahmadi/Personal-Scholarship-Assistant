"""Deterministic profile-to-opportunity matching rules."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import yaml

from src.models import MatchResult


FACTOR_WEIGHTS = {
	"nationality": 25,
	"degree": 20,
	"field": 20,
	"gpa": 20,
	"english": 15,
}


def load_profile(profile_path: str | Path = "profile.yaml") -> dict[str, Any]:
	"""Load and validate the user's YAML profile."""
	with Path(profile_path).open("r", encoding="utf-8") as profile_file:
		profile = yaml.safe_load(profile_file) or {}

	if not isinstance(profile, dict):
		raise ValueError("Profile must contain a YAML mapping.")

	return profile


def match_opportunity(
	opportunity: dict[str, Any],
	profile: dict[str, Any],
) -> dict[str, Any]:
	"""Compare an analyzed opportunity with a profile without guessing."""
	result = MatchResult(eligibility_status="Uncertain", match_score=0)
	results = [
		_check_nationality(opportunity, profile),
		_check_degree(opportunity, profile),
		_check_field(opportunity, profile),
		_check_gpa(opportunity, profile),
		_check_english(opportunity, profile),
	]

	for factor, status, reason in results:
		weight = FACTOR_WEIGHTS[factor]
		if status == "pass":
			result.match_score += weight
			result.reasons.append(reason)
		elif status == "fail":
			result.reasons.append(reason)
		else:
			result.match_score += weight // 2
			result.uncertain_requirements.append(reason)

	result.missing_requirements.extend(_missing_profile_requirements(opportunity, profile))
	result.match_score = max(0, min(100, result.match_score))
	if any(status == "fail" for _, status, _ in results):
		result.eligibility_status = "Likely Not Eligible"
	elif result.uncertain_requirements:
		result.eligibility_status = "Uncertain"
	else:
		result.eligibility_status = "Likely Eligible"

	return result.to_dict()


def _missing_profile_requirements(
	opportunity: dict[str, Any], profile: dict[str, Any]
) -> list[str]:
	"""List required profile values that are not available for comparison."""
	missing: list[str] = []
	personal = profile.get("personal", {})
	education = profile.get("education", {})
	english = profile.get("english", {})

	if _text(opportunity.get("nationality_requirement")) and not _text(personal.get("nationality")):
		missing.append("Nationality")
	if _text(opportunity.get("degree_requirement")) and not _text(education.get("degree")):
		missing.append("Degree or education level")
	field_requirement = _text(opportunity.get("field_requirement"))
	if field_requirement and not _is_unrestricted_field(field_requirement) and not _text(education.get("field")):
		missing.append("Field of study")
	if _text(opportunity.get("gpa_requirement")) and education.get("gpa") is None:
		missing.append("GPA")
	language_requirement = _text(opportunity.get("english_requirement")).lower()
	if "ielts" in language_requirement and english.get("ielts") is None:
		missing.append("IELTS score")
	if "toefl" in language_requirement and english.get("toefl") is None:
		missing.append("TOEFL score")

	return missing


def _check_nationality(
	opportunity: dict[str, Any], profile: dict[str, Any]
) -> tuple[str, str, str]:
	requirement = _text(opportunity.get("nationality_requirement"))
	nationality = _text(profile.get("personal", {}).get("nationality"))
	if not requirement:
		return "nationality", "uncertain", "Nationality eligibility is not stated."
	if not nationality:
		return "nationality", "uncertain", "User nationality is missing."

	lowered = requirement.lower()
	if any(term in lowered for term in ("all nationalities", "any nationality", "international")):
		return "nationality", "pass", "The opportunity accepts international applicants."
	if nationality.lower() in lowered:
		return "nationality", "pass", "The user's nationality is listed as eligible."
	if any(term in lowered for term in ("eu only", "eea only", "european union only")):
		return "nationality", "fail", "The opportunity is restricted to a nationality group that excludes the user."
	return "nationality", "uncertain", "The nationality requirement is unclear for the user."


def _check_degree(
	opportunity: dict[str, Any], profile: dict[str, Any]
) -> tuple[str, str, str]:
	requirement = _text(opportunity.get("degree_requirement"))
	degree = _text(profile.get("education", {}).get("degree"))
	if not requirement:
		return "degree", "uncertain", "Degree eligibility is not stated."
	if not degree:
		return "degree", "uncertain", "User education level is missing."

	required_levels = _degree_levels(requirement)
	profile_level = _degree_level(degree)
	if not required_levels or profile_level is None:
		return "degree", "uncertain", "The degree requirement cannot be compared clearly."
	if profile_level in required_levels:
		return "degree", "pass", "The user's education level meets the stated degree requirement."
	if required_levels == {"master"} and profile_level == "bachelor":
		return "degree", "pass", "A bachelor's degree is the usual entry qualification for a master's opportunity."
	return "degree", "fail", "The user's education level does not meet the stated degree requirement."


def _check_field(
	opportunity: dict[str, Any], profile: dict[str, Any]
) -> tuple[str, str, str]:
	requirement = _text(opportunity.get("field_requirement"))
	field = _text(profile.get("education", {}).get("field"))
	if not requirement:
		return "field", "uncertain", "Field eligibility is not stated."
	if _is_unrestricted_field(requirement):
		return "field", "pass", "The opportunity accepts applicants from any academic field."
	if not field:
		return "field", "uncertain", "User field of study is missing."
	if _field_matches(requirement, field):
		return "field", "pass", "The user's field of study matches the opportunity."
	if _looks_exclusive(requirement):
		return "field", "fail", "The user's field of study does not match the stated field requirement."
	return "field", "uncertain", "The field requirement is unclear for the user's field."


def _check_gpa(
	opportunity: dict[str, Any], profile: dict[str, Any]
) -> tuple[str, str, str]:
	requirement = _text(opportunity.get("gpa_requirement"))
	if not requirement:
		return "gpa", "pass", "No GPA requirement is stated."
	required_gpa = _number_in_text(requirement)
	user_gpa = profile.get("education", {}).get("gpa")
	if required_gpa is None:
		return "gpa", "uncertain", "The GPA requirement is not numeric or clearly comparable."
	if user_gpa is None:
		return "gpa", "uncertain", "The opportunity requires a GPA, but the user's GPA is missing."
	try:
		user_gpa_value = float(user_gpa)
	except (TypeError, ValueError):
		return "gpa", "uncertain", "The user's GPA is not clearly numeric."
	if user_gpa_value >= required_gpa:
		return "gpa", "pass", "The user's GPA meets the stated minimum."
	return "gpa", "fail", "The user's GPA is below the stated minimum."


def _check_english(
	opportunity: dict[str, Any], profile: dict[str, Any]
) -> tuple[str, str, str]:
	requirement = _text(opportunity.get("english_requirement"))
	if not requirement:
		return "english", "pass", "No English or language requirement is stated."

	profile_english = profile.get("english", {})
	required_score = _number_in_text(requirement)
	if "ielts" in requirement.lower():
		user_score = profile_english.get("ielts")
		test_name = "IELTS"
	elif "toefl" in requirement.lower():
		user_score = profile_english.get("toefl")
		test_name = "TOEFL"
	else:
		return "english", "uncertain", "The language requirement cannot be compared with the available profile information."

	if required_score is None:
		return "english", "uncertain", f"The {test_name} requirement is not numeric or clearly comparable."
	if user_score is None:
		return "english", "uncertain", f"The opportunity requires {test_name}, but the user's score is missing."
	try:
		user_score_value = float(user_score)
	except (TypeError, ValueError):
		return "english", "uncertain", f"The user's {test_name} score is not clearly numeric."
	if user_score_value >= required_score:
		return "english", "pass", f"The user's {test_name} score meets the stated minimum."
	return "english", "fail", f"The user's {test_name} score is below the stated minimum."


def _text(value: Any) -> str:
	return value.strip() if isinstance(value, str) else ""


def _number_in_text(value: str) -> float | None:
	match = re.search(r"\d+(?:\.\d+)?", value)
	return float(match.group()) if match else None


def _degree_level(value: str) -> str | None:
	lowered = value.lower()
	if re.search(r"\b(phd|doctorate|doctoral)\b", lowered):
		return "phd"
	if re.search(r"\b(master|graduate)\b", lowered):
		return "master"
	if re.search(r"\b(bachelor|undergraduate)\b", lowered):
		return "bachelor"
	return None


def _degree_levels(value: str) -> set[str]:
	"""Return every normalized degree level accepted by a requirement."""
	levels: set[str] = set()
	for level, terms in {
		"bachelor": ("bachelor", "undergraduate"),
		"master": ("master", "graduate"),
		"phd": ("phd", "doctorate", "doctoral"),
	}.items():
		if any(re.search(rf"\b{term}\b", value.lower()) for term in terms):
			levels.add(level)
	return levels


def _field_matches(requirement: str, field: str) -> bool:
	if _is_unrestricted_field(requirement):
		return True
	requirement_words = set(re.findall(r"[a-z]+", requirement.lower()))
	field_words = set(re.findall(r"[a-z]+", field.lower()))
	aliases = {
		"cs": "computer",
		"computing": "computer",
		"software": "software",
	}
	normalized_requirement = {aliases.get(word, word) for word in requirement_words}
	normalized_field = {aliases.get(word, word) for word in field_words}
	return bool(normalized_requirement & normalized_field) or field.lower() in requirement.lower()


def _is_unrestricted_field(requirement: str) -> bool:
	"""Identify requirements that explicitly accept any academic field."""
	normalized = re.sub(r"[^a-z]+", " ", requirement.lower()).strip()
	return normalized in {
		"all",
		"all fields",
		"any field",
		"any fields",
		"any discipline",
		"any subject",
		"no field restriction",
		"field of study not restricted",
	}


def _looks_exclusive(requirement: str) -> bool:
	lowered = requirement.lower()
	return any(term in lowered for term in ("only", "must be", "required", "restricted"))


if __name__ == "__main__":
	sample_opportunity = {
		"title": "Computer Science Master's Scholarship",
		"nationality_requirement": "Open to international students",
		"degree_requirement": "Bachelor's degree required",
		"field_requirement": "Computer Science or related field",
		"gpa_requirement": "Minimum GPA 3.0",
		"english_requirement": "IELTS 6.5 required",
	}
	print(match_opportunity(sample_opportunity, load_profile()))

