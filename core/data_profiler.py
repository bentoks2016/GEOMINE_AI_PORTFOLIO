"""
Dataset profiling utilities for the SSML AI Engine.

Phase 3 responsibilities:
- inspect CSV files
- describe their schema
- detect possible latitude/longitude columns
- identify missing values and duplicates
- identify likely geometry
- suggest possible dataset roles

This module does NOT:
- alter source files
- register datasets
- train models
- decide whether records are valid ML labels
"""

from pathlib import Path
import pandas as pd


LAT_NAMES = {
    "lat",
    "latitude",
    "lat_dd",
    "y",
    "ycoord",
    "y_coord",
}

LON_NAMES = {
    "lon",
    "lng",
    "long",
    "longitude",
    "lon_dd",
    "x",
    "xcoord",
    "x_coord",
}

MINERAL_NAMES = {
    "mineral",
    "commodity",
    "commodity_name",
    "mineral_name",
}

GEOMETRY_NAMES = {
    "geometry",
    "geometry_wkt",
    "wkt",
    "geom",
}

SOURCE_NAMES = {
    "source",
    "reference",
    "provenance",
}

CONFIDENCE_NAMES = {
    "confidence",
    "interpretation_confidence",
    "coord_accuracy",
    "coordinate_accuracy",
}

LINE_HINTS = {
    "start_lat",
    "start_lon",
    "end_lat",
    "end_lon",
    "lineament",
    "fault",
}


def _normalise_column_name(name):
    return str(name).strip().lower()


def detect_coordinate_columns(columns):
    """
    Detect likely latitude and longitude columns.

    Returns:
        {
            "lat_column": ...,
            "lon_column": ...
        }
    """

    normalized = {
        _normalise_column_name(c): c
        for c in columns
    }

    lat = next(
        (
            normalized[name]
            for name in LAT_NAMES
            if name in normalized
        ),
        None,
    )

    lon = next(
        (
            normalized[name]
            for name in LON_NAMES
            if name in normalized
        ),
        None,
    )

    return {
        "lat_column": lat,
        "lon_column": lon,
    }


def detect_geometry_type(df):
    """
    Suggest likely geometry type.

    This is a suggestion only.
    User confirmation will be required in the UI.
    """

    cols = {
        _normalise_column_name(c)
        for c in df.columns
    }

    # WKT / explicit geometry
    geometry_cols = cols.intersection(GEOMETRY_NAMES)

    if geometry_cols:
        col_lookup = {
            _normalise_column_name(c): c
            for c in df.columns
        }

        geom_col = col_lookup[next(iter(geometry_cols))]

        samples = (
            df[geom_col]
            .dropna()
            .astype(str)
            .head(25)
            .str.upper()
        )

        if samples.str.startswith("POINT").any():
            return "POINT"

        if samples.str.startswith(
            ("LINESTRING", "MULTILINESTRING")
        ).any():
            return "LINE"

        if samples.str.startswith(
            ("POLYGON", "MULTIPOLYGON")
        ).any():
            return "POLYGON"

        return "MIXED"

    # Start/end coordinates imply lines
    if {
        "start_lat",
        "start_lon",
        "end_lat",
        "end_lon",
    }.issubset(cols):
        return "LINE"

    coords = detect_coordinate_columns(df.columns)

    if (
        coords["lat_column"] is not None
        and coords["lon_column"] is not None
    ):
        return "POINT"

    return "NONE"


def coordinate_quality(df, lat_col, lon_col):
    """
    Evaluate coordinate quality while distinguishing
    missing, nonnumeric, invalid and valid coordinates.

    Original coordinate values are never modified.
    """

    result = {
        "coordinate_rows": 0,
        "missing_coordinates": 0,
        "non_numeric_coordinates": 0,
        "invalid_latitude": 0,
        "invalid_longitude": 0,
        "valid_coordinate_rows": 0,
    }

    if not lat_col or not lon_col:
        return result

    raw_lat = df[lat_col]
    raw_lon = df[lon_col]

    missing_tokens = {
        "",
        "nan",
        "none",
        "null",
        "n/a",
        "na",
    }

    lat_blank = (
        raw_lat.isna()
        | raw_lat.astype(str).str.strip().str.lower().isin(missing_tokens)
    )

    lon_blank = (
        raw_lon.isna()
        | raw_lon.astype(str).str.strip().str.lower().isin(missing_tokens)
    )

    lat = pd.to_numeric(raw_lat, errors="coerce")
    lon = pd.to_numeric(raw_lon, errors="coerce")

    missing = lat_blank | lon_blank

    non_numeric_lat = ~lat_blank & lat.isna()
    non_numeric_lon = ~lon_blank & lon.isna()

    non_numeric = non_numeric_lat | non_numeric_lon

    invalid_lat = lat.notna() & ~lat.between(-90, 90)
    invalid_lon = lon.notna() & ~lon.between(-180, 180)

    valid = (
        ~missing
        & ~non_numeric
        & ~invalid_lat
        & ~invalid_lon
    )

    result["coordinate_rows"] = len(df)
    result["missing_coordinates"] = int(missing.sum())
    result["non_numeric_coordinates"] = int(non_numeric.sum())
    result["invalid_latitude"] = int(invalid_lat.sum())
    result["invalid_longitude"] = int(invalid_lon.sum())
    result["valid_coordinate_rows"] = int(valid.sum())

    return result


def suggest_roles(df, geometry_type):
    """
    Suggest dataset roles from schema clues.

    These are suggestions only.
    Registration still requires user confirmation.
    """

    cols = {
        _normalise_column_name(c)
        for c in df.columns
    }

    roles = {"REFERENCE"}

    # Spatial data can normally be mapped.
    if geometry_type in {
        "POINT",
        "LINE",
        "POLYGON",
        "RASTER",
        "MIXED",
    }:
        roles.add("MAP")

    # Mineral/commodity occurrences may potentially
    # contribute to narrative and ML.
    if cols.intersection(MINERAL_NAMES):
        roles.add("NARRATIVE")
        roles.add("RAG")
        roles.add("ML_LABEL")

    # Lines/faults/lineaments typically become features,
    # not labels.
    if (
        geometry_type == "LINE"
        or "lineament" in cols
        or "fault" in cols
    ):
        roles.add("ML_FEATURE")

    # Numeric scientific measurements are potential features.
    measurement_hints = {
        "elevation",
        "slope",
        "ndvi",
        "iron_oxide",
        "clay",
        "grade",
        "ppm",
        "assay",
        "magnetic",
        "gravity",
    }

    if cols.intersection(measurement_hints):
        roles.add("ML_FEATURE")

    return sorted(roles)


def profile_dataframe(df, filename=None):
    """
    Produce a reusable profile dictionary for a dataframe.
    """

    coords = detect_coordinate_columns(
        df.columns
    )

    geometry_type = detect_geometry_type(df)

    coord_quality = coordinate_quality(
        df,
        coords["lat_column"],
        coords["lon_column"],
    )

    missing = {
        str(col): int(df[col].isna().sum())
        for col in df.columns
    }

    dtypes = {
        str(col): str(df[col].dtype)
        for col in df.columns
    }

    duplicate_rows = int(
        df.duplicated().sum()
    )

    return {
        "filename": filename,
        "row_count": int(len(df)),
        "column_count": int(len(df.columns)),
        "columns": [
            str(c)
            for c in df.columns
        ],
        "dtypes": dtypes,
        "missing_values": missing,
        "duplicate_rows": duplicate_rows,
        "lat_column": coords["lat_column"],
        "lon_column": coords["lon_column"],
        "geometry_type": geometry_type,
        "coordinate_quality": coord_quality,
        "suggested_roles": suggest_roles(
            df,
            geometry_type,
        ),
    }


def profile_csv(path, comment=None):
    """
    Read and profile a CSV from disk.

    `comment` may be supplied for legacy files such as
    training_deposits.csv that contain comment lines.
    """

    path = Path(path)

    if not path.exists():
        raise FileNotFoundError(
            f"Dataset not found: {path}"
        )

    df = pd.read_csv(
        path,
        comment=comment,
    )

    profile = profile_dataframe(
        df,
        filename=path.name,
    )

    return df, profile
