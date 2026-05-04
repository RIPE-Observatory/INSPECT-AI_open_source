import pytest
from httpx import AsyncClient
from httpx import ASGITransport

from main import app
from core.db.session import get_db_session
from core.db.crud import job as crud_job
from core.schemas.enums import JobSourceEnum
from core.db.crud import reviewer as reviewer_crud
from api.dependencies.reviewer import require_complete_reviewer
from core.schemas.inspect_sr import QUESTION_TYPES, BETA_QUESTION_IDS, get_active_question_types


def build_beta_payload():
    """Build payload with 5 beta questions."""
    records = []
    for qid in BETA_QUESTION_IDS:
        qtype = QUESTION_TYPES[qid]
        if qtype == 'check':
            answer = 'yes'
        else:
            answer = 'no-concerns'
        records.append({
            'question_id': qid,
            'label': qid,
            'reviewed_judgement': answer,
            'automated_judgement': None,
            'comment': ''
        })
    return records


@pytest.mark.asyncio
async def test_inspect_sr_put_requires_beta_unique_set(test_db):
    """Test that PUT requires the beta question set (5 questions) by default."""
    async def override_db():
        yield test_db

    app.dependency_overrides[get_db_session] = override_db

    reviewer = await reviewer_crud.ensure_reviewer(test_db, "test-user")
    reviewer.onboarding_complete = True
    await test_db.commit()

    async def override_reviewer():
        return reviewer

    app.dependency_overrides[require_complete_reviewer] = override_reviewer

    # Create a job
    job = await crud_job.create_job(
        db=test_db,
        identifier="test.pdf",
        source=JobSourceEnum.USER,
        reviewer_id=reviewer.id,
        external_id=None,
        file_path=None,
    )
    await test_db.commit()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Valid beta payload should succeed
        beta = build_beta_payload()
        r = await client.put(f"/api/v1/jobs/{job.id}/inspect-sr", json={'data': beta, 'version': 0})
        assert r.status_code == 200, f"Expected 200 but got {r.status_code}: {r.text}"

        # Missing id case: drop one question from beta set
        missing = beta[:-1]  # Drop OVERALL
        r = await client.put(f"/api/v1/jobs/{job.id}/inspect-sr", json={'data': missing, 'version': 1})
        assert r.status_code == 400
        body = r.json()
        assert body.get('detail', {}).get('error') == 'invalid_question_set'
        assert 'OVERALL' in body['detail'].get('missing', [])

        # Duplicate id case
        dup = build_beta_payload()
        dup.append(dup[0])
        r = await client.put(f"/api/v1/jobs/{job.id}/inspect-sr", json={'data': dup, 'version': 1})
        assert r.status_code == 400
        assert 'Duplicate question_id' in r.text

        # Unknown id case
        bad = build_beta_payload()
        bad[0]['question_id'] = 'Q0.0'
        r = await client.put(f"/api/v1/jobs/{job.id}/inspect-sr", json={'data': bad, 'version': 1})
        assert r.status_code == 400
        assert 'Unknown question_id' in r.text

    app.dependency_overrides.pop(get_db_session, None)
    app.dependency_overrides.pop(require_complete_reviewer, None)


@pytest.mark.asyncio
async def test_inspect_sr_put_get_progress_beta(test_db):
    """Test progress calculation for beta profile (4 checks + OVERALL)."""
    async def override_db():
        yield test_db

    app.dependency_overrides[get_db_session] = override_db

    reviewer = await reviewer_crud.ensure_reviewer(test_db, "test-user-2")
    reviewer.onboarding_complete = True
    await test_db.commit()

    async def override_reviewer():
        return reviewer

    app.dependency_overrides[require_complete_reviewer] = override_reviewer

    # Create a job
    job = await crud_job.create_job(
        db=test_db,
        identifier="test2.pdf",
        source=JobSourceEnum.USER,
        reviewer_id=reviewer.id,
        external_id=None,
        file_path=None,
    )
    await test_db.commit()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        beta = build_beta_payload()
        # Initial save with all beta questions answered
        r = await client.put(f"/api/v1/jobs/{job.id}/inspect-sr", json={'data': beta, 'version': 0})
        assert r.status_code == 200
        v1 = r.json()['version']

        # Check progress: 4 checks completed out of 4 (OVERALL excluded from progress count)
        r = await client.get(f"/api/v1/jobs/{job.id}/inspect-sr/progress")
        assert r.status_code == 200
        pj = r.json()
        assert pj['completed'] == 4, f"Expected 4, got {pj['completed']}"
        assert pj['total'] == 4, f"Expected total=4, got {pj['total']}"
        assert pj['percent'] == 100

        # Change only a comment on first record; save again
        beta[0]['comment'] = 'note'
        r = await client.put(f"/api/v1/jobs/{job.id}/inspect-sr", json={'data': beta, 'version': v1})
        assert r.status_code == 200
        v2 = r.json()['version']
        assert v2 == v1 + 1

        # GET and verify the first record
        r = await client.get(f"/api/v1/jobs/{job.id}/inspect-sr")
        assert r.status_code == 200
        data = r.json()['data']
        rec0 = next((x for x in data if x['question_id'] == beta[0]['question_id']), None)
        assert rec0 is not None
        assert rec0['comment'] == 'note'
        # Ensure answer unchanged and progress still 100
        assert rec0['reviewed_judgement'] == beta[0]['reviewed_judgement']
        r = await client.get(f"/api/v1/jobs/{job.id}/inspect-sr/progress")
        assert r.json()['percent'] == 100

    app.dependency_overrides.pop(get_db_session, None)
    app.dependency_overrides.pop(require_complete_reviewer, None)
