def test_app_docs_reachable(client):
    """
    Test that the application is running and accessible.
    We check /docs as a proxy for the app being up.
    """
    response = client.get("/docs")
    assert response.status_code == 200
