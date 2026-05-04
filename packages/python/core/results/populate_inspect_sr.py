"""
Auto-populate INSPECT-SR data structure from check results.

This module creates the inspect_sr data structure during job processing,
extracting automated_judgement values from completed checks.
"""

from datetime import datetime, timezone
from typing import Any, Dict, Optional

from core.schemas.inspect_sr import AnswerRecord, compute_progress_from_records


def populate_inspect_sr_from_checks(results: Dict[str, Any]) -> Dict[str, Any]:
    """
    Populate INSPECT-SR data structure from check results.

    Extracts automated_judgement values for:
    - Q1.1: Retraction detection
    - Q1.2: EOC/PubPeer notices
    - Q1.3: Author retraction history
    - Q2.2: Prospective registration timing
    - OVERALL: Auto-set to "serious-concerns" if Q1.1 = yes

    Args:
        results: Full job results dict with 'checks' key

    Returns:
        inspect_sr dict with version, updated_at, progress, and data
    """
    data_records = []
    now_iso = datetime.now(timezone.utc).isoformat()

    # Helper to get nested check data
    def get_check_payload(check_name: str) -> Optional[Dict]:
        if not isinstance(results, dict):
            return None
        return results.get("checks", {}).get(check_name, {}).get("payload")

    # Q1.1 Retraction: yes/no/unclear
    try:
        retraction = get_check_payload("retraction_detection")
        if retraction:
            main = retraction.get("main_article_result")
            if main and isinstance(main, dict):
                found = main.get("found")
                q11_answer = "yes" if found is True else "no" if found is False else "unclear"
                data_records.append({
                    "question_id": "Q1.1",
                    "label": "Does the study have an associated retraction?",
                    "automated_judgement": q11_answer,
                    "reviewed_judgement": None,
                    "comment": "",
                })
    except Exception:
        pass

    # Q1.2 Post-publication notice (EOC + PubPeer): yes/no/unclear
    try:
        eoc = get_check_payload("eoc_correction_detection")
        pubpeer = get_check_payload("pubpeer_signal_analysis")

        # Check EOC notices
        eoc_notices = []
        if eoc:
            eoc_notices = eoc.get("main_article_result", {}).get("notices", [])

        # Check PubPeer comments
        pubpeer_comments = []
        if pubpeer:
            pubpeer_comments = pubpeer.get("main_paper_result", {}).get("scraped_comments", {}).get("comments", [])

        # If EITHER has notices/comments, answer is "yes"
        if eoc or pubpeer:
            q12_answer = "yes" if (len(eoc_notices) > 0 or len(pubpeer_comments) > 0) else "no"
            data_records.append({
                "question_id": "Q1.2",
                "label": "Does the study have an associated expression of concern or other relevant post publication notice?",
                "automated_judgement": q12_answer,
                "reviewed_judgement": None,
                "comment": "",
            })
    except Exception:
        pass

    # Q1.3 Author retraction history: yes/no/unclear
    try:
        author_history = get_check_payload("author_retraction_history")
        if author_history:
            summary = author_history.get("summary", {})
            total_retractions = summary.get("total_retractions_found", 0)
            q13_answer = "yes" if total_retractions > 0 else "no"
            data_records.append({
                "question_id": "Q1.3",
                "label": "Is there evidence of concerning patterns in the publication history of authors?",
                "automated_judgement": q13_answer,
                "reviewed_judgement": None,
                "comment": "",
            })
    except Exception:
        pass

    # Q2.2 Prospective registration timing: false -> yes (concern), true -> no
    try:
        reg = get_check_payload("prospective_registration_analysis")
        if reg and isinstance(reg, dict):
            is_pro = reg.get("is_prospective")
            q22_answer = "yes" if is_pro is False else "no" if is_pro is True else "unclear"
            data_records.append({
                "question_id": "Q2.2",
                "label": "Are there concerns relating to the timing or absence of study registration?",
                "automated_judgement": q22_answer,
                "reviewed_judgement": None,
                "comment": "",
            })
    except Exception:
        pass

    # Validate all records
    records_valid = []
    for r in data_records:
        try:
            records_valid.append(AnswerRecord.model_validate(r).model_dump())
        except Exception:
            continue

    # AUTO-POPULATE OVERALL judgement if Q1.1 automated_judgement = yes (retraction detected)
    q11_record = next((r for r in records_valid if r["question_id"] == "Q1.1"), None)
    if q11_record and q11_record.get("automated_judgement") == "yes":
        # Retraction detected - add OVERALL with serious-concerns
        overall_record = {
            "question_id": "OVERALL",
            "label": "Overall Study Judgement",
            "automated_judgement": "serious-concerns",
            "reviewed_judgement": None,
            "comment": "",
        }
        try:
            records_valid.append(AnswerRecord.model_validate(overall_record).model_dump())
        except Exception:
            pass

    # Convert to AnswerRecord objects for progress computation
    answer_records = []
    for r in records_valid:
        try:
            answer_records.append(AnswerRecord.model_validate(r))
        except Exception:
            continue

    # Build container
    container = {
        "version": 1,
        "updated_at": now_iso,
        "progress": compute_progress_from_records(answer_records),
        "data": records_valid,
    }

    return container
