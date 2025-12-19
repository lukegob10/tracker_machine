from __future__ import annotations

import csv
from io import StringIO

import pytest

from backend.app.models import Phase


def seed_minimal_phases(db_sessionmaker):
    with db_sessionmaker() as session:
        session.add_all(
            [
                Phase(phase_id="backlog", phase_group="Backlog", phase_name="Backlog", sequence=1),
                Phase(phase_id="requirements", phase_group="Planning", phase_name="Requirements", sequence=2),
            ]
        )
        session.commit()


@pytest.mark.anyio
async def test_solutions_import_updates_creates_and_exports(client, db_sessionmaker):
    seed_minimal_phases(db_sessionmaker)

    project = (
        await client.post(
            "/api/projects/",
            json={"project_name": "Data Platform", "name_abbreviation": "DPLT", "sponsor": "CFO Office"},
        )
    ).json()

    sol_phase = (
        await client.post(
            f"/api/projects/{project['project_id']}/solutions",
            json={"solution_name": "Update Phase", "version": "0.1.0", "status": "active", "owner": "Owner"},
        )
    ).json()
    sol_complete = (
        await client.post(
            f"/api/projects/{project['project_id']}/solutions",
            json={"solution_name": "Mark Complete", "version": "0.1.0", "status": "active", "owner": "Owner"},
        )
    ).json()

    fieldnames = [
        "project_name",
        "solution_name",
        "version",
        "status",
        "rag_status",
        "rag_source",
        "rag_reason",
        "priority",
        "due_date",
        "current_phase",
        "description",
        "success_criteria",
        "owner",
        "assignee",
        "approver",
        "key_stakeholder",
        "blockers",
        "risks",
    ]
    buf = StringIO()
    writer = csv.DictWriter(buf, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerow(
        {
            "project_name": "Data Platform",
            "solution_name": "Update Phase",
            "version": "0.1.0",
            "status": "active",
            "priority": "2",
            "current_phase": "requirements",
            "description": "Desc",
            "owner": "Owner",
            "assignee": "Assignee",
        }
    )
    writer.writerow(
        {
            "project_name": "Data Platform",
            "solution_name": "Mark Complete",
            "version": "0.1.0",
            "status": "complete",
            "priority": "3",
            "current_phase": "",
            "owner": "Owner",
        }
    )
    writer.writerow(
        {
            "project_name": "Data Platform",
            "solution_name": "Manual RAG",
            "version": "0.1.0",
            "status": "active",
            "rag_status": "green",
            "rag_source": "",
            "rag_reason": "Escalation approved",
            "priority": "3",
            "current_phase": "requirements",
            "owner": "Owner",
        }
    )
    writer.writerow(
        {
            "project_name": "Auto Project",
            "solution_name": "Auto Solution",
            "version": "0.1.0",
            "status": "not_started",
            "priority": "3",
            "owner": "Auto Owner",
        }
    )
    writer.writerow(
        {
            "project_name": "Data Platform",
            "solution_name": "Bad Rag Source",
            "version": "0.1.0",
            "status": "active",
            "rag_source": "invalid",
            "priority": "3",
            "owner": "Owner",
        }
    )
    writer.writerow(
        {
            "project_name": "Data Platform",
            "solution_name": "Bad Phase",
            "version": "0.1.0",
            "status": "active",
            "priority": "3",
            "current_phase": "does_not_exist",
            "owner": "Owner",
        }
    )
    writer.writerow(
        {
            "project_name": "Data Platform",
            "solution_name": "Missing Owner",
            "version": "0.1.0",
            "status": "active",
            "priority": "3",
            "owner": "",
        }
    )

    resp = await client.post(
        "/api/solutions/import",
        content=buf.getvalue().encode("utf-8"),
        headers={"Content-Type": "text/csv"},
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["updated"] == 2
    assert data["created"] == 2
    assert data["projects_created"] == 1
    assert data["total_rows"] == 7
    assert len(data["errors"]) == 3

    updated_phase = (await client.get(f"/api/solutions/{sol_phase['solution_id']}")).json()
    assert updated_phase["current_phase"] == "requirements"
    assert updated_phase["priority"] == 2

    updated_complete = (await client.get(f"/api/solutions/{sol_complete['solution_id']}")).json()
    assert updated_complete["status"] == "complete"
    assert updated_complete["completed_at"] is not None
    assert updated_complete["current_phase"] == "requirements"

    exported = await client.get("/api/solutions/export")
    assert exported.status_code == 200
    assert "text/csv" in exported.headers.get("content-type", "")
    rows = list(csv.DictReader(StringIO(exported.text)))
    assert any(r["solution_name"] == "Manual RAG" for r in rows)
    assert any(r["project_name"] == "Auto Project" for r in rows)

    list_complete = await client.get("/api/solutions", params={"status": "complete"})
    assert list_complete.status_code == 200
    assert [s["solution_name"] for s in list_complete.json()] == ["Mark Complete"]


@pytest.mark.anyio
async def test_create_solution_rejects_unknown_project_and_current_phase(client, db_sessionmaker):
    seed_minimal_phases(db_sessionmaker)

    missing_project = await client.get("/api/projects/does-not-exist/solutions")
    assert missing_project.status_code == 404
    assert missing_project.json()["detail"] == "Project not found"

    project = (
        await client.post(
            "/api/projects/",
            json={"project_name": "P", "name_abbreviation": "PROJ", "sponsor": "S"},
        )
    ).json()
    bad_phase = await client.post(
        f"/api/projects/{project['project_id']}/solutions",
        json={
            "solution_name": "S",
            "version": "0.1.0",
            "status": "active",
            "owner": "Owner",
            "current_phase": "does_not_exist",
        },
    )
    assert bad_phase.status_code == 400
    assert "current_phase" in bad_phase.json()["detail"]


@pytest.mark.anyio
async def test_create_solution_requires_rag_fields_for_manual_source(client):
    project = (
        await client.post(
            "/api/projects/",
            json={"project_name": "RAG Project", "name_abbreviation": "RAGP", "sponsor": "S"},
        )
    ).json()

    missing_status = await client.post(
        f"/api/projects/{project['project_id']}/solutions",
        json={
            "solution_name": "Manual Missing Status",
            "version": "0.1.0",
            "status": "active",
            "rag_source": "manual",
            "rag_reason": "Because",
            "owner": "Owner",
        },
    )
    assert missing_status.status_code == 400
    assert missing_status.json()["detail"] == "rag_status is required when rag_source is manual"

    missing_reason = await client.post(
        f"/api/projects/{project['project_id']}/solutions",
        json={
            "solution_name": "Manual Missing Reason",
            "version": "0.1.0",
            "status": "active",
            "rag_source": "manual",
            "rag_status": "green",
            "owner": "Owner",
        },
    )
    assert missing_reason.status_code == 400
    assert missing_reason.json()["detail"] == "rag_reason is required when rag_source is manual"


@pytest.mark.anyio
async def test_update_solution_sets_manual_when_rag_fields_provided_without_source(client):
    project = (
        await client.post(
            "/api/projects/",
            json={"project_name": "P", "name_abbreviation": "PROJ", "sponsor": "S"},
        )
    ).json()
    created = (
        await client.post(
            f"/api/projects/{project['project_id']}/solutions",
            json={"solution_name": "S", "version": "0.1.0", "owner": "Owner"},
        )
    ).json()

    resp = await client.patch(
        f"/api/solutions/{created['solution_id']}",
        json={"rag_status": "green", "rag_reason": "Approved"},
    )
    assert resp.status_code == 200, resp.text
    updated = resp.json()
    assert updated["rag_source"] == "manual"
    assert updated["rag_status"] == "green"
    assert updated["rag_reason"] == "Approved"


@pytest.mark.anyio
async def test_update_solution_rejects_manual_source_without_rag_status(client):
    project = (
        await client.post(
            "/api/projects/",
            json={"project_name": "P", "name_abbreviation": "PROJ", "sponsor": "S"},
        )
    ).json()
    created = (
        await client.post(
            f"/api/projects/{project['project_id']}/solutions",
            json={"solution_name": "S", "version": "0.1.0", "owner": "Owner"},
        )
    ).json()

    resp = await client.patch(
        f"/api/solutions/{created['solution_id']}",
        json={"rag_source": "manual", "rag_reason": "Because"},
    )
    assert resp.status_code == 400
    assert resp.json()["detail"] == "rag_status is required when rag_source is manual"


@pytest.mark.anyio
async def test_update_solution_rejects_name_version_conflict(client):
    project = (
        await client.post(
            "/api/projects/",
            json={"project_name": "P", "name_abbreviation": "PROJ", "sponsor": "S"},
        )
    ).json()
    s1 = (
        await client.post(
            f"/api/projects/{project['project_id']}/solutions",
            json={"solution_name": "A", "version": "0.1.0", "owner": "Owner"},
        )
    ).json()
    s2 = (
        await client.post(
            f"/api/projects/{project['project_id']}/solutions",
            json={"solution_name": "B", "version": "0.2.0", "owner": "Owner"},
        )
    ).json()

    resp = await client.patch(
        f"/api/solutions/{s2['solution_id']}",
        json={"solution_name": s1["solution_name"], "version": s1["version"]},
    )
    assert resp.status_code == 400
    assert resp.json()["detail"] == "Solution name and version already exist for this project"


@pytest.mark.anyio
async def test_solution_auto_rag_marks_abandoned_as_red(client):
    project = (
        await client.post(
            "/api/projects/",
            json={"project_name": "P", "name_abbreviation": "PROJ", "sponsor": "S"},
        )
    ).json()
    created = (
        await client.post(
            f"/api/projects/{project['project_id']}/solutions",
            json={"solution_name": "Abandoned", "version": "0.1.0", "status": "abandoned", "owner": "Owner"},
        )
    ).json()
    assert created["rag_source"] == "auto"
    assert created["rag_status"] == "red"
