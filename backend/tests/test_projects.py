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
        poolclass=StaticPool,  # share the same in-memory DB across connections
    )
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    def get_test_db():
        with TestingSessionLocal() as session:
            yield session

    app.dependency_overrides[get_db] = get_test_db
    return TestClient(app)


def test_create_and_list_projects():
    client = setup_test_app()
    resp = client.post(
        "/projects/",
        json={
            "project_name": "Data Platform",
            "name_abbreviation": "DPLT",
            "description": "Modernize data stack",
        },
    )
    assert resp.status_code == 201, resp.text
    data = resp.json()
    assert data["project_name"] == "Data Platform"
    assert data["name_abbreviation"] == "DPLT"
    assert data["status"] == "not_started"

    list_resp = client.get("/projects/")
    assert list_resp.status_code == 200
    projects = list_resp.json()
    assert len(projects) == 1
    assert projects[0]["project_name"] == "Data Platform"


def test_project_name_uniqueness():
    client = setup_test_app()
    payload = {
        "project_name": "Access Controls",
        "name_abbreviation": "ACCS",
        "status": "active",
    }
    assert client.post("/projects/", json=payload).status_code == 201
    dup_resp = client.post("/projects/", json=payload)
    assert dup_resp.status_code == 400
    assert dup_resp.json()["detail"] == "Project name already exists"


def test_update_project_status_and_description():
    client = setup_test_app()
    create = client.post(
        "/projects/",
        json={
            "project_name": "Portal",
            "name_abbreviation": "PORT",
            "status": "active",
        },
    ).json()
    project_id = create["project_id"]

    update_resp = client.patch(
        f"/projects/{project_id}",
        json={"status": "on_hold", "description": "Waiting on vendor"},
    )
    assert update_resp.status_code == 200
    updated = update_resp.json()
    assert updated["status"] == "on_hold"
    assert updated["description"] == "Waiting on vendor"


def test_delete_project_soft_deletes():
    client = setup_test_app()
    create = client.post(
        "/projects/",
        json={
            "project_name": "Billing",
            "name_abbreviation": "BILL",
        },
    ).json()
    project_id = create["project_id"]

    delete_resp = client.delete(f"/projects/{project_id}")
    assert delete_resp.status_code == 204

    get_resp = client.get(f"/projects/{project_id}")
    assert get_resp.status_code == 404

    list_resp = client.get("/projects/")
    assert list_resp.status_code == 200
    assert list_resp.json() == []
