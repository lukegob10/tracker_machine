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
