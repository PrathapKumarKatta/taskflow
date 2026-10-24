from app.main import migration_heads


async def test_readiness_rejects_outdated_schema(client, monkeypatch):
    monkeypatch.setattr("app.main.migration_heads", lambda: frozenset({"unapplied_revision"}))
    response = await client.get("/health/ready")
    assert response.status_code == 503
    assert response.json() == {"status": "migration_required"}
    assert (await client.get("/health")).status_code == 200


def test_packaged_migration_heads():
    assert migration_heads() == frozenset({"d3ab45f21c90"})
