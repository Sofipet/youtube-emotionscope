from __future__ import annotations

import json
from pathlib import Path
from typing import Any


MANIFEST_PATH = Path("data/eval/eval_manifest.json")
COMMENT_CASES_PATH = Path("data/eval/comment_eval_cases.json")
OUTPUT_PATH = Path("data/eval/case_comparison_results.json")

ANALYSIS_CACHE_DIR = Path("data/cache/analysis")
AGENT_CACHE_DIR = Path("data/cache/agent_insights")
CLASSIFIED_DIR = Path("data/artifacts/classified")


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def safe_mean(values: list[float]) -> float | None:
    if not values:
        return None
    return round(sum(values) / len(values), 4)


def find_analysis_by_video_id(video_id: str) -> dict[str, Any]:
    for path in ANALYSIS_CACHE_DIR.glob("*.json"):
        raw = load_json(path)
        payload = raw.get("payload", raw)
        if payload.get("video", {}).get("video_id") == video_id:
            return payload
    raise FileNotFoundError(f"No analysis cache found for video_id={video_id}")


def find_agent_by_video_id_and_question(video_id: str, question: str) -> dict[str, Any]:
    for path in AGENT_CACHE_DIR.glob("*.json"):
        raw = load_json(path)
        if raw.get("video_id") == video_id and raw.get("question") == question:
            return raw.get("payload", raw)
    raise FileNotFoundError(f"No agent cache found for video_id={video_id}, question={question}")


def extract_comment_list(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        if payload and isinstance(payload[0], dict) and "comment_id" in payload[0]:
            return payload

    if isinstance(payload, dict):
        for key in ["classified_comments", "comments", "items", "classified", "payload"]:
            if key in payload:
                extracted = extract_comment_list(payload[key])
                if extracted:
                    return extracted

    return []


def detect_video_id(payload: Any, path: Path) -> str | None:
    if isinstance(payload, dict):
        if "video_id" in payload and isinstance(payload["video_id"], str):
            return payload["video_id"]

        if "video" in payload and isinstance(payload["video"], dict):
            video_id = payload["video"].get("video_id")
            if isinstance(video_id, str):
                return video_id

        if "payload" in payload:
            nested = detect_video_id(payload["payload"], path)
            if nested:
                return nested

    return path.stem.split("__")[0]


def build_classified_comment_index() -> dict[str, dict[str, dict[str, Any]]]:
    index: dict[str, dict[str, dict[str, Any]]] = {}

    for path in CLASSIFIED_DIR.glob("*.json"):
        raw = load_json(path)
        video_id = detect_video_id(raw, path)
        comments = extract_comment_list(raw)

        if not video_id or not comments:
            continue

        index.setdefault(video_id, {})
        for c in comments:
            comment_id = c.get("comment_id")
            if comment_id:
                index[video_id][comment_id] = c

    return index


def compare_comment_case(case: dict[str, Any], classified_index: dict[str, dict[str, dict[str, Any]]]) -> dict[str, Any]:
    video_id = case["video_id"]
    comment_id = case["comment_id"]

    generated = classified_index.get(video_id, {}).get(comment_id)
    if generated is None:
        return {
            "case_id": case["case_id"],
            "video_id": video_id,
            "comment_id": comment_id,
            "found_generated_comment": False
        }

    generated_primary = generated.get("primary_emotion")
    generated_valence = generated.get("valence")
    generated_intensity = generated.get("emotion_intensity")
    generated_nuanced = generated.get("nuanced_emotion")

    primary_match = generated_primary in case.get("expected_primary_emotion_options", [])
    valence_match = generated_valence in case.get("expected_valence_options", [])

    intensity_range = case.get("expected_intensity_range", [0.0, 1.0])
    intensity_match = (
        isinstance(generated_intensity, (int, float))
        and intensity_range[0] <= float(generated_intensity) <= intensity_range[1]
    )

    nuanced_options = case.get("expected_nuanced_options", [])
    nuanced_match = generated_nuanced in nuanced_options

    return {
        "case_id": case["case_id"],
        "video_id": video_id,
        "comment_id": comment_id,
        "found_generated_comment": True,
        "generated_primary_emotion": generated_primary,
        "generated_valence": generated_valence,
        "generated_emotion_intensity": generated_intensity,
        "generated_nuanced_emotion": generated_nuanced,
        "primary_match": primary_match,
        "valence_match": valence_match,
        "intensity_match": intensity_match,
        "nuanced_match": nuanced_match
    }


def compare_video_case(case: dict[str, Any], analysis_payload: dict[str, Any]) -> dict[str, Any]:
    top_primary = analysis_payload.get("top_primary_emotions", [])
    dominant_generated = top_primary[0]["emotion"] if top_primary else None

    secondary_generated = top_primary[1]["emotion"] if len(top_primary) > 1 else None

    dominant_match = dominant_generated in case.get("expected_dominant_emotion_options", [])
    secondary_match = secondary_generated in case.get("expected_secondary_emotion_options", [])

    negative_valence = analysis_payload.get("valence", {}).get("negative", 0.0)
    negative_valence_ok = negative_valence >= case.get("expected_negative_valence_min", 0.0)

    language_labels = [
        item.get("language_label")
        for item in analysis_payload.get("video", {}).get("languages", [])
    ]
    language_match = all(
        expected in language_labels
        for expected in case.get("expected_language_contains", [])
    )

    warnings_generated = analysis_payload.get("warnings", [])
    expected_warning_options = case.get("expected_warning_options", [])
    warnings_match = (
        warnings_generated == expected_warning_options
        if expected_warning_options == []
        else all(w in expected_warning_options for w in warnings_generated)
    )

    return {
        "case_id": case["case_id"],
        "video_id": case["video_id"],
        "generated_dominant_emotion": dominant_generated,
        "generated_secondary_emotion": secondary_generated,
        "generated_negative_valence": negative_valence,
        "generated_languages": language_labels,
        "generated_warnings": warnings_generated,
        "dominant_match": dominant_match,
        "secondary_match": secondary_match,
        "negative_valence_ok": negative_valence_ok,
        "language_match": language_match,
        "warnings_match": warnings_match
    }


def compare_agent_case(case: dict[str, Any], agent_payload: dict[str, Any]) -> dict[str, Any]:
    answer = agent_payload.get("answer", "")
    answer_lc = answer.lower()
    tools_used = agent_payload.get("tools_used", [])

    required_concepts = case.get("required_concepts", [])
    required_concepts_present = all(concept.lower() in answer_lc for concept in required_concepts)

    focus_options = case.get("expected_focus_options", [])
    focus_match = any(
        all(word in answer_lc for word in option.lower().split()[:2])
        for option in focus_options
    )

    acceptable_tools = set(case.get("acceptable_tools", []))
    tools_used_set = set(tools_used)

    tools_overlap = len(acceptable_tools.intersection(tools_used_set)) > 0
    tools_subset_ok = tools_used_set.issubset(acceptable_tools)

    return {
        "case_id": case["case_id"],
        "video_id": case["video_id"],
        "question": case["question"],
        "answer": answer,
        "tools_used": tools_used,
        "required_concepts_present": required_concepts_present,
        "focus_match": focus_match,
        "tools_overlap": tools_overlap,
        "tools_subset_ok": tools_subset_ok
    }


def main() -> None:
    manifest = load_json(MANIFEST_PATH)
    comment_cases_payload = load_json(COMMENT_CASES_PATH)
    comment_cases = comment_cases_payload["cases"]

    classified_index = build_classified_comment_index()

    comment_results = [
        compare_comment_case(case, classified_index)
        for case in comment_cases
    ]

    video_results = []
    for case in manifest["videos"]:
        analysis_payload = find_analysis_by_video_id(case["video_id"])
        video_results.append(compare_video_case(case, analysis_payload))

    agent_results = []
    for case in manifest["agent_cases"]:
        agent_payload = find_agent_by_video_id_and_question(case["video_id"], case["question"])
        agent_results.append(compare_agent_case(case, agent_payload))

    summary = {
        "comment_cases_total": len(comment_results),
        "video_cases_total": len(video_results),
        "agent_cases_total": len(agent_results),

        "comment_found_rate": safe_mean([1.0 if r["found_generated_comment"] else 0.0 for r in comment_results]),
        "comment_primary_match_rate": safe_mean([1.0 if r.get("primary_match") else 0.0 for r in comment_results if r.get("found_generated_comment")]),
        "comment_valence_match_rate": safe_mean([1.0 if r.get("valence_match") else 0.0 for r in comment_results if r.get("found_generated_comment")]),
        "comment_intensity_match_rate": safe_mean([1.0 if r.get("intensity_match") else 0.0 for r in comment_results if r.get("found_generated_comment")]),
        "comment_nuanced_match_rate": safe_mean([1.0 if r.get("nuanced_match") else 0.0 for r in comment_results if r.get("found_generated_comment")]),

        "video_dominant_match_rate": safe_mean([1.0 if r["dominant_match"] else 0.0 for r in video_results]),
        "video_secondary_match_rate": safe_mean([1.0 if r["secondary_match"] else 0.0 for r in video_results]),
        "video_negative_valence_ok_rate": safe_mean([1.0 if r["negative_valence_ok"] else 0.0 for r in video_results]),
        "video_language_match_rate": safe_mean([1.0 if r["language_match"] else 0.0 for r in video_results]),
        "video_warnings_match_rate": safe_mean([1.0 if r["warnings_match"] else 0.0 for r in video_results]),

        "agent_required_concepts_present_rate": safe_mean([1.0 if r["required_concepts_present"] else 0.0 for r in agent_results]),
        "agent_focus_match_rate": safe_mean([1.0 if r["focus_match"] else 0.0 for r in agent_results]),
        "agent_tools_overlap_rate": safe_mean([1.0 if r["tools_overlap"] else 0.0 for r in agent_results]),
        "agent_tools_subset_ok_rate": safe_mean([1.0 if r["tools_subset_ok"] else 0.0 for r in agent_results]),
    }

    output = {
        "summary": summary,
        "comment_results": comment_results,
        "video_results": video_results,
        "agent_results": agent_results
    }

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(
        json.dumps(output, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )

    print(f"Saved case comparison results to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()