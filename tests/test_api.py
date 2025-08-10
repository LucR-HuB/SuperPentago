from fastapi.testclient import TestClient
from server.main import app

def test_api_flow():
    client = TestClient(app)
    r = client.post("/new")
    assert r.status_code == 200
    data = r.json()
    gid = data["game_id"]
    r = client.get(f"/state/{gid}")
    assert r.status_code == 200
    r = client.post(f"/play/{gid}", json={"cell":"C3","quadrant":"Q00","direction":"CW"})
    assert r.status_code == 200
    r = client.post(f"/bot/{gid}", json={"depth":2})
    assert r.status_code == 200
    js = r.json()
    assert "move" in js and isinstance(js["move"], str)