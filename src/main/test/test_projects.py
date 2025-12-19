import pytest


@pytest.mark.anyio
async def test_create_and_list_projects(client):
    resp = await client.post(
        "/api/projects/",
        json={
            "project_name": "Data Platform",
            "name_abbreviation": "DPLT",
            "description": "Modernize data stack",
            "success_criteria": "Reduce run time by 30% and decommission legacy tooling",
            "sponsor": "CFO Office",
        },
    )
    assert resp.status_code == 201, resp.text
    data = resp.json()
    assert data["project_name"] == "Data Platform"
    assert data["name_abbreviation"] == "DPLT"
    assert data["status"] == "not_started"
    assert data["success_criteria"] == "Reduce run time by 30% and decommission legacy tooling"

    list_resp = await client.get("/api/projects/")
    assert list_resp.status_code == 200
    projects = list_resp.json()
    assert len(projects) == 1
    assert projects[0]["project_name"] == "Data Platform"


@pytest.mark.anyio
async def test_project_name_uniqueness(client):
    payload = {
        "project_name": "Access Controls",
        "name_abbreviation": "ACCS",
        "status": "active",
        "sponsor": "CFO Office",
    }
    assert (await client.post("/api/projects/", json=payload)).status_code == 201
    dup_resp = await client.post("/api/projects/", json=payload)
    assert dup_resp.status_code == 400
    assert dup_resp.json()["detail"] == "Project name already exists"


@pytest.mark.anyio
async def test_update_project_status_and_description(client):
    create = (
        await client.post(
        "/api/projects/",
        json={
            "project_name": "Portal",
            "name_abbreviation": "PORT",
            "status": "active",
            "sponsor": "CFO Office",
        },
        )
    ).json()
    project_id = create["project_id"]

    update_resp = await client.patch(
        f"/api/projects/{project_id}",
        json={
            "status": "on_hold",
            "description": "Waiting on vendor",
            "success_criteria": "Pilot with 3 teams and hit >90% satisfaction",
        },
    )
    assert update_resp.status_code == 200
    updated = update_resp.json()
    assert updated["status"] == "on_hold"
    assert updated["description"] == "Waiting on vendor"
    assert updated["success_criteria"] == "Pilot with 3 teams and hit >90% satisfaction"


@pytest.mark.anyio
async def test_delete_project_soft_deletes(client):
    create = (
        await client.post(
        "/api/projects/",
        json={
            "project_name": "Billing",
            "name_abbreviation": "BILL",
            "sponsor": "CFO Office",
        },
        )
    ).json()
    project_id = create["project_id"]

    delete_resp = await client.delete(f"/api/projects/{project_id}")
    assert delete_resp.status_code == 204

    get_resp = await client.get(f"/api/projects/{project_id}")
    assert get_resp.status_code == 404

    list_resp = await client.get("/api/projects/")
    assert list_resp.status_code == 200
    assert list_resp.json() == []
