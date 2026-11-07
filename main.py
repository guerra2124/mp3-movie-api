import io
import logging
from pathlib import Path
import pandas as pd
from fastapi import FastAPI, File, HTTPException, Query, UploadFile
from src import (
    HealthResponse,
    MovieDataResponse,
    MovieProcessingReport,
    MovieStorage,
    MovieUploadInfo,
    ProcessConfig,
    log_requests,
    setup_logging,
)
from src.storage import MOVIE_COLUMNS
from data_pipeline import create_cleaning_report, process_data, validate_dataframe

setup_logging(verbose=True)
logger = logging.getLogger(__name__)

app = FastAPI(title="Data Processing API", version="1.0.0")
app.middleware("http")(log_requests)
storage = MovieStorage()


@app.get("/health", response_model=HealthResponse)
def health_check():
    """Return the application status and version."""
    return {"status": "ok", "version": app.version}


@app.post("/upload", response_model=MovieUploadInfo)
async def upload_movies(file: UploadFile = File(...)):
    """Read a movie CSV and replace the stored collection."""
    suffix = Path(file.filename or "").suffix.lower()
    if suffix != ".csv":
        logger.warning(f"Unsupported file format: {suffix}")
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file format: '{suffix}'. Please upload a .csv file."
        )

    contents = await file.read()
    try:
        df = pd.read_csv(io.BytesIO(contents))
    except (pd.errors.EmptyDataError, pd.errors.ParserError, UnicodeDecodeError) as error:
        logger.warning(f"Could not read CSV {file.filename}: {error}")
        raise HTTPException(
            status_code=400,
            detail=f"Could not read the CSV file: {error}"
        ) from error

    if sorted(df.columns) != sorted(MOVIE_COLUMNS):
        logger.warning(f"Invalid columns in {file.filename}: {list(df.columns)}")
        raise HTTPException(
            status_code=400,
            detail=f"CSV must have exactly these columns: {', '.join(MOVIE_COLUMNS)}"
        )

    if df.empty:
        logger.warning(f"No data rows in {file.filename}")
        raise HTTPException(status_code=400, detail="CSV must contain at least one data row")

    df = df[MOVIE_COLUMNS]

    storage.save(df)
    logger.info(f"Uploaded movies: filename={file.filename}, rows={len(df)}")
    return {
        "filename": file.filename,
        "rows": len(df),
        "columns": len(df.columns),
        "column_names": list(df.columns),
    }


@app.get("/movies", response_model=MovieDataResponse)
def get_movies(limit: int = Query(default=100, ge=1)):
    """Return up to limit stored movies and the total count."""
    data = storage.select_columns(MOVIE_COLUMNS, limit)
    total_rows = storage.count_movies()
    logger.info(f"Retrieved movies: returned_rows={len(data)}, total_rows={total_rows}")
    return {"data": data, "total_rows": total_rows}

@app.get("/movies/search", response_model=list[dict])
def query_movies(
    columns: list[str] = Query(default=["title"]),
    min_rating: float = Query(default=0, ge=0, le=10),
    limit: int = Query(default=100, ge=1)
):
    """Return selected fields from movies at or above min_rating."""
    try:
        results = storage.query_movies(columns, min_rating, limit)
    except ValueError as error:
        logger.warning(f"Invalid movie query: {error}")
        raise HTTPException(status_code=400, detail=str(error)) from error

    logger.info(
        f"Queried movies: columns={columns}, "
        f"min_rating={min_rating}, returned_rows={len(results)}"
    )
    return results


@app.post("/movies/process", response_model=MovieProcessingReport)
def process_movies(config: ProcessConfig):
    """Validate and process the stored movies using MP1 functions."""
    df = storage.get()
    if df.empty:
        logger.warning("No movies stored to process")
        raise HTTPException(status_code=400, detail="No movies stored. Upload a CSV first.")

    config_dict = config.model_dump()
    validation = config_dict["validation"]

    missing_numeric = [col for col in validation["numeric_columns"] if col not in df.columns]
    if missing_numeric:
        logger.warning(f"Numeric columns not found in movies: {missing_numeric}")
        raise HTTPException(
            status_code=400,
            detail=f"Numeric column(s) not found: {', '.join(missing_numeric)}"
        )

    try:
        rows_before_validation = len(df)
        validated = validate_dataframe(
            df,
            validation["required_columns"],
            validation["numeric_columns"],
        )
        validation_rows_removed = rows_before_validation - len(validated)
        validated_copy = validated.copy()

        processed = process_data(validated, config_dict)
        cleaning_report = create_cleaning_report(validated_copy, processed)
    except ValueError as error:
        logger.warning(f"Processing failed for movies: {error}")
        raise HTTPException(status_code=400, detail=str(error)) from error

    storage.save(processed)
    logger.info(
        f"Processed movies: "
        f"validation_removed={validation_rows_removed}, "
        f"rows_before={cleaning_report['rows_before']}, "
        f"rows_after={cleaning_report['rows_after']}"
    )
    return {
        "validation_rows_removed": validation_rows_removed,
        "cleaning_report": cleaning_report,
    }