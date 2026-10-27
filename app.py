import pandas as pd
import streamlit as st

from core.data_profiler import profile_dataframe


st.set_page_config(
    page_title="GEOMINE | Data Intelligence",
    page_icon="🌍",
    layout="wide",
)

st.title("GEOMINE")
st.caption("Applied AI • Earth Observation • Data Intelligence • Automation")

st.subheader("Automated Dataset Intelligence")

st.write(
    "Upload a CSV dataset to inspect its structure, "
    "identify data-quality issues, detect geographic coordinates, "
    "and generate suggested dataset classifications."
)

uploaded_file = st.file_uploader(
    "Upload a CSV dataset",
    type=["csv"],
)

if uploaded_file is not None:

    try:
        df = pd.read_csv(uploaded_file)

        profile = profile_dataframe(
            df,
            filename=uploaded_file.name,
        )

        st.success("Dataset analysed successfully.")

        col1, col2, col3, col4 = st.columns(4)

        col1.metric("Records", profile["row_count"])
        col2.metric("Columns", profile["column_count"])
        col3.metric("Duplicate Rows", profile["duplicate_rows"])
        col4.metric("Geometry", profile["geometry_type"])

        st.divider()

        st.subheader("Coordinate Quality")

        quality = profile["coordinate_quality"]

        c1, c2, c3 = st.columns(3)

        c1.metric(
            "Valid Coordinates",
            quality["valid_coordinate_rows"],
        )

        c2.metric(
            "Missing Coordinates",
            quality["missing_coordinates"],
        )

        c3.metric(
            "Nonnumeric Coordinates",
            quality["non_numeric_coordinates"],
        )

        c4, c5 = st.columns(2)

        c4.metric(
            "Invalid Latitude",
            quality["invalid_latitude"],
        )

        c5.metric(
            "Invalid Longitude",
            quality["invalid_longitude"],
        )

        st.caption(
            "Coordinate checks use global latitude/longitude bounds. "
            "They do not verify the actual geographic location or CRS."
        )

        st.divider()

        st.subheader("Detected Coordinate Columns")

        st.write(
            "Latitude:",
            profile["lat_column"] or "Not detected",
        )

        st.write(
            "Longitude:",
            profile["lon_column"] or "Not detected",
        )

        st.divider()

        st.subheader("Missing Values")

        missing_df = pd.DataFrame(
            [
                {
                    "Column": column,
                    "Missing Values": count,
                }
                for column, count in profile["missing_values"].items()
            ]
        )

        st.dataframe(
            missing_df,
            use_container_width=True,
            hide_index=True,
        )

        st.divider()

        st.subheader("Column Information")

        dtype_df = pd.DataFrame(
            [
                {
                    "Column": column,
                    "Detected Type": dtype,
                }
                for column, dtype in profile["dtypes"].items()
            ]
        )

        st.dataframe(
            dtype_df,
            use_container_width=True,
            hide_index=True,
        )

        st.divider()

        st.subheader("Suggested Dataset Roles")

        st.write(", ".join(profile["suggested_roles"]))

        st.info(
            "Dataset roles are automated suggestions, "
            "not verification of scientific suitability. "
            "In particular, ML_LABEL does not mean that "
            "a dataset contains verified training labels."
        )

        st.divider()

        st.subheader("Data Preview")

        st.dataframe(
            df.head(20),
            use_container_width=True,
        )

        st.caption(
            "GEOMINE Portfolio Demonstration | "
            "Automated CSV profiling and coordinate validation"
        )

    except Exception as exc:
        st.error(f"Unable to analyse the CSV: {exc}")

else:
    st.info("Upload a CSV file to begin automated analysis.")