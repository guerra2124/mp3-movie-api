# MP3 Movie API

This project is a FastAPI application that stores a movie collection in SQLite and caches repeated retrievals. `POST /upload` reads a CSV with the columns `title`, `release_year`, `rating`, and `genre`, checks the columns and rows, and replaces the stored collection through the `MovieStorage` class in `src/storage.py`. `src/database.py` creates the SQLite connection and the `movies` table, and every read, filter, sort, and count uses SQL with parameterized queries. `GET /movies` returns movies with a total count, and `GET /movies/search` filters by minimum rating and returns only the requested columns. `POST /movies/process` reuses the MP1 `data_pipeline` functions to validate and clean the stored movies, then saves the cleaned rows back to SQLite. `src/cache.py` caches `GET /movies` responses in FakeRedis for 90 seconds, keyed by `limit`, so repeated requests skip the database. Every successful upload or processing run invalidates the cache, so clients never get stale data. Request logging comes from `src/middleware.py`, and `src/models.py` defines the Pydantic request and response models.

## Running the API

```bash
python -m uvicorn main:app --reload
```

Then open http://127.0.0.1:8000/docs.

## Running the Tests

```bash
python -m pytest tests -v
```

## Sample Processing Request

After uploading `fixtures/sample_movies.csv`, send this body to `POST /movies/process`:

```json
{
  "validation": {
    "required_columns": ["title", "release_year", "rating", "genre"],
    "numeric_columns": ["release_year", "rating"]
  },
  "processing": {
    "remove_duplicates": true,
    "missing": {"enabled": true, "axis": "rows"},
    "outliers": {
      "enabled": true,
      "columns": ["rating"],
      "method": "iqr",
      "threshold": 1.5
    }
  }
}
```

Expected response:

```json
{
  "validation_rows_removed": 0,
  "cleaning_report": {
    "rows_before": 20,
    "rows_after": 16,
    "rows_removed": 4,
    "columns_before": 4,
    "columns_after": 4,
    "columns_removed": 0
  }
}
```