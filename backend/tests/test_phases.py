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
                Phase(
                    phase_id="uat",
                    phase_group="Deployment",
                    phase_name="UAT Deployment",
                    sequence=3,
                ),
            ]
        )
        session.commit()


def create_project_and_solution(client: TestClient):
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


def test_list_phases():
    client, SessionLocal = setup_test_app()
    seed_phases(SessionLocal)
    resp = client.get("/phases")
    assert resp.status_code == 200
    data = resp.json()
    assert [p["phase_id"] for p in data] == ["backlog", "requirements", "uat"]


def test_set_and_get_solution_phases():
    client, SessionLocal = setup_test_app()
    seed_phases(SessionLocal)
    _, solution = create_project_and_solution(client)

    set_resp = client.post(
        f"/solutions/{solution['solution_id']}/phases",
        json={
            "phases": [
                {"phase_id": "backlog", "is_enabled": True},
                {"phase_id": "requirements", "is_enabled": True, "sequence_override": 5},
            ]
        },
    )
    assert set_resp.status_code == 200, set_resp.text
    items = set_resp.json()
    assert len(items) == 2
    assert items[0]["phase_id"] == "backlog"
    assert items[0]["is_enabled"] is True

    list_resp = client.get(f"/solutions/{solution['solution_id']}/phases")
    assert list_resp.status_code == 200
    listed = list_resp.json()
    assert len(listed) == 2
    assert listed[1]["phase_id"] == "requirements"
    assert listed[1]["sequence_override"] == 5
