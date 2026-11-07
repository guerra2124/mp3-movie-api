import logging
import pandas as pd

logger = logging.getLogger(__name__)


def validate_dataframe(df, required_columns, numeric_columns):
    """Validate the DataFrame and return valid data.

    required_columns: a list of column names that must exist.
    numeric_columns: a list of column names whose values should be numeric.
    """
    rows_before = len(df)

    for col in required_columns:
        if col not in df.columns:
            logger.error(f"Missing required column: {col}")
            raise ValueError(f"Missing required column: {col}")

    for col in numeric_columns:
        invalid_rows = []

        for i, value in df[col].items():
            if pd.notna(value):
                try:
                    float(value)
                except ValueError:
                    invalid_rows.append(i)

        if invalid_rows:
            logger.warning(
                f"Removed {len(invalid_rows)} rows with invalid numeric values in {col}"
            )
            df = df.drop(index=invalid_rows)

        # convert to a numeric data type
        df[col] = pd.to_numeric(df[col])

    rows_after = len(df)
    logger.debug(f"Validation: {rows_before} -> {rows_after} rows")
    return df