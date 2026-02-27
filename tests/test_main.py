def test_root_endpoint(client):
    response = client.get("/")
    assert response.status_code == 200
    assert "Welcome to Nepali Handicrafts API" in response.json()["message"]

def test_health_check(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"
