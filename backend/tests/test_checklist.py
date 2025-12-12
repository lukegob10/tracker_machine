import os
import sys

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from backend.app.deps import get_db
from backend.app.main import app
from backend.app.models import Base, Phase


def setup_test_app():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    def get_test_db():
        with TestingSessionLocal() as session:
            yield session

    app.dependency_overrides[get_db] = get_test_db
    return TestClient(app), TestingSessionLocal


def seed_phases(SessionLocal):
    with SessionLocal() as session:
        session.add_all(
            [
                Phase(phase_id="backlog", phase_group="Backlog", phase_name="Backlog", sequence=1),
                Phase(
                    phase_id="requirements",
                    phase_group="Planning",
                    phase_name="Requirements",
                    sequence=2,
                ),
            ]
        )
        session.commit()


def bootstrap(client: TestClient):
    project = client.post(
        "/projects/",
        json={"project_name": "Data Platform", "name_abbreviation": "DPLT"},
    ).json()
    solution = client.post(
        f"/projects/{project['project_id']}/solutions",
        json={"solution_name": "Access Controls", "version": "0.1.0"},
    ).json()
    client.post(
        f"/solutions/{solution['solution_id']}/phases",
        json={
            "phases": [
                {"phase_id": "backlog", "is_enabled": True},
                {"phase_id": "requirements", "is_enabled": True},
            ]
        },
    )
    sub = client.post(
        f"/solutions/{solution['solution_id']}/subcomponents",
        json={"subcomponent_name": "Define RBAC"},
    ).json()
    return project, solution, sub


def test_checklist_sync_and_bulk_update():
    client, SessionLocal = setup_test_app()
    seed_phases(SessionLocal)
    _, solution, sub = bootstrap(client)

    # initial sync should create rows for enabled phases
    resp = client.get(f"/subcomponents/{sub['subcomponent_id']}/phases")
    assert resp.status_code == 200
    items = resp.json()
    assert len(items) == 2
    assert {i["phase_id"] for i in items} == {"backlog", "requirements"}
    assert all(i["is_complete"] is False for i in items)

    # bulk update completion
    updates = [
        {"solution_phase_id": items[0]["solution_phase_id"], "is_complete": True},
        {"solution_phase_id": items[1]["solution_phase_id"], "is_complete": False},
    ]
    bulk_resp = client.post(
        f"/subcomponents/{sub['subcomponent_id']}/phases/bulk",
        json={"updates": updates},
    )
    assert bulk_resp.status_code == 200, bulk_resp.text
    updated = bulk_resp.json()
    completed_flags = {i["solution_phase_id"]: i["is_complete"] for i in updated}
    assert completed_flags[updates[0]["solution_phase_id"]] is True
    assert completed_flags[updates[1]["solution_phase_id"]] is False
