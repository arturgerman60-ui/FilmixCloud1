from fastapi.testclient import TestClient

from app.main import app, store


client = TestClient(app)


def setup_function() -> None:
    store.clear()


def test_index_serves_local_website() -> None:
    response = client.get("/")

    assert response.status_code == 200
    assert "Карта гражданских рисков" in response.text


def test_create_report_and_list_events() -> None:
    response = client.post(
        "/api/reports",
        json={
            "text": "БПЛА в районі Кременчук, ймовірно на Полтаву",
            "source": "test",
        },
    )

    assert response.status_code == 201
    event = response.json()
    assert event["threat_type"] == "uav"
    assert event["primary_location"] == "кременчук"
    assert isinstance(event["direction_uncertainty_deg"], int)

    list_response = client.get("/api/events")
    assert list_response.status_code == 200
    assert len(list_response.json()["events"]) == 1


def test_geojson_returns_feature_collection() -> None:
    client.post(
        "/api/reports",
        json={
            "text": "КАБ у напрямку Харківського району",
            "source": "test",
        },
    )

    response = client.get("/api/events.geojson")

    assert response.status_code == 200
    body = response.json()
    assert body["type"] == "FeatureCollection"
    assert len(body["features"]) == 1
    assert body["features"][0]["properties"]["threat_type"] == "kab"
    assert "direction_uncertainty_deg" in body["features"][0]["properties"]


def test_telegram_status_endpoint_exists() -> None:
    response = client.get("/api/telegram/status")

    assert response.status_code == 200
    body = response.json()
    assert "enabled" in body
    assert "configured" in body
    assert body["mode"] in {"none", "bot_api", "telethon", "web_public"}
