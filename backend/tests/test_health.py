def test_root(client):
    r = client.get("/")
    assert r.status_code == 200
    data = r.json()
    assert "name" in data
    assert "version" in data


def test_simple_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "healthy"


def test_health_status(client):
    r = client.get("/api/v1/health/status")
    assert r.status_code == 200
    data = r.json()
    assert "status" in data
    assert "components" in data
    assert "version" in data


def test_health_ready(client):
    r = client.get("/api/v1/health/ready")
    assert r.status_code == 200
    assert r.json()["status"] == "ready"


def test_health_live(client):
    r = client.get("/api/v1/health/live")
    assert r.status_code == 200
    assert r.json()["status"] == "alive"


def test_monitoring_metrics_alias(client):
    r = client.get("/api/v1/monitoring/metrics")
    assert r.status_code == 200
    data = r.json()
    assert "total_documents" in data
