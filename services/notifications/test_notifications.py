import pytest
from app import app

@pytest.fixture
def client():
    return app.test_client()

def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json == {"service": "notifications", "status": "ok"}