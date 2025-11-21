from fastapi.testclient import TestClient
from app.main import app
from app.db.models import Property, PropertyEvent

def test_read_main(test_client: TestClient):
    response = test_client.get("/")
    assert response.status_code == 200
    assert response.json() == {"Hello": "World"}


def test_create_and_read_property(test_client: TestClient, db_session):
    # Create a property
    db_property = Property(id=1, synthetic_stateid="test", CONAME="test county")
    db_session.add(db_property)
    db_session.commit()
    db_session.refresh(db_property)

    # Read the property
    response = test_client.get("/api/v1/properties/1")
    assert response.status_code == 200
    assert response.json()["id"] == 1
    assert response.json()["synthetic_stateid"] == "test"


def test_read_property_not_found(test_client: TestClient):
    response = test_client.get("/api/v1/properties/999")
    assert response.status_code == 404
    assert response.json() == {"detail": "Property not found"}


def test_create_and_read_event(test_client: TestClient, db_session):
    # Create a property to associate with the event
    db_property = Property(id=1, synthetic_stateid="test", CONAME="test county")
    db_session.add(db_property)
    db_session.commit()
    db_session.refresh(db_property)
    
    # Create an event
    db_event = PropertyEvent(
        event_id=1,
        event_type="sale",
        event_date="2025-11-21T00:00:00",
        raw_parcel_identification="test",
    )
    db_session.add(db_event)
    db_session.commit()
    db_session.refresh(db_event)

    # Read the event
    response = test_client.get("/api/v1/events/1")
    assert response.status_code == 200
    assert response.json()["event_id"] == 1
    assert response.json()["event_type"] == "sale"


def test_read_event_not_found(test_client: TestClient):
    response = test_client.get("/api/v1/events/999")
    assert response.status_code == 404
    assert response.json() == {"detail": "Event not found"}
