def test_upload_csv(client, sample_csv_bytes):
    response = client.post(
        "/upload",
        files={"file": ("sample_data.csv", sample_csv_bytes, "text/csv")}
    )
    assert response.status_code == 200
    body = response.json()
    assert body["rows"] == 6
    assert body["columns"] == 2
    assert isinstance(body["id"], int)
    assert body["id"] > 0


def test_process_and_retrieve(client, uploaded_dataset_id, processing_body):
    response = client.post(
        f"/datasets/{uploaded_dataset_id}/process",
        json=processing_body
    )
    assert response.status_code == 200
    report = response.json()
    assert report["validation_rows_removed"] == 1
    assert report["cleaning_report"]["rows_before"] == 5
    assert report["cleaning_report"]["rows_after"] == 3

    response = client.get(f"/datasets/{uploaded_dataset_id}")
    assert response.status_code == 200
    body = response.json()
    assert body["total_rows"] == 3
    student_ids = [row["student_id"] for row in body["data"]]
    scores = [row["score"] for row in body["data"]]
    assert student_ids == [1, 2, 5]
    assert scores == [80, 90, 85]


def test_retrieve_missing_dataset(client):
    response = client.get("/datasets/999")
    assert response.status_code == 404