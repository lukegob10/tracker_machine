import os
import sys

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from backend.app.deps import get_db
from backend.app.main import app
from backend.app.models import Base


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
    return TestClient(app)


def create_project(client: TestClient):
    resp = client.post(
        "/projects/",
        json={
            "project_name": "Data Platform",
            "name_abbreviation": "DPLT",
            "description": "Modernize data stack",
        },
    )
    assert resp.status_code == 201
    return resp.json()


def test_create_and_list_solutions():
    client = setup_test_app()
    project = create_project(client)

    resp = client.post(
        f"/projects/{project['project_id']}/solutions",
        json={
            "solution_name": "Access Controls",
            "version": "0.1.0",
            "status": "active",
            "description": "RBAC and audit",
        },
    )
    assert resp.status_code == 201, resp.text
    data = resp.json()
    assert data["solution_name"] == "Access Controls"
    assert data["version"] == "0.1.0"

    list_resp = client.get(f"/projects/{project['project_id']}/solutions")
    assert list_resp.status_code == 200
    items = list_resp.json()
    assert len(items) == 1
    assert items[0]["solution_name"] == "Access Controls"


def test_solution_uniqueness_per_project_version():
    client = setup_test_app()
    project = create_project(client)
    payload = {
        "solution_name": "Access Controls",
        "version": "0.1.0",
        "status": "active",
    }
    assert (
        client.post(f"/projects/{project['project_id']}/solutions", json=payload).status_code
        == 201
    )
    dup_resp = client.post(f"/projects/{project['project_id']}/solutions", json=payload)
    assert dup_resp.status_code == 400
    assert "already exist" in dup_resp.json()["detail"]

    # Different version should be allowed
    payload["version"] = "0.2.0"
    assert (
        client.post(f"/projects/{project['project_id']}/solutions", json=payload).status_code
        == 201
    )


def test_update_solution_status_and_description():
    client = setup_test_app()
    project = create_project(client)
    created = client.post(
        f"/projects/{project['project_id']}/solutions",
        json={"solution_name": "Portal", "version": "1.0.0"},
    ).json()
    solution_id = created["solution_id"]

    update_resp = client.patch(
        f"/solutions/{solution_id}",
        json={"status": "complete", "description": "Shipped"},
    )
    assert update_resp.status_code == 200
    updated = update_resp.json()
    assert updated["status"] == "complete"
    assert updated["description"] == "Shipped"


def test_delete_solution_soft_deletes():
    client = setup_test_app()
    project = create_project(client)
    created = client.post(
        f"/projects/{project['project_id']}/solutions",
        json={"solution_name": "Billing", "version": "0.1.0"},
    ).json()
    solution_id = created["solution_id"]

    delete_resp = client.delete(f"/solutions/{solution_id}")
    assert delete_resp.status_code == 204

    get_resp = client.get(f"/solutions/{solution_id}")
    assert get_resp.status_code == 404

    list_resp = client.get(f"/projects/{project['project_id']}/solutions")
    assert list_resp.status_code == 200
    assert list_resp.json() == []
