import pandas as pd

from core.data_profiler import profile_dataframe


def test_profiler_runs():
    df = pd.DataFrame({
        "latitude": [7.5, 8.2, None],
        "longitude": [5.1, 6.3, 7.2],
        "mineral": ["Gold", "Lithium", "Gold"],
    })

    result = profile_dataframe(df, filename="sample.csv")

    assert isinstance(result, dict)
    assert result["row_count"] == 3
    assert result["column_count"] == 3
    assert result["geometry_type"] == "POINT"


def test_coordinate_quality_categories():
    df = pd.DataFrame({
        "latitude": [
            7.5,
            None,
            8.2,
            95.0,
            7.1,
            6.5,
        ],
        "longitude": [
            5.1,
            6.2,
            "unknown",
            5.5,
            200.0,
            4.3,
        ],
    })

    result = profile_dataframe(df, filename="coordinates.csv")

    quality = result["coordinate_quality"]

    assert quality["coordinate_rows"] == 6
    assert quality["missing_coordinates"] == 1
    assert quality["non_numeric_coordinates"] == 1
    assert quality["invalid_latitude"] == 1
    assert quality["invalid_longitude"] == 1
    assert quality["valid_coordinate_rows"] == 2


def test_original_data_is_preserved():
    df = pd.DataFrame({
        "latitude": [7.5, 8.2],
        "longitude": ["unknown", "6.30"],
    })

    original = df.copy(deep=True)

    profile_dataframe(df, filename="preservation.csv")

    pd.testing.assert_frame_equal(df, original)