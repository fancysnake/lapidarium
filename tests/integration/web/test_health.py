from http import HTTPStatus


def test_healthz_answers_without_touching_the_database(client):
    response = client.get("/healthz/")

    assert response.status_code == HTTPStatus.OK
    assert response.content == b"ok"
    assert response["Content-Type"] == "text/plain"
    assert "no-cache" in response["Cache-Control"]
