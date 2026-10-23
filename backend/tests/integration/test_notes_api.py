"""Notes through the web API."""


def test_notes_api(make_client):
    client, _ = make_client()
    page = client.post("/api/notes", json={"title": "Weekly plan", "content": [{"type": "todo", "text": "Apply to 10"}]}).json()["page"]
    child = client.post("/api/notes", json={"title": "Monday", "parent_id": page["id"]}).json()["page"]
    assert [p["title"] for p in client.get("/api/notes").json()["pages"]] == ["Weekly plan", "Monday"]
    assert "content" not in client.get("/api/notes").json()["pages"][0]  # the tree has no blocks

    saved = client.patch(f"/api/notes/{page['id']}", json={"content": [{"type": "todo", "text": "Apply", "checked": True}]}).json()
    assert saved["page"]["content"][0]["checked"] is True
    assert client.patch(f"/api/notes/{page['id']}", json={"content": [{"type": "video"}]}).status_code == 400
    assert client.post(f"/api/notes/{child['id']}/move", json={"parent_id": None, "position": 0}).json()["pages"][0]["title"] == "Monday"
    assert client.post(f"/api/notes/{child['id']}/move", json={"parent_id": "x"}).status_code == 400

    assert client.delete(f"/api/notes/{page['id']}").json() == {"ok": True}
    assert client.get(f"/api/notes/{page['id']}").status_code == 404
    client.post("/api/auth/logout")
    assert client.get("/api/notes").status_code == 401
