"""Signing in a test client (every API route except /api/auth/* needs a signed-in user)."""

OWNER = {"name": "Test Owner", "email": "owner@example.com", "password": "correct horse battery"}


def signed_in(client):
    """Create the owner account on first use (or sign in to it) and return the client with its cookie."""
    setup_required = client.get("/api/auth/status").json()["setup_required"]
    response = client.post("/api/auth/setup" if setup_required else "/api/auth/login", json=OWNER)
    assert response.status_code == 200, response.text
    return client
