from fastapi.testclient import TestClient

from budgetscope.main import app


def test_app_exposes_openapi_schema() -> None:
    with TestClient(app) as client:
        response = client.get("/openapi.json")

    assert response.status_code == 200
    assert response.json()["info"]["title"] == "BudgetScope"
