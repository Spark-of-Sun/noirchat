import os
from pathlib import Path
import sys

# Load .env into environment for settings
p = Path(__file__).resolve().parents[1] / ".env"
if p.exists():
    for line in p.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        k, v = line.split('=', 1)
        # Strip inline comments after the value
        v = v.split('#', 1)[0].strip()
        os.environ[k.strip()] = v

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient


def _patch_db_redis_noop():
    # Patch DB/Redis create/close to no-ops to avoid external dependencies
    async def noop(*a, **k):
        return None

    import app.store.database as db
    import app.store.redis_store as rds

    db.create_pool = noop
    db.close_pool = noop
    rds.create_redis = noop
    rds.close_redis = noop


def test_health_endpoint():
    import app.server as server

    _patch_db_redis_noop()

    app = server.create_app()
    with TestClient(app) as client:
        r = client.get('/health')
        assert r.status_code == 200
        assert r.json() == {'status': 'ok'}


def test_register_and_login_endpoints():
    # Ensure DB/Redis no-op patches are applied
    _patch_db_redis_noop()

    import app.server as server
    # Patch repository functions used by auth routes
    import app.api.auth as auth_mod
    import app.api.dependencies as deps_mod

    async def fake_get_user_by_username(db_param, username):
        return None

    async def fake_create_user(db_param, user):
        return user

    auth_mod.get_user_by_username = fake_get_user_by_username
    auth_mod.create_user = fake_create_user

    # get_db dependency should return a dummy object
    deps_mod.get_db = lambda: object()

    # Also patch login handler to a simple stub for login test
    async def fake_login(db, username, passphrase):
        return 'token-stub'

    auth_mod.login = fake_login

    app = server.create_app()
    with TestClient(app) as client:
        # Register
        r = client.post('/v1/auth/register', json={'username': 'alice', 'passphrase': 'supersecret', 'ack_code': 'ACK1'})
        assert r.status_code == 201
        body = r.json()
        assert 'user_id' in body and body['username'] == 'alice'

        # Login
        r2 = client.post('/v1/auth/login', json={'username': 'alice', 'passphrase': 'supersecret'})
        assert r2.status_code == 200
        assert r2.json().get('access_token') == 'token-stub'
