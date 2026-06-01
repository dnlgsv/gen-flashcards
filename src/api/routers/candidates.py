"""Candidate extraction endpoints."""

from __future__ import annotations

import json

from fastapi import APIRouter

from src.exceptions import ModelInferenceError
from src.llm_catalog import extract_local_model_path, normalize_model_name
from src.model_manager import model_manager
from src.nlp_utils import extract_flashcard_candidates

from ..schemas import Candidate, CandidateExtractRequest, CandidateExtractResponse

router = APIRouter(prefix="/candidates", tags=["Candidates"])


def _extract_json_array(text: str) -> list[object]:
    start = text.find("[")
    end = text.rfind("]")
    if start == -1 or end == -1 or end <= start:
        raise ValueError("model response did not contain a JSON array")
    parsed = json.loads(text[start : end + 1])
    if not isinstance(parsed, list):
        raise ValueError("model response was not a JSON array")
    return parsed


def _rerank_candidates(
    candidates: list[dict[str, object]],
    *,
    model_name: str,
    language: str,
    learner_level: str,
    target_count: int,
) -> list[dict[str, object]]:
    """Use an LLM to reorder a local shortlist without inventing candidates."""
    if not candidates:
        return candidates

    try:
        from litellm import completion

        normalized_model = normalize_model_name(model_name)
        model_manager._ensure_local_provider_registered(model_manager)  # noqa: SLF001
        model_manager._validate_provider_credentials(normalized_model)  # noqa: SLF001

        compact_candidates = [
            {
                "expression": item["expression"],
                "kind": item["kind"],
                "score": item["score"],
                "frequency": item["frequency"],
                "contexts": list(item["contexts"])[:1]
                if isinstance(item["contexts"], list)
                else [],
            }
            for item in candidates
        ]
        prompt = (
            "Rank vocabulary flashcard candidates for a language learner. "
            "Prefer useful words and phrases that are important in the source text. "
            "Do not add new candidates. Return only a JSON array of expressions, "
            "best first."
        )
        user_message = (
            f"Language: {language}\n"
            f"Learner level: {learner_level}\n"
            f"Target count: {target_count}\n"
            f"Candidates JSON:\n{json.dumps(compact_candidates, ensure_ascii=False)}"
        )
        if "qwen3" in extract_local_model_path(normalized_model).lower():
            user_message += "\n/no_think"
        response = completion(
            model=normalized_model,
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": user_message},
            ],
            temperature=0.1,
            max_tokens=1200,
        )
        order = _extract_json_array(response.choices[0].message.content or "")
    except Exception as exc:
        raise ModelInferenceError(f"Candidate rerank failed: {exc}") from exc

    by_expression = {
        str(item["expression"]).casefold(): item
        for item in candidates
        if str(item.get("expression", "")).strip()
    }
    reranked: list[dict[str, object]] = []
    seen: set[str] = set()
    for expression in order:
        key = str(expression).strip().casefold()
        if key in by_expression and key not in seen:
            reranked.append(by_expression[key])
            seen.add(key)
    for item in candidates:
        key = str(item["expression"]).casefold()
        if key not in seen:
            reranked.append(item)
    return reranked[:target_count]


@router.post("/extract", response_model=CandidateExtractResponse)
async def extract_candidates(body: CandidateExtractRequest) -> CandidateExtractResponse:
    """Extract ranked flashcard candidates from pasted or uploaded text."""
    candidates = extract_flashcard_candidates(
        body.text,
        language=body.language,
        learner_level=body.learner_level,
        target_count=body.target_count,
        include_phrases=body.include_phrases,
    )
    if body.use_model_rerank and body.model_name:
        candidates = _rerank_candidates(
            candidates,
            model_name=body.model_name,
            language=body.language,
            learner_level=body.learner_level,
            target_count=body.target_count,
        )
    return CandidateExtractResponse(
        candidates=[Candidate.model_validate(candidate) for candidate in candidates]
    )
