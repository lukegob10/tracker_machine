from datetime import date, timedelta

import pytest


async def create_project(client):
    resp = await client.post(
        "/api/projects/",
        json={
            "project_name": "Data Platform",
            "name_abbreviation": "DPLT",
            "description": "Modernize data stack",
            "sponsor": "CFO Office",
        },
    )
    assert resp.status_code == 201
    return resp.json()


@pytest.mark.anyio
async def test_create_and_list_solutions(client):
    project = await create_project(client)

    resp = await client.post(
        f"/api/projects/{project['project_id']}/solutions",
        json={
            "solution_name": "Access Controls",
            "version": "0.1.0",
            "status": "active",
            "description": "RBAC and audit",
            "success_criteria": "Enforce RBAC for top 10 apps and pass audit",
            "owner": "Solution Owner",
        },
    )
    assert resp.status_code == 201, resp.text
    data = resp.json()
    assert data["solution_name"] == "Access Controls"
    assert data["version"] == "0.1.0"
    assert data["priority"] == 3
    assert data["success_criteria"] == "Enforce RBAC for top 10 apps and pass audit"

    list_resp = await client.get(f"/api/projects/{project['project_id']}/solutions")
    assert list_resp.status_code == 200
    items = list_resp.json()
    assert len(items) == 1
    assert items[0]["solution_name"] == "Access Controls"


@pytest.mark.anyio
async def test_solution_uniqueness_per_project_version(client):
    project = await create_project(client)
    payload = {
        "solution_name": "Access Controls",
        "version": "0.1.0",
        "status": "active",
        "owner": "Solution Owner",
    }
    assert (
        (await client.post(f"/api/projects/{project['project_id']}/solutions", json=payload)).status_code
        == 201
    )
    dup_resp = await client.post(f"/api/projects/{project['project_id']}/solutions", json=payload)
    assert dup_resp.status_code == 400
    assert "already exist" in dup_resp.json()["detail"]

    # Different version should be allowed
    payload["version"] = "0.2.0"
    assert (
        (await client.post(f"/api/projects/{project['project_id']}/solutions", json=payload)).status_code
        == 201
    )


@pytest.mark.anyio
async def test_update_solution_status_and_description(client):
    project = await create_project(client)
    created = (
        await client.post(
            f"/api/projects/{project['project_id']}/solutions",
            json={"solution_name": "Portal", "version": "1.0.0", "owner": "Solution Owner"},
        )
    ).json()
    solution_id = created["solution_id"]

    update_resp = await client.patch(
        f"/api/solutions/{solution_id}",
        json={
            "status": "complete",
            "description": "Shipped",
            "success_criteria": "100% traffic migrated; no Sev1 incidents for 30 days",
        },
    )
    assert update_resp.status_code == 200
    updated = update_resp.json()
    assert updated["status"] == "complete"
    assert updated["description"] == "Shipped"
    assert updated["success_criteria"] == "100% traffic migrated; no Sev1 incidents for 30 days"
    assert updated["completed_at"] is not None


@pytest.mark.anyio
async def test_delete_solution_soft_deletes(client):
    project = await create_project(client)
    created = (
        await client.post(
            f"/api/projects/{project['project_id']}/solutions",
            json={"solution_name": "Billing", "version": "0.1.0", "owner": "Solution Owner"},
        )
    ).json()
    solution_id = created["solution_id"]

    delete_resp = await client.delete(f"/api/solutions/{solution_id}")
    assert delete_resp.status_code == 204

    get_resp = await client.get(f"/api/solutions/{solution_id}")
    assert get_resp.status_code == 404

    list_resp = await client.get(f"/api/projects/{project['project_id']}/solutions")
    assert list_resp.status_code == 200
    assert list_resp.json() == []


@pytest.mark.anyio
async def test_solution_rag_auto_rules(client):
    project = await create_project(client)
    created = (
        await client.post(
            f"/api/projects/{project['project_id']}/solutions",
            json={
                "solution_name": "RAG Demo",
                "version": "0.1.0",
                "status": "active",
                "owner": "Solution Owner",
            },
        )
    ).json()

    assert created["rag_source"] == "auto"
    assert created["rag_status"] == "amber"
    assert created["rag_reason"] is None

    past = (date.today() - timedelta(days=1)).isoformat()
    updated = (await client.patch(f"/api/solutions/{created['solution_id']}", json={"due_date": past})).json()
    assert updated["rag_source"] == "auto"
    assert updated["rag_status"] == "red"
    assert updated["rag_reason"] is None

    completed = (await client.patch(f"/api/solutions/{created['solution_id']}", json={"status": "complete"})).json()
    assert completed["rag_source"] == "auto"
    assert completed["rag_status"] == "green"


@pytest.mark.anyio
async def test_solution_rag_manual_override_and_reset(client):
    project = await create_project(client)
    past = (date.today() - timedelta(days=1)).isoformat()
    created_resp = await client.post(
        f"/api/projects/{project['project_id']}/solutions",
        json={
            "solution_name": "Manual RAG",
            "version": "0.1.0",
            "status": "active",
            "due_date": past,
            "owner": "Solution Owner",
        },
    )
    assert created_resp.status_code == 201, created_resp.text
    created = created_resp.json()
    assert created["rag_source"] == "auto"
    assert created["rag_status"] == "red"

    bad_resp = await client.patch(
        f"/api/solutions/{created['solution_id']}",
        json={"rag_source": "manual", "rag_status": "green"},
    )
    assert bad_resp.status_code == 400
    assert "rag_reason" in bad_resp.json()["detail"]

    manual_resp = await client.patch(
        f"/api/solutions/{created['solution_id']}",
        json={"rag_source": "manual", "rag_status": "green", "rag_reason": "Escalation approved"},
    )
    assert manual_resp.status_code == 200, manual_resp.text
    manual = manual_resp.json()
    assert manual["rag_source"] == "manual"
    assert manual["rag_status"] == "green"
    assert manual["rag_reason"] == "Escalation approved"

    # Manual override persists until switched back to auto.
    still_manual = (
        await client.patch(
            f"/api/solutions/{created['solution_id']}",
            json={"due_date": (date.today() - timedelta(days=10)).isoformat()},
        )
    ).json()
    assert still_manual["rag_source"] == "manual"
    assert still_manual["rag_status"] == "green"
    assert still_manual["rag_reason"] == "Escalation approved"

    reset_resp = await client.patch(
        f"/api/solutions/{created['solution_id']}",
        json={"rag_source": "auto"},
    )
    assert reset_resp.status_code == 200, reset_resp.text
    reset = reset_resp.json()
    assert reset["rag_source"] == "auto"
    assert reset["rag_status"] == "red"
    assert reset["rag_reason"] is None
