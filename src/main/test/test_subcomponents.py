from datetime import date

import pytest

from backend.app.models import Phase


def seed_phases(SessionLocal):
    with SessionLocal() as session:
        session.add_all(
            [
                Phase(
                    phase_id="backlog",
                    phase_group="Backlog",
                    phase_name="Backlog",
                    sequence=1,
                ),
                Phase(
                    phase_id="requirements",
                    phase_group="Planning",
                    phase_name="Requirements",
                    sequence=2,
                ),
            ]
        )
        session.commit()


async def create_project_solution(client):
    project = (
        await client.post(
        "/api/projects/",
        json={
            "project_name": "Data Platform",
            "name_abbreviation": "DPLT",
            "description": "Modernize data stack",
            "sponsor": "CFO Office",
        },
        )
    ).json()
    solution = (
        await client.post(
            f"/api/projects/{project['project_id']}/solutions",
            json={"solution_name": "Access Controls", "version": "0.1.0", "owner": "Solution Owner"},
        )
    ).json()
    return project, solution


async def enable_phases(client, solution_id: str):
    resp = await client.post(
        f"/api/solutions/{solution_id}/phases",
        json={
            "phases": [
                {"phase_id": "backlog", "is_enabled": True},
                {"phase_id": "requirements", "is_enabled": True},
            ]
        },
    )
    assert resp.status_code == 200


@pytest.mark.anyio
async def test_create_and_list_subcomponents(client, db_sessionmaker):
    seed_phases(db_sessionmaker)
    _, solution = await create_project_solution(client)

    resp = await client.post(
        f"/api/solutions/{solution['solution_id']}/subcomponents",
        json={
            "subcomponent_name": "Define RBAC roles",
            "priority": 1,
            "due_date": date.today().isoformat(),
            "assignee": "Engineer A",
        },
    )
    assert resp.status_code == 201, resp.text
    data = resp.json()
    assert data["subcomponent_name"] == "Define RBAC roles"
    assert data["priority"] == 1
    assert data["assignee"] == "Engineer A"

    list_resp = await client.get(f"/api/solutions/{solution['solution_id']}/subcomponents")
    assert list_resp.status_code == 200
    items = list_resp.json()
    assert len(items) == 1
    assert items[0]["assignee"] == "Engineer A"


@pytest.mark.anyio
async def test_list_all_subcomponents_filter_by_assignee(client, db_sessionmaker):
    seed_phases(db_sessionmaker)
    _, solution = await create_project_solution(client)

    assert (
        (await client.post(
            f"/api/solutions/{solution['solution_id']}/subcomponents",
            json={"subcomponent_name": "Task A", "assignee": "Engineer A"},
        )).status_code
        == 201
    )
    assert (
        (await client.post(
            f"/api/solutions/{solution['solution_id']}/subcomponents",
            json={"subcomponent_name": "Task B", "assignee": "Engineer B"},
        )).status_code
        == 201
    )

    all_resp = await client.get("/api/subcomponents")
    assert all_resp.status_code == 200
    assert len(all_resp.json()) == 2

    filtered = await client.get("/api/subcomponents", params={"assignee": "Engineer A"})
    assert filtered.status_code == 200
    items = filtered.json()
    assert len(items) == 1
    assert items[0]["subcomponent_name"] == "Task A"


@pytest.mark.anyio
async def test_subcomponent_uniqueness_and_soft_delete(client, db_sessionmaker):
    seed_phases(db_sessionmaker)
    _, solution = await create_project_solution(client)

    payload = {"subcomponent_name": "Billing UI", "assignee": "Engineer A"}
    assert (await client.post(f"/api/solutions/{solution['solution_id']}/subcomponents", json=payload)).status_code == 201
    dup = await client.post(f"/api/solutions/{solution['solution_id']}/subcomponents", json=payload)
    assert dup.status_code == 400

    # soft delete
    created = (await client.get(f"/api/solutions/{solution['solution_id']}/subcomponents")).json()[0]
    delete_resp = await client.delete(f"/api/subcomponents/{created['subcomponent_id']}")
    assert delete_resp.status_code == 204

    get_resp = await client.get(f"/api/subcomponents/{created['subcomponent_id']}")
    assert get_resp.status_code == 404

    list_resp = await client.get(f"/api/solutions/{solution['solution_id']}/subcomponents")
    assert list_resp.status_code == 200
    assert list_resp.json() == []
