from fastapi.testclient import TestClient
from server.main import app

client = TestClient(app)

def test_new_and_mcts_move():
    r = client.post("/new")
    assert r.status_code == 200
    data = r.json()
    gid = data["game_id"]
    assert data["state"]["to_move"] == "B"

    r2 = client.post(f"/bot/{gid}", json={"depth": 2, "time_ms": 50, "engine": "mcts"})
    assert r2.status_code == 200
    data2 = r2.json()
    assert "move" in data2
    assert data2["engine"] == "mcts"
    assert data2["state"]["to_move"] == "W"