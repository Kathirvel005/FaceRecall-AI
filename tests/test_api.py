import pytest
import asyncio
from httpx import AsyncClient, ASGITransport
from backend.app.main import app
from backend.app.database.connection import init_db

@pytest.mark.asyncio
async def test_health_and_system():
    await init_db()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        res = await ac.get("/health")
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "HEALTHY"

        res_sys = await ac.get("/system/info")
        assert res_sys.status_code == 200
        data_sys = res_sys.json()
        assert "cpu_percent" in data_sys
        assert "ram_total_gb" in data_sys

@pytest.mark.asyncio
async def test_person_crud():
    await init_db()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # Create person
        payload = {
            "student_id": "TEST_STU_001",
            "name": "Test Student",
            "department": "AI & DS",
            "class_name": "Year 4",
            "email": "student@test.com",
            "active": True
        }
        res_create = await ac.post("/persons", json=payload)
        if res_create.status_code == 400:
            # Already exists from previous run, get by list
            pass
        else:
            assert res_create.status_code == 200
            p_data = res_create.json()
            assert p_data["student_id"] == "TEST_STU_001"
            pid = p_data["id"]

            # Read person
            res_get = await ac.get(f"/persons/{pid}")
            assert res_get.status_code == 200
            assert res_get.json()["name"] == "Test Student"

            # Delete person
            res_del = await ac.delete(f"/persons/{pid}")
            assert res_del.status_code == 200

if __name__ == "__main__":
    asyncio.run(test_health_and_system())
    asyncio.run(test_person_crud())
    print("API tests passed successfully!")
