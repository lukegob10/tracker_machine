import os
import sys
from datetime import date

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


def create_project_solution(client: TestClient):
    project = client.post(
        "/projects/",
        json={
            "project_name": "Data Platform",
            "name_abbreviation": "DPLT",
            "description": "Modernize data stack",
        },
    ).json()
    solution = client.post(
        f"/projects/{project['project_id']}/solutions",
        json={"solution_name": "Access Controls", "version": "0.1.0"},
    ).json()
    return project, solution


def enable_phases(client: TestClient, solution_id: str):
    resp = client.post(
        f"/solutions/{solution_id}/phases",
        json={
            "phases": [
                {"phase_id": "backlog", "is_enabled": True},
                {"phase_id": "requirements", "is_enabled": True},
            ]
        },
    )
    assert resp.status_code == 200


def test_create_and_list_subcomponents():
    client, SessionLocal = setup_test_app()
    seed_phases(SessionLocal)
    _, solution = create_project_solution(client)
    enable_phases(client, solution["solution_id"])

    resp = client.post(
        f"/solutions/{solution['solution_id']}/subcomponents",
        json={
            "subcomponent_name": "Define RBAC roles",
            "priority": 1,
            "due_date": date.today().isoformat(),
            "sub_phase": "backlog",
        },
    )
    assert resp.status_code == 201, resp.text
    data = resp.json()
    assert data["subcomponent_name"] == "Define RBAC roles"
    assert data["priority"] == 1

    list_resp = client.get(f"/solutions/{solution['solution_id']}/subcomponents")
    assert list_resp.status_code == 200
    items = list_resp.json()
    assert len(items) == 1
    assert items[0]["sub_phase"] == "backlog"


def test_sub_phase_validation():
    client, SessionLocal = setup_test_app()
    seed_phases(SessionLocal)
    _, solution = create_project_solution(client)
    enable_phases(client, solution["solution_id"])

    bad_resp = client.post(
        f"/solutions/{solution['solution_id']}/subcomponents",
        json={"subcomponent_name": "Invalid phase", "sub_phase": "nonexistent"},
    )
    assert bad_resp.status_code == 400


def test_subcomponent_uniqueness_and_soft_delete():
    client, SessionLocal = setup_test_app()
    seed_phases(SessionLocal)
    _, solution = create_project_solution(client)
    enable_phases(client, solution["solution_id"])

    payload = {"subcomponent_name": "Billing UI"}
    assert client.post(f"/solutions/{solution['solution_id']}/subcomponents", json=payload).status_code == 201
    dup = client.post(f"/solutions/{solution['solution_id']}/subcomponents", json=payload)
    assert dup.status_code == 400

    # soft delete
    created = client.get(f"/solutions/{solution['solution_id']}/subcomponents").json()[0]
    delete_resp = client.delete(f"/subcomponents/{created['subcomponent_id']}")
    assert delete_resp.status_code == 204

    get_resp = client.get(f"/subcomponents/{created['subcomponent_id']}")
    assert get_resp.status_code == 404

    list_resp = client.get(f"/solutions/{solution['solution_id']}/subcomponents")
    assert list_resp.status_code == 200
    assert list_resp.json() == []
