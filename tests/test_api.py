def test_upload_csv(client, sample_csv_bytes):
    response = client.post(
        "/upload",
        files={"file": ("sample_movies.csv", sample_csv_bytes, "text/csv")}
    )
    assert response.status_code == 200
    assert response.json() == {
        "filename": "sample_movies.csv",
        "rows": 20,
        "columns": 4,
        "column_names": ["title", "release_year", "rating", "genre"],
    }


def test_get_movies_with_limit(client, uploaded_movies):
    response = client.get("/movies", params={"limit": 2})
    assert response.status_code == 200
    body = response.json()
    assert body["total_rows"] == 20
    assert [row["id"] for row in body["data"]] == [1, 2]
    assert [row["title"] for row in body["data"]] == ["Movie A", "Movie B"]


def test_search_movies(client, uploaded_movies):
    response = client.get("/movies/search", params={"min_rating": 8.5, "limit": 2})
    assert response.status_code == 200
    assert response.json() == [
        {"id": 4, "title": "Movie C"},
        {"id": 2, "title": "Movie B"},
    ]

    response = client.get(
        "/movies/search",
        params={"columns": ["title", "rating"], "min_rating": 8.5, "limit": 2}
    )
    assert response.status_code == 200
    assert response.json() == [
        {"id": 4, "title": "Movie C", "rating": 9.0},
        {"id": 2, "title": "Movie B", "rating": 8.5},
    ]


def test_upload_replaces_collection(client, uploaded_movies, sample_csv_bytes):
    client.post(
        "/upload",
        files={"file": ("sample_movies.csv", sample_csv_bytes, "text/csv")}
    )
    response = client.get("/movies")
    assert response.json()["total_rows"] == 20


def test_process_and_retrieve(client, uploaded_movies, processing_body):
    response = client.post("/movies/process", json=processing_body)
    assert response.status_code == 200
    report = response.json()
    assert report["validation_rows_removed"] == 0
    assert report["cleaning_report"]["rows_before"] == 20
    assert report["cleaning_report"]["rows_after"] == 16

    response = client.get("/movies")
    assert response.json()["total_rows"] == 16


def test_unsupported_file_and_health(client):
    response = client.post(
        "/upload",
        files={"file": ("notes.txt", b"hello", "text/plain")}
    )
    assert response.status_code == 400

    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_invalid_search_column(client, uploaded_movies):
    response = client.get("/movies/search", params={"columns": "unknown"})
    assert response.status_code == 400