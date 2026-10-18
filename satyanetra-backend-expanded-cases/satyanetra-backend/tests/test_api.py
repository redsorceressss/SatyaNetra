import os
os.environ["DATABASE_URL"] = "sqlite:///./test_satyanetra.db"
os.environ["JWT_SECRET"] = "test-secret-that-is-long-enough-for-local-tests-only"
from fastapi.testclient import TestClient
from app.main import app
client = TestClient(app)

def test_health():
    r = client.get("/api/v1/health")
    assert r.status_code == 200 and r.json()["status"] == "ok"

def test_register_login_and_protected_profile():
    email = "testuser@example.com"
    r = client.post("/api/v1/auth/register", json={"name":"Test User","email":email,"password":"CorrectHorseBattery12!","role":"individual"})
    assert r.status_code in (201, 409)
    r = client.post("/api/v1/auth/login", json={"email":email,"password":"CorrectHorseBattery12!"})
    assert r.status_code == 200
    token = r.json()["access_token"]
    assert client.get("/api/v1/auth/me", headers={"Authorization":f"Bearer {token}"}).status_code == 200
    assert client.get("/api/v1/auth/me").status_code == 401

def test_privileged_role_cannot_self_register():
    r = client.post("/api/v1/auth/register", json={"name":"Bad Actor","email":"role-escalation@example.com","password":"CorrectHorseBattery12!","role":"admin"})
    assert r.status_code == 400

def test_guest_report_and_reference_lookup():
    r = client.post("/api/v1/reports", json={"category":"Bribery","description":"A sufficiently long synthetic test report description.","anonymous":True})
    assert r.status_code == 201
    ref = r.json()["reference"]
    lookup = client.get(f"/api/v1/reports/{ref}")
    assert lookup.status_code == 200
    assert lookup.json()["reference"] == ref
    assert "description" not in lookup.json()
    assert "contact_email" not in lookup.json()

def test_ai_mock_is_labelled():
    r = client.post("/api/v1/ai/ask", json={"message":"How do I report bribery?"})
    assert r.status_code == 200
    assert r.json()["mode"] == "mock"


def test_public_cases_have_provenance_and_filters():
    r = client.get("/api/v1/public-cases")
    assert r.status_code == 200
    body = r.json()
    assert body["count"] >= 8
    assert all(c["source_url"].startswith("https://") for c in body["records"])
    assert all("status_basis" in c and "case_status" in c for c in body["records"])
    la = client.get("/api/v1/public-cases", params={"state": "Louisiana"})
    assert la.status_code == 200
    assert la.json()["count"] >= 3
    assert all(c["state"] == "Louisiana" for c in la.json()["records"])

def test_public_report_lookup_does_not_expose_description():
    r = client.post("/api/v1/reports", json={"category":"Bribery","description":"Synthetic report description for testing privacy.","anonymous":True})
    ref = r.json()["reference"]
    lookup = client.get(f"/api/v1/reports/{ref}")
    assert lookup.status_code == 200
    assert "description" not in lookup.json()
    assert "location" not in lookup.json()
