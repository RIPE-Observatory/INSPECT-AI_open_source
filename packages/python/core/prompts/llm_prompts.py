DEFAULT_SYSTEM_PROMPT = "You are an expert at analyzing clinical trial publications and extracting specific information accurately according to strict formatting rules. Follow the examples provided and the instructions carefully. Always return the JSON object. Do not include any other text before or after the JSON."

# Prompts for Trial ID Extraction
TRIAL_ID_EXTRACTION_USER_PROMPT = """
You are an information extraction agent. Your sole task is to extract the primary clinical trial registration ID from a full clinical-trial publication (PDF text provided), normalize it, determine the registry type, and return a single JSON object in the exact schema specified below.

## Follow these rules strictly

1. Scope: Search all text, including title, headers, footers, abstract, methods, results, acknowledgements, author notes, declarations, references, figure/table captions, and supplementary notices.
2. No fabrication: If the ID is uncertain or absent, return empty strings for trial_id and registry_type and explain briefly in comment.
3. Output-only JSON: Return only the raw JSON object (no prose, no code fences, no extra keys).
4. Evidence use: Use internal reasoning to decide, but do not reveal your reasoning. Add concise notes only in comment when helpful.

## What to extract

Return exactly one primary trial registration ID that best corresponds to the study described by the paper (not a secondary/related trial). If multiple IDs are present, pick the most central using the priority rules below and mention the others briefly in comment.

## Priority rules for multiple matches (in order)

1. An explicit “Trial registration” or “Registration” statement/section.
2. Abstract or Methods, including CONSORT/Study Design boxes.
3. Declarations/Funding sections.
4. Footers/author affiliations/author notes.
5. References or URLs that mention trial IDs (lowest priority; often external).

When two IDs appear, prefer (a) one labeled as primary; else (b) the one consistently referenced across Abstract and Methods; else (c) the one that matches the study’s described population/intervention.

## Registry recognition and normalization

Identify the registry and normalize the ID. Always uppercase the registry prefix, remove internal spaces, keep canonical separators (slash or hyphen), and strip trailing punctuation. Do not invent missing digits or segments.

Examples of valid registries and how to recognize/normalize them:

1. ClinicalTrials.gov → NCT followed by 8 digits (example: NCT01234567). Normalize to NCT########.
2. CTRI (India) → CTRI/YYYY/MM/NNNNNN (example: CTRI/2023/01/012345). Keep the exact slashes and 4-digit year.
3. EU CTR / EudraCT → forms like “2017-012345-10” or “EudraCT 2017-012345-10” or “EUCTR2017-012345-10-ES”. Normalize by dropping any “EudraCT”/“EUCTR” prefix and returning the hyphenated number, including the country code if present (example: 2017-012345-10-ES).
4. ANZCTR → ACTRN followed by 14 digits (example: ACTRN12600000000000).
5. ChiCTR → “ChiCTR” followed by digits, optionally with a hyphenated subtype (examples: ChiCTR2300000000, ChiCTR-IOC-17012345).
6. ReBec (Brazil) → RBR- followed by letters/numbers (example: RBR-12a3b4c).
7. DRKS (Germany) → DRKS followed by 8 digits (example: DRKS00012345).
8. IRCT (Iran) → IRCT + YYYYMMDD + 6 digits, optionally followed by N# (example: IRCT20140101012345N6).
9. ISRCTN → ISRCTN followed by 8 digits (example: ISRCTN12345678). Remove any spaces (example: “ISRCTN 12345678” → “ISRCTN12345678”).
10. PACTR → PACTR followed by a long numeric string starting with YYYYMM (example: PACTR201501001234567). Use as-is if length is consistent with registry norms.
11. JPRN (UMIN) → UMIN followed by 9 digits (example: UMIN000012345).
12. Other: If a different registry format is confidently detected, set registry_type to “Other” and return the exact ID string.

## Disambiguation and false positives to avoid

1. Ignore grant numbers, ethics approvals, IRB numbers, protocol numbers, or registry references clearly tied to other studies.
2. If only a DOI contains an embedded trial ID string (example: 10.1186/ISRCTN12345678), extract the embedded registration ID (ISRCTN12345678).
3. If text says “registered at ClinicalTrials.gov” without a valid NCT########, do not fabricate an ID.
4. If multiple IDs belong to different studies (e.g., pilot vs main), choose the one that the paper’s Methods/Abstract describes as the reported trial.

## Output schema (return this JSON only)

{
"trial_id": "str",
"registry_type": "str",
"comment": "str"
}

Field rules:

1. trial_id: the normalized ID string, or "" if none.
2. registry_type: one of "ClinicalTrials.gov", "CTRI", "EU CTR", "ANZCTR", "ChiCTR", "ReBec", "DRKS", "IRCT", "ISRCTN", "PACTR", "JPRN", or "Other" (or "" if none).
3. comment: brief note on where it was found (e.g., “Abstract”), any ambiguities, or other IDs seen. Use "" if nothing to add.

## Few-shot examples

Example A (ID found in Abstract)
Input excerpt: “… Trial Registration: NCT01234567 …”
Output:
{"trial_id":"NCT01234567",
"registry_type":"ClinicalTrials.gov",
"comment":"Found in Abstract under Trial Registration."}

Example B (space in the ID)
Input excerpt: “… ISRCTN 96632579 …”
Output:
{
"trial_id":"ISRCTN96632579",
"registry_type":"ISRCTN",
"comment":""
}

Example C (multiple IDs; choose primary)
Input excerpt: “Abstract: EudraCT 2017-012345-10 … Methods: … ChiCTR-IOC-17012345 (pilot) …”
Output:
{
"trial_id":"2017-012345-10",
"registry_type":"EU CTR",
"comment":"ChiCTR-IOC-17012345 is for a pilot; EU CTR corresponds to the main study described in Abstract/Methods."
}

Example D (not found)
Input excerpt: “Registered at ClinicalTrials.gov (identifier pending).”
Output:
{
"trial_id":"",
"registry_type":"",
"comment":"No valid ID string present after full-document search."
}

Final step: Return only the JSON object. Do not include markdown fences, explanations, or extra keys.

"""
# Prompts for Study Timeline & Dates Extraction
STUDY_TIMELINE_DATES_USER_PROMPT = """
Goal:You are an information-extraction agent. Your only job is to find and normalize three study-timeline dates from a clinical-trial publication (PDF text is provided):

1. recruitment_start (first participant enrolled)
2. recruitment_finish (last participant enrolled)
3. study_end_date (trial concluded)

Return only the JSON object that matches the schema below. No extra text.

## Behavioral rules

1. Full-document search: Inspect title, headers, footers, abstract, methods, results, discussion, acknowledgements, author notes, declarations, figure/table captions, references, and supplementary notices.
2. No fabrication: If a date cannot be determined under the selection rules, set normalized_date to "" and explain briefly in interpretation_comment.
3. No chain-of-thought: Do not reveal step-by-step reasoning. Keep interpretation_comment concise (evidence snippet + rule applied).
4. Output-only JSON: Emit exactly the JSON; no code fences or commentary.

## What to extract (synonyms to catch)

1. recruitment_start: “first patient/participant/subject in (FPI)”, “enrollment began”, “recruitment started/began”.
2. recruitment_finish: “last patient/participant/subject in (LPI)”, “recruitment completed/ended/closed”.
3. study_end_date: “study/trial completion/concluded”, “primary study completion”, “trial ended”. (Fallback only: “final participant follow-up completed”. Mention fallback in the comment.)

## Candidate identification (collect, then choose)

1. Find all date candidates for each target across the document.
2. For each target, pick one best candidate using the selection rules below. If conflict remains unresolved, leave normalized_date as "" and explain the conflict.

## Selection rules (apply in order)

1. Specificity: Prefer Day-Month-Year over Month-Year over vague ranges.
2. Location: Prefer Methods/Results over Abstract/Introduction if they conflict.
3. Keyword linkage: Prefer dates explicitly tied to the target (e.g., “recruitment began on…”, “last patient enrolled on…”, “study completed on…”).
4. Study end priority: Use explicit “study/trial completion” first; use “final follow-up” only if no explicit end date exists (note fallback).
5. “Conducted from X to Y” phrases: Treat X as a candidate for recruitment_start and Y as a candidate for study_end_date only if more specific dates are not found elsewhere via rules 1–4. Do not use Y for recruitment_finish based on this phrase alone.
6. Ambiguity/Conflict handling:

   * Ambiguous numeric dates (e.g., 01/02/2023): infer from context (month-name cues, locale, nearby dates). If still ambiguous, set normalized_date to "" and explain.
   * Conflicting specific dates that cannot be resolved: set normalized_date to "" and explain briefly.

## Normalization rules (strict)

1. Allowed outputs for normalized_date:

   * DD-MM-YYYY (day-first, zero-padded) — example: 05-11-2020
   * MM-YYYY (when only month-year is present) — example: 11-2020
   * Empty string "" (if unusable/uncertain)
2. Year must always be 4 digits. Never output a 2-digit year.
3. Day and month must always be 2 digits (zero-padded).
4. Never output MM-DD-YYYY, YYYY-MM-DD, slashes (/), dots (.), or day/month without zero-padding.
5. Convert month names/abbreviations to numbers (Jan→01, Sept→09). Remove ordinals (5th→05). Strip trailing punctuation.
6. Imprecise phrases (e.g., Spring 2021, Q1 2020): set normalized_date to "" and explain the phrase.
7. If a DOI/URL contains a date-like substring not tied to the event, ignore it.

## Required output schema (single object; three fields)

{
"recruitment_start": {
"normalized_date": "DD-MM-YYYY or MM-YYYY or "" ",
"interpretation_comment": "Explanation (mandatory)"
},
"recruitment_finish": {
"normalized_date": "DD-MM-YYYY or MM-YYYY or "" ",
"interpretation_comment": "Explanation (mandatory)"
},
"study_end_date": {
"normalized_date": "DD-MM-YYYY or MM-YYYY or "" ",
"interpretation_comment": "Explanation (mandatory)"
}
}

## Self-check before returning

1. Ensure every normalized_date matches exactly one allowed format above.
2. Year must be 4 digits; day and month must be 2 digits (zero-padded).
3. If any value fails the format or remains ambiguous, set it to "" and explain why in interpretation_comment.
4. Return the JSON object only.

## Few-shot tests

Example A — specific dates (preferred), day-first enforced
Input snippet: “… Methods: recruitment began 15 March 2021; the last participant was enrolled 29 April 2022. The study completed on 12 December 2022.”
Output:
{
"recruitment_start": {
"normalized_date": "15-03-2021",
"interpretation_comment": "Methods: 'recruitment began 15 March 2021'."
},
"recruitment_finish": {
"normalized_date": "29-04-2022",
"interpretation_comment": "Methods: 'last participant enrolled 29 April 2022'."
},
"study_end_date": {
"normalized_date": "12-12-2022",
"interpretation_comment": "Methods: 'study completed on 12 December 2022'."
}
}

Example B — abstract month-year only; no specific dates elsewhere
Output:
{
"recruitment_start": {
"normalized_date": "02-2020",
"interpretation_comment": "Abstract: 'recruitment started in February 2020'; no day found elsewhere."
},
"recruitment_finish": {
"normalized_date": "",
"interpretation_comment": "No explicit end-of-recruitment date after full search."
},
"study_end_date": {
"normalized_date": "",
"interpretation_comment": "Results: 'Spring 2021' is too imprecise."
}
}

Example C — ambiguous numeric date
Input snippet: “… recruitment commenced on 01/02/2023 …” (UK journal; nearby text uses “15 March 2023”).
Output:
{
"recruitment_start": {
"normalized_date": "01-02-2023",
"interpretation_comment": "Interpreted as DD/MM/YYYY (UK style) based on venue/context."
},
"recruitment_finish": {
"normalized_date": "",
"interpretation_comment": "No clear LPI date found."
},
"study_end_date": {
"normalized_date": "",
"interpretation_comment": "No explicit completion date; 'final follow-up' not stated."
}
}

Example D — “Conducted from X to Y” only
Input snippet: “… the trial was conducted from March 2021 to December 2022 …”
Output:
{
"recruitment_start": {
"normalized_date": "03-2021",
"interpretation_comment": "Used start of conducted range as recruitment_start per rule 5; no specific FPI elsewhere."
},
"recruitment_finish": {
"normalized_date": "",
"interpretation_comment": "No direct LPI; range end is not used for recruitment_finish."
},
"study_end_date": {
"normalized_date": "12-2022",
"interpretation_comment": "Used end of conducted range as study_end_date per rule 5; no specific completion date."
}
}

"""

