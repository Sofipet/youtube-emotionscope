from __future__ import annotations

import json
from pathlib import Path
from typing import Any


EVAL_MANIFEST_PATH = Path("data/eval/eval_manifest.json")
COMMENT_CASES_PATH = Path("data/eval/comment_eval_cases.json")
OUTPUT_PATH = Path("data/eval/auto_eval_results.json")

ANALYSIS_CACHE_DIR = Path("data/cache/analysis")
AGENT_CACHE_DIR = Path("data/cache/agent_insights")

ALLOWED_PRIMARY = {
    "anger",
    "fear",
    "sadness",
    "disgust",
    "joy",
    "trust",
    "anticipation",
    "surprise",
}
ALLOWED_VALENCE = {"positive", "negative", "mixed", "neutral"}


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def safe_mean(values: list[float]) -> float | None:
    if not values:
        return None
    return round(sum(values) / len(values), 4)


def in_range(x: float, low: float, high: float) -> bool:
    return low <= x <= high


def find_analysis_by_video_id(video_id: str) -> dict[str, Any]:
    for path in ANALYSIS_CACHE_DIR.glob("*.json"):
        raw = load_json(path)
        payload = raw.get("payload", raw)
        if payload.get("video", {}).get("video_id") == video_id:
            return raw
    raise FileNotFoundError(f"No analysis cache found for video_id={video_id}")


def find_agent_by_video_id_and_question(video_id: str, question: str) -> dict[str, Any]:
    for path in AGENT_CACHE_DIR.glob("*.json"):
        raw = load_json(path)
        if raw.get("video_id") == video_id and raw.get("question") == question:
            return raw
    raise FileNotFoundError(f"No agent cache found for video_id={video_id}, question={question}")


def check_comment_case(case: dict[str, Any]) -> dict[str, Any]:
    primary = case.get("expected_primary_emotion_options", [])
    valence = case.get("expected_valence_options", [])
    intensity_range = case.get("expected_intensity_range", [])
    nuanced = case.get("expected_nuanced_options", [])

    detected_language_present = case.get("detected_language") is not None
    expected_primary_options_valid = all(p in ALLOWED_PRIMARY for p in primary)
    expected_valence_options_valid = all(v in ALLOWED_VALENCE for v in valence)
    expected_intensity_range_valid = (
        isinstance(intensity_range, list)
        and len(intensity_range) == 2
        and all(isinstance(x, (int, float)) for x in intensity_range)
        and 0.0 <= intensity_range[0] <= 1.0
        and 0.0 <= intensity_range[1] <= 1.0
        and intensity_range[0] <= intensity_range[1]
    )
    expected_nuanced_options_valid = isinstance(nuanced, list)

    required_fields_present = all(
        case.get(field) is not None
        for field in [
            "case_id",
            "video_id",
            "comment_id",
            "text",
            "expected_primary_emotion_options",
            "expected_valence_options",
            "expected_intensity_range",
            "expected_nuanced_options",
        ]
    )

    return {
        "case_id": case["case_id"],
        "required_fields_present": required_fields_present,
        "detected_language_present": detected_language_present,
        "expected_primary_options_valid": expected_primary_options_valid,
        "expected_valence_options_valid": expected_valence_options_valid,
        "expected_intensity_range_valid": expected_intensity_range_valid,
        "expected_nuanced_options_valid": expected_nuanced_options_valid,
    }


def check_video_case(case: dict[str, Any], analysis_payload: dict[str, Any]) -> dict[str, Any]:
    top_primary = analysis_payload.get("top_primary_emotions", [])
    dominant_generated = top_primary[0]["emotion"] if top_primary else None

    dominant_match = dominant_generated in case.get("expected_dominant_emotion_options", [])

    negative_valence = analysis_payload.get("valence", {}).get("negative")
    negative_valence_ok = (
        isinstance(negative_valence, (int, float))
        and negative_valence >= case.get("expected_negative_valence_min", 0.0)
    )

    languages = [
        item.get("language_label")
        for item in analysis_payload.get("video", {}).get("languages", [])
    ]
    expected_languages = case.get("expected_language_contains", [])
    languages_ok = all(lang in languages for lang in expected_languages)

    prevalence_ok = True
    intensity_ok = True

    for item in top_primary:
        if not in_range(float(item.get("prevalence", -1)), 0.0, 1.0):
            prevalence_ok = False
        if not in_range(float(item.get("avg_intensity", -1)), 0.0, 1.0):
            intensity_ok = False

    valence_ok = True
    for key in ["positive", "negative", "mixed", "neutral"]:
        value = analysis_payload.get("valence", {}).get(key)
        if value is None or not in_range(float(value), 0.0, 1.0):
            valence_ok = False

    timeline = analysis_payload.get("timeline", [])
    timeline_structure_ok = isinstance(timeline, list) and len(timeline) > 0
    if timeline_structure_ok:
        for point in timeline:
            if "date" not in point or "comment_count" not in point or "valence" not in point:
                timeline_structure_ok = False
                break

    representative_comments = analysis_payload.get("representative_comments", [])
    representative_comments_valid = isinstance(representative_comments, list) and len(representative_comments) > 0
    if representative_comments_valid:
        for c in representative_comments:
            if "comment_id" not in c or "text" not in c:
                representative_comments_valid = False
                break

    return {
        "case_id": case["case_id"],
        "video_id": case["video_id"],
        "dominant_generated": dominant_generated,
        "dominant_match": dominant_match,
        "negative_valence_ok": negative_valence_ok,
        "languages_ok": languages_ok,
        "prevalence_ok": prevalence_ok,
        "intensity_ok": intensity_ok,
        "valence_ok": valence_ok,
        "timeline_structure_ok": timeline_structure_ok,
        "representative_comments_valid": representative_comments_valid,
    }


def check_agent_case(case: dict[str, Any], agent_payload: dict[str, Any]) -> dict[str, Any]:
    payload = agent_payload.get("payload", agent_payload)
    answer = payload.get("answer")
    followups = payload.get("suggested_followups")
    tools_used = payload.get("tools_used", [])

    answer_present = isinstance(answer, str) and len(answer.strip()) > 0
    followups_valid = isinstance(followups, list)

    acceptable_tools = set(case.get("acceptable_tools", []))
    tools_used_set = set(tools_used)
    acceptable_tools_overlap = len(acceptable_tools.intersection(tools_used_set)) > 0
    only_known_expected_tools = tools_used_set.issubset(acceptable_tools) if tools_used_set else False

    required_concepts = case.get("required_concepts", [])
    answer_lc = (answer or "").lower()
    required_concepts_present = all(concept.lower() in answer_lc for concept in required_concepts)

    return {
        "case_id": case["case_id"],
        "video_id": case["video_id"],
        "question": case["question"],
        "answer_present": answer_present,
        "followups_valid": followups_valid,
        "tools_used": tools_used,
        "acceptable_tools_overlap": acceptable_tools_overlap,
        "only_known_expected_tools": only_known_expected_tools,
        "required_concepts_present": required_concepts_present,
    }


def main() -> None:
    manifest = load_json(EVAL_MANIFEST_PATH)
    comment_cases_payload = load_json(COMMENT_CASES_PATH)
    comment_cases = comment_cases_payload["cases"]

    comment_results = [check_comment_case(case) for case in comment_cases]

    video_results = []
    for case in manifest["videos"]:
        analysis_raw = find_analysis_by_video_id(case["video_id"])
        analysis_payload = analysis_raw.get("payload", analysis_raw)
        video_results.append(check_video_case(case, analysis_payload))

    agent_results = []
    for case in manifest["agent_cases"]:
        agent_raw = find_agent_by_video_id_and_question(case["video_id"], case["question"])
        agent_results.append(check_agent_case(case, agent_raw))

    summary = {
        "comment_cases_total": len(comment_results),
        "video_cases_total": len(video_results),
        "agent_cases_total": len(agent_results),

        "comment_required_fields_present_rate": safe_mean([
            1.0 if r["required_fields_present"] else 0.0 for r in comment_results
        ]),
        "comment_detected_language_present_rate": safe_mean([
            1.0 if r["detected_language_present"] else 0.0 for r in comment_results
        ]),
        "comment_expected_primary_options_valid_rate": safe_mean([
            1.0 if r["expected_primary_options_valid"] else 0.0 for r in comment_results
        ]),
        "comment_expected_valence_options_valid_rate": safe_mean([
            1.0 if r["expected_valence_options_valid"] else 0.0 for r in comment_results
        ]),
        "comment_expected_intensity_range_valid_rate": safe_mean([
            1.0 if r["expected_intensity_range_valid"] else 0.0 for r in comment_results
        ]),
        "comment_expected_nuanced_options_valid_rate": safe_mean([
            1.0 if r["expected_nuanced_options_valid"] else 0.0 for r in comment_results
        ]),

        "video_dominant_match_rate": safe_mean([
            1.0 if r["dominant_match"] else 0.0 for r in video_results
        ]),
        "video_negative_valence_ok_rate": safe_mean([
            1.0 if r["negative_valence_ok"] else 0.0 for r in video_results
        ]),
        "video_languages_ok_rate": safe_mean([
            1.0 if r["languages_ok"] else 0.0 for r in video_results
        ]),
        "video_prevalence_ok_rate": safe_mean([
            1.0 if r["prevalence_ok"] else 0.0 for r in video_results
        ]),
        "video_intensity_ok_rate": safe_mean([
            1.0 if r["intensity_ok"] else 0.0 for r in video_results
        ]),
        "video_valence_ok_rate": safe_mean([
            1.0 if r["valence_ok"] else 0.0 for r in video_results
        ]),
        "video_timeline_structure_ok_rate": safe_mean([
            1.0 if r["timeline_structure_ok"] else 0.0 for r in video_results
        ]),
        "video_representative_comments_valid_rate": safe_mean([
            1.0 if r["representative_comments_valid"] else 0.0 for r in video_results
        ]),

        "agent_answer_present_rate": safe_mean([
            1.0 if r["answer_present"] else 0.0 for r in agent_results
        ]),
        "agent_followups_valid_rate": safe_mean([
            1.0 if r["followups_valid"] else 0.0 for r in agent_results
        ]),
        "agent_acceptable_tools_overlap_rate": safe_mean([
            1.0 if r["acceptable_tools_overlap"] else 0.0 for r in agent_results
        ]),
        "agent_only_known_expected_tools_rate": safe_mean([
            1.0 if r["only_known_expected_tools"] else 0.0 for r in agent_results
        ]),
        "agent_required_concepts_present_rate": safe_mean([
            1.0 if r["required_concepts_present"] else 0.0 for r in agent_results
        ]),
    }

    output = {
        "summary": summary,
        "comment_results": comment_results,
        "video_results": video_results,
        "agent_results": agent_results,
    }

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(
        json.dumps(output, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print(f"Saved auto evaluation results to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()