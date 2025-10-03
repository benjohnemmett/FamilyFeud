import pytest
from httpx import AsyncClient
from main import asgi_app


@pytest.mark.asyncio
async def test_state_endpoint():
    async with AsyncClient(app=asgi_app, base_url='http://test') as ac:
        r = await ac.get('/api/state')
    assert r.status_code == 200
    data = r.json()
    assert 'question' in data
    assert 'answers' in data
    assert isinstance(data['answers'], list)
import json
from app import app

def test_state_endpoint():
    client = app.test_client()
    r = client.get('/api/state')
    assert r.status_code == 200
    data = r.get_json()
    assert 'question' in data
    assert 'answers' in data
    assert isinstance(data['answers'], list)
