import json
from pathlib import Path

import folium
import pandas as pd
import plotly.express as px
import streamlit as st
from folium.plugins import Fullscreen, MousePosition
from streamlit_folium import st_folium


st.set_page_config(page_title="AEGIS | Norala", page_icon="🌾", layout="wide")

COLORS = {
    "none": "#f2f2f2",
    "low": "#fee5d9",
    "moderate": "#fcae91",
    "high": "#fb6a4a",
    "very_high": "#cb181d",
}

STATIC_MAPS = {
    "Report Frequency": Path(__file__).with_name("assets") / "report_frequency_map.png",
    "Mean Percentage Damage": Path(__file__).with_name("assets") / "mean_damage_map.png",
    "Infestation Priority Index": Path(__file__).with_name("assets") / "ipi_priority_map.png",
}

st.markdown(
    """
    <style>
    .block-container {padding-top: 1.4rem; padding-bottom: 3rem;}
    .hero {padding: 1.1rem 1.35rem; border-radius: 14px; color: white;
           background: linear-gradient(115deg,#173f2a,#2f7547); margin-bottom: 1rem;}
    .hero h1 {margin:0; font-size:2.1rem}.hero p {margin:.35rem 0 0; opacity:.92}
    .callout {border-left:5px solid #2f7547; background:#f4faf6; padding:1rem;
              border-radius:8px; margin:.7rem 0;}
    .warning {border-left-color:#b7791f; background:#fffaf0;}
    .priority-card {border:1px solid #d8e2da; border-radius:12px; padding:1rem;
                    background:white; min-height:170px;}
    .map-details {border:1px solid #d8e2da; border-radius:12px; padding:1rem;
                  background:#fbfdfb; margin:.6rem 0 1rem;}
    </style>
    """,
    unsafe_allow_html=True,
)


def load_geojson():
    path = Path(__file__).with_name("norala_barangay.geojson")
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def minmax(series):
    positive = series[series > 0]
    result = pd.Series(0.0, index=series.index)
    if len(positive) and positive.max() != positive.min():
        result.loc[positive.index] = (positive - positive.min()) / (positive.max() - positive.min())
    elif len(positive):
        result.loc[positive.index] = 1.0
    return result


def priority_label(value, reported=True):
    if not reported:
        return "No report"
    if value < 0.21:
        return "Low"
    if value < 0.41:
        return "Moderate"
    if value < 0.61:
        return "High"
    return "Very High"


def class_color(value, field):
    if value <= 0:
        return COLORS["none"]
    if field == "Total_Repo":
        limits = (5, 10, 20)
    elif field == "Affected_A":
        limits = (7, 15, 30)
    elif field == "Severity":
        limits = (20, 40, 60)
    else:
        limits = (0.21, 0.41, 0.61)
    if value <= limits[0]:
        return COLORS["low"]
    if value <= limits[1]:
        return COLORS["moderate"]
    if value <= limits[2]:
        return COLORS["high"]
    return COLORS["very_high"]


def legend_html(title, items):
    rows = "".join(
        f'<div style="display:flex;align-items:center;margin:.35rem 0">'
        f'<span style="width:18px;height:18px;background:{color};border:1px solid #777;'
        f'display:inline-block;margin-right:9px"></span>{label}</div>'
        for color, label in items
    )
    return (
        f'<div style="border:1px solid #ccd5ce;border-radius:9px;padding:12px;background:#fff">'
        f'<b>{title}</b>{rows}</div>'
    )


geojson_data = load_geojson()
rows = []
for feature in geojson_data["features"]:
    p = feature["properties"]
    rows.append(
        {
            "Barangay": p["NAME_3"],
            "Report Frequency": float(p.get("Total_Repo", 0) or 0),
            "Affected Area (ha)": float(p.get("Affected_A", 0) or 0),
            "Mean Damage (%)": float(p.get("Severity", 0) or 0),
        }
    )

df = pd.DataFrame(rows)
df["Frequency (normalized)"] = minmax(df["Report Frequency"])
df["Area (normalized)"] = minmax(df["Affected Area (ha)"])
df["Damage (normalized)"] = minmax(df["Mean Damage (%)"])
df["IPI"] = df[["Frequency (normalized)", "Area (normalized)", "Damage (normalized)"]].mean(axis=1)
df.loc[df["Report Frequency"] == 0, "IPI"] = 0
df["Priority"] = [priority_label(v, r > 0) for v, r in zip(df["IPI"], df["Report Frequency"])]
df["IPI Rank"] = df["IPI"].where(df["Report Frequency"] > 0).rank(ascending=False, method="first")

lookup = df.set_index("Barangay").to_dict("index")
for feature in geojson_data["features"]:
    name = feature["properties"]["NAME_3"]
    record = lookup[name]
    feature["properties"].update(
        {
            "Location": "Norala, South Cotabato",
            "IPI": round(record["IPI"], 6),
            "Priority": record["Priority"],
            "IPI_Rank": int(record["IPI Rank"]) if pd.notna(record["IPI Rank"]) else "—",
        }
    )

affected = df[df["Report Frequency"] > 0].copy().sort_values("IPI", ascending=False)


with st.sidebar:
    st.title("🌾 AEGIS")
    st.markdown("**Agricultural Geospatial Intelligence System**")
    st.caption("Norala, South Cotabato | Validated August 2025 MAO reports")
    st.divider()
    st.markdown(
        "AEGIS integrates documented report frequency, affected rice area, and mean damage "
        "into an equally weighted Infestation Priority Index (IPI)."
    )
    st.info(
        "IPI is a relative monitoring-priority score. It is not a forecast, farm-level risk "
        "estimate, or statistically confirmed biological hotspot."
    )
    st.divider()
    st.caption("Infestation data: Municipal Agriculture Office, Norala")
    st.caption("Boundary: GADM 4.1, WGS 84 (indicative)")


st.markdown(
    """
    <div class="hero"><h1>🌾 AEGIS Dashboard</h1>
    <p>Barangay-level spatial decision support for documented rice stem borer monitoring in Norala</p></div>
    """,
    unsafe_allow_html=True,
)

tab_overview, tab_map, tab_decision, tab_validation, tab_data = st.tabs(
    ["Overview", "Spatial Evidence", "Decision Support", "Validation & Robustness", "Data & Methods"]
)


with tab_overview:
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Validated MAO records", f"{int(df['Report Frequency'].sum())}")
    c2.metric("Reported affected area", f"{df['Affected Area (ha)'].sum():.2f} ha")
    c3.metric("Barangays with reports", f"{len(affected)} of {len(df)}")
    c4.metric("Highest monitoring priority", affected.iloc[0]["Barangay"], f"IPI {affected.iloc[0]['IPI']:.3f}")

    st.subheader("What the three indicators show")
    st.markdown(
        "The indicators do not identify exactly the same barangays as having the greatest documented "
        "burden. Simsiman leads in report frequency and affected area, while Matapol records the highest "
        "mean percentage damage. Lapuz also rises in priority because its damage is high despite a much "
        "smaller reported area and fewer reports. Frequency alone therefore does not provide a complete "
        "representation of documented burden. The IPI combines occurrence, spatial extent, and reported "
        "damage to support a more balanced priority decision."
    )

    chart_data = affected.melt(
        id_vars="Barangay",
        value_vars=["Frequency (normalized)", "Area (normalized)", "Damage (normalized)"],
        var_name="Indicator",
        value_name="Normalized value",
    )
    fig = px.bar(
        chart_data,
        x="Barangay",
        y="Normalized value",
        color="Indicator",
        barmode="group",
        title="Normalized Indicator Profiles of Barangays with Reports",
        color_discrete_sequence=["#355f47", "#d39b38", "#b5413e"],
    )
    fig.update_layout(yaxis_range=[0, 1.05], legend_title="")
    st.plotly_chart(fig, width="stretch")

    st.markdown(
        '<div class="callout warning"><b>Interpretation boundary:</b> Zero means no report in the '
        'available August 2025 MAO records. It does not prove the absence of stem borers. Report frequency '
        'may also reflect differences in surveillance, farmer reporting, and documentation intensity.</div>',
        unsafe_allow_html=True,
    )


with tab_map:
    st.header("Spatial Evidence")
    st.markdown(
        "The static maps present the principal barangay-level GIS outputs prepared for the study. "
        "The interactive map below allows users to compare indicators and inspect individual barangays."
    )

    static_choice = st.radio(
        "Static research map",
        list(STATIC_MAPS),
        horizontal=True,
        key="static_spatial_map",
    )
    static_captions = {
        "Report Frequency": "Barangay distribution of documented rice stem borer reports.",
        "Mean Percentage Damage": "Barangay distribution of reported mean percentage damage.",
        "Infestation Priority Index": "Combined barangay monitoring priorities based on the IPI.",
    }
    st.image(
        str(STATIC_MAPS[static_choice]),
        caption=static_captions[static_choice],
        use_container_width=True,
    )
    st.caption(
        "Static maps are barangay-level summaries. White areas indicate no documented report in the "
        "available dataset and do not confirm absence of rice stem borer infestation."
    )

    st.divider()
    st.subheader("Interactive Barangay-Level Thematic Map")
    control_1, control_2, control_3 = st.columns(3)
    indicator = control_1.selectbox(
        "Indicator",
        ["Infestation Priority Index", "Report Frequency", "Affected Area (ha)", "Mean Damage (%)"],
        key="interactive_indicator",
    )
    selected_barangay = control_2.selectbox(
        "Barangay profile",
        ["All barangays"] + sorted(df["Barangay"].tolist()),
        key="interactive_barangay",
    )
    map_extent = control_3.selectbox(
        "Map extent",
        ["Norala barangays", "Municipal context"],
        help="Municipal context displays neighboring municipalities for geographic reference.",
        key="interactive_map_extent",
    )
    field_map = {
        "Infestation Priority Index": "IPI",
        "Report Frequency": "Total_Repo",
        "Affected Area (ha)": "Affected_A",
        "Mean Damage (%)": "Severity",
    }
    selected_field = field_map[indicator]
    legends = {
        "Report Frequency": (
            "Number of documented reports",
            [(COLORS["none"], "No report (0)"), (COLORS["low"], "Low (1–5)"),
             (COLORS["moderate"], "Moderate (6–10)"), (COLORS["high"], "High (11–20)"),
             (COLORS["very_high"], "Very High (21–40)")],
        ),
        "Affected Area (ha)": (
            "Total reported affected area (ha)",
            [(COLORS["none"], "No report"), (COLORS["low"], "Low (0.01–7.00 ha)"),
             (COLORS["moderate"], "Moderate (7.01–15.00 ha)"),
             (COLORS["high"], "High (15.01–30.00 ha)"),
             (COLORS["very_high"], "Very High (30.01–61.10 ha)")],
        ),
        "Mean Damage (%)": (
            "Mean reported damage (%)",
            [(COLORS["none"], "No report"), (COLORS["low"], "0.01–20.00%"),
             (COLORS["moderate"], "20.01–40.00%"), (COLORS["high"], "40.01–60.00%"),
             (COLORS["very_high"], "60.01–80.00%")],
        ),
        "Infestation Priority Index": (
            "Relative monitoring priority (IPI)",
            [(COLORS["none"], "No report"), (COLORS["low"], "Low (0.000–<0.210)"),
             (COLORS["moderate"], "Moderate (0.210–<0.410)"),
             (COLORS["high"], "High (0.410–<0.610)"),
             (COLORS["very_high"], "Very High (0.610–1.000)")],
        ),
    }
    title, items = legends[indicator]
    st.markdown(legend_html(title, items), unsafe_allow_html=True)

    # OpenStreetMap supplies municipal labels, roads, and surrounding geographic context
    # without requiring an API key. Its required attribution remains visible.
    map_obj = folium.Map(
        location=[6.52, 124.65],
        zoom_start=11,
        tiles="OpenStreetMap",
        attribution_control=True,
        control_scale=True,
    )
    Fullscreen(
        position="topleft",
        title="Open full-screen map",
        title_cancel="Exit full-screen map",
        force_separate_button=True,
    ).add_to(map_obj)
    MousePosition(
        position="bottomright",
        separator=" | ",
        prefix="Coordinates:",
        empty_string="Move pointer over map",
        num_digits=5,
    ).add_to(map_obj)

    # Mask labels embedded in the basemap within Norala. The AEGIS layer below
    # supplies its own barangay names from the research boundary dataset.
    folium.GeoJson(
        geojson_data,
        name="Norala label mask",
        style_function=lambda _: {
            "fillColor": "#ffffff",
            "color": "#ffffff",
            "weight": 0,
            "fillOpacity": 1.0,
        },
        interactive=False,
        control=False,
    ).add_to(map_obj)

    def style_function(feature):
        value = float(feature["properties"].get(selected_field, 0) or 0)
        return {"fillColor": class_color(value, selected_field), "color": "#20262e", "weight": 1.35, "fillOpacity": 0.62}

    geojson_layer = folium.GeoJson(
        geojson_data,
        name=indicator,
        style_function=style_function,
        highlight_function=lambda _: {"weight": 3, "color": "#111", "fillOpacity": 0.80},
        tooltip=folium.GeoJsonTooltip(
            fields=["NAME_3", "Total_Repo", "Affected_A", "Severity", "IPI", "Priority", "IPI_Rank"],
            aliases=["Barangay:", "Reports:", "Affected area (ha):", "Mean damage (%):", "IPI:", "Priority:", "IPI rank:"],
            sticky=True,
        ),
        popup=folium.GeoJsonPopup(
            fields=["NAME_3", "Location", "Total_Repo", "Affected_A", "Severity", "IPI", "Priority", "IPI_Rank"],
            aliases=["Barangay", "Municipality and province", "Reports", "Affected area (ha)", "Mean damage (%)", "IPI", "Priority", "IPI rank"],
            localize=True,
            labels=True,
            style="background-color: white;",
        ),
    )
    geojson_layer.add_to(map_obj)

    def feature_coordinates(node):
        if (
            isinstance(node, list)
            and len(node) >= 2
            and isinstance(node[0], (int, float))
            and isinstance(node[1], (int, float))
        ):
            return [(float(node[0]), float(node[1]))]
        points = []
        if isinstance(node, list):
            for child in node:
                points.extend(feature_coordinates(child))
        return points

    if map_extent == "Norala barangays":
        for feature in geojson_data["features"]:
            points = feature_coordinates(feature["geometry"]["coordinates"])
            if not points:
                continue
            min_lon = min(point[0] for point in points)
            max_lon = max(point[0] for point in points)
            min_lat = min(point[1] for point in points)
            max_lat = max(point[1] for point in points)
            properties = feature["properties"]
            name = properties["NAME_3"]
            value_line = (
                f'<br><span style="font-size:0.9em;font-weight:600">{float(properties["IPI"]):.3f}</span>'
                if indicator == "Infestation Priority Index"
                else ""
            )
            folium.Marker(
                location=[(min_lat + max_lat) / 2, (min_lon + max_lon) / 2],
                icon=folium.DivIcon(
                    icon_size=(110, 32),
                    icon_anchor=(55, 16),
                    html=(
                        f'<div style="width:110px;text-align:center;white-space:nowrap;'
                        f'font-size:11px;font-weight:800;color:#17202a;line-height:1.05;'
                        f'text-shadow:-1px -1px 0 #fff,1px -1px 0 #fff,-1px 1px 0 #fff,'
                        f'1px 1px 0 #fff">{name}{value_line}</div>'
                    ),
                ),
                tooltip=f"{name}: IPI {float(properties['IPI']):.3f}",
            ).add_to(map_obj)

    map_center = [6.5262, 124.6784]
    map_zoom = 10 if map_extent == "Municipal context" else 12
    st_folium(
        map_obj,
        center=map_center,
        zoom=map_zoom,
        height=610,
        use_container_width=True,
        key=f"interactive_map_v5_{selected_field}_{selected_barangay}_{map_extent}",
        returned_objects=["last_object_clicked", "last_object_clicked_popup"],
    )

    if selected_barangay != "All barangays":
        profile = df.loc[df["Barangay"] == selected_barangay].iloc[0]
        rank_text = int(profile["IPI Rank"]) if pd.notna(profile["IPI Rank"]) else "—"
        st.markdown(
            f'<div class="map-details"><b>{selected_barangay}</b><br>'
            f'Reports: {int(profile["Report Frequency"])} &nbsp;|&nbsp; '
            f'Affected area: {profile["Affected Area (ha)"]:.2f} ha &nbsp;|&nbsp; '
            f'Mean damage: {profile["Mean Damage (%)"]:.2f}%<br>'
            f'IPI: {profile["IPI"]:.3f} &nbsp;|&nbsp; Priority: {profile["Priority"]} &nbsp;|&nbsp; '
            f'Rank: {rank_text}</div>',
            unsafe_allow_html=True,
        )
    else:
        st.info("Click a barangay polygon to open its map popup, or select a barangay above for a persistent profile.")
    st.caption(
        "The map displays relative barangay-level monitoring priorities from available August 2025 MAO reports. "
        "Names inside Norala follow the AEGIS research boundary layer; OpenStreetMap is used only for surrounding geographic context. "
        "Neighboring municipalities are displayed only as geographic context and have no AEGIS infestation values. "
        "The map must not be interpreted as a farm-level infestation map or a statistically confirmed biological hotspot map."
    )


with tab_decision:
    st.header("Monitoring Prioritization and Field-Assessment Support")
    st.markdown(
        "The priority ranking is intended to guide the sequence and intensity of follow-up monitoring. "
        "It does not automatically prescribe pesticide application or confirm present infestation."
    )

    top_cols = st.columns(4)
    for column, (_, row) in zip(top_cols, affected.head(4).iterrows()):
        with column:
            st.markdown(
                f'<div class="priority-card"><b>Rank {int(row["IPI Rank"])} · {row["Barangay"]}</b><br>'
                f'<span style="color:#8b1a1a;font-weight:700">{row["Priority"]} priority</span><br><br>'
                f'IPI: {row["IPI"]:.3f}<br>Reports: {int(row["Report Frequency"])}<br>'
                f'Area: {row["Affected Area (ha)"]:.2f} ha<br>Damage: {row["Mean Damage (%)"]:.2f}%</div>',
                unsafe_allow_html=True,
            )

    st.subheader("Recommended operational sequence")
    action_rows = []
    for _, row in affected.iterrows():
        if row["Priority"] == "Very High":
            action = "First field-assessment tier; verify present conditions and coordinate rapid follow-up."
        elif row["Priority"] == "High":
            action = "Second field-assessment tier; schedule close monitoring after very-high-priority sites."
        elif row["Priority"] == "Moderate":
            action = "Targeted follow-up; review report locations and assess representative rice areas."
        else:
            action = "Routine follow-up; maintain surveillance and improve reporting coverage."
        action_rows.append(
            {"Rank": int(row["IPI Rank"]), "Barangay": row["Barangay"], "IPI": round(row["IPI"], 3),
             "Priority": row["Priority"], "Suggested monitoring action": action}
        )
    st.dataframe(pd.DataFrame(action_rows), hide_index=True, width="stretch")

    st.subheader("Resource-allocation scenario")
    available_visits = st.slider("Available barangay field visits", 1, len(affected), 4)
    allocation = affected.head(available_visits)[["IPI Rank", "Barangay", "IPI", "Priority"]].copy()
    allocation["Proposed sequence"] = range(1, len(allocation) + 1)
    allocation["Purpose"] = "Field verification, current-condition assessment, and monitoring coordination"
    st.dataframe(allocation, hide_index=True, width="stretch")
    st.caption(
        "This scenario allocates visits by relative IPI rank. Final deployment should also consider crop stage, "
        "travel time, current farmer reports, personnel, and MAO judgment."
    )

    st.subheader("Custom priority scenario")
    w1, w2, w3 = st.columns(3)
    frequency_weight = w1.slider("Frequency weight", 0, 100, 33)
    area_weight = w2.slider("Affected-area weight", 0, 100, 33)
    damage_weight = w3.slider("Damage weight", 0, 100, 34)
    total_weight = frequency_weight + area_weight + damage_weight
    if total_weight == 0:
        st.warning("Set at least one weight above zero.")
    else:
        scenario = affected.copy()
        scenario["Scenario IPI"] = (
            scenario["Frequency (normalized)"] * frequency_weight
            + scenario["Area (normalized)"] * area_weight
            + scenario["Damage (normalized)"] * damage_weight
        ) / total_weight
        scenario["Scenario Rank"] = scenario["Scenario IPI"].rank(ascending=False, method="first").astype(int)
        scenario["Rank Change"] = scenario["IPI Rank"].astype(int) - scenario["Scenario Rank"]
        st.dataframe(
            scenario.sort_values("Scenario Rank")[["Barangay", "IPI Rank", "Scenario Rank", "Rank Change", "Scenario IPI"]],
            hide_index=True,
            width="stretch",
        )


with tab_validation:
    st.header("Validation and Ranking Robustness")
    st.subheader("Record-validation summary")
    validation = pd.DataFrame(
        [
            ["Original MAO records", 87, "Received for screening"],
            ["Duplicate screening", 0, "No duplicate records removed"],
            ["Missing-data screening", 0, "No critical values removed"],
            ["Barangay-name standardization", 14, "Boundary names matched using standardized labels"],
            ["Range and validity screening", 0, "No out-of-range records removed"],
            ["Final analytical dataset", 87, "100% retained"],
        ],
        columns=["Validation stage", "Result", "Interpretation"],
    )
    st.dataframe(validation, hide_index=True, width="stretch")

    st.subheader("Frequency-only ranking versus integrated IPI ranking")
    comparison = affected[["Barangay", "Report Frequency", "IPI Rank"]].copy()
    comparison["Frequency Rank"] = comparison["Report Frequency"].rank(ascending=False, method="min").astype(int)
    comparison["Rank Change"] = comparison["Frequency Rank"] - comparison["IPI Rank"].astype(int)
    st.dataframe(
        comparison.sort_values("IPI Rank")[["Barangay", "Frequency Rank", "IPI Rank", "Rank Change"]],
        hide_index=True,
        width="stretch",
    )
    stat_table = pd.DataFrame(
        [
            ["Spearman's ρ", 0.398, 0.329, "Weak-to-moderate positive agreement; not statistically significant"],
            ["Kendall's τb", 0.296, 0.315, "Weak positive ordinal agreement; not statistically significant"],
        ],
        columns=["Statistic", "Coefficient", "p-value", "Interpretation"],
    )
    st.dataframe(stat_table, hide_index=True, width="stretch")
    st.caption("Rank-agreement tests use the eight barangays with documented reports (n = 8).")

    st.subheader("Ablation analysis")
    ablation = pd.DataFrame(
        [
            ["Simsiman", 1, 1, 1, 1], ["Matapol", 2, 2, 2, 2],
            ["Lapuz", 3, 3, 3, 7], ["Puti", 4, 4, 4, 5],
            ["Poblacion", 5, 6, 6, 3], ["BS Aquino Jr.", 6, 5, 5, 8],
            ["Kibid", 7, 7, 7, 4], ["Esperanza", 8, 8, 8, 6],
        ],
        columns=["Barangay", "Full IPI Rank", "Without Frequency", "Without Area", "Without Damage"],
    )
    st.dataframe(ablation, hide_index=True, width="stretch")
    st.markdown(
        "Simsiman and Matapol remain first and second under every ablation condition, indicating stable "
        "top-priority identification. Removing damage produces the largest lower-rank changes, especially "
        "for Lapuz, showing that damage contributes information not captured by frequency and area alone."
    )

    st.subheader("Alternative-weight sensitivity")
    sensitivity = pd.DataFrame(
        [
            ["Simsiman", 1, 1, 1, 1], ["Matapol", 2, 2, 2, 2], ["Lapuz", 3, 3, 3, 3],
            ["Puti", 4, 4, 4, 4], ["Poblacion", 5, 7, 6, 5], ["BS Aquino Jr.", 6, 5, 5, 6],
            ["Kibid", 7, 6, 7, 7], ["Esperanza", 8, 8, 8, 8],
        ],
        columns=["Barangay", "Equal weights", "Frequency emphasis", "Area emphasis", "Damage emphasis"],
    )
    st.dataframe(sensitivity, hide_index=True, width="stretch")
    st.success(
        "Overall ranking robustness is strongest for the first four and last positions. Middle-priority "
        "barangays show limited movement when one indicator receives greater weight, so operational decisions "
        "near category boundaries should be supported by current field information."
    )

    st.subheader("Dashboard evaluation status")
    st.info(
        "The ISO/IEC 25010 evaluation sheet contains no completed respondent ratings yet. Software-quality "
        "results should remain marked as pending until expert or user evaluations are collected; no evaluation "
        "score is fabricated in this dashboard."
    )


with tab_data:
    st.header("Data, Method, and Information Dissemination")
    st.subheader("Barangay dataset")
    display_df = df[["Barangay", "Report Frequency", "Affected Area (ha)", "Mean Damage (%)", "IPI", "Priority", "IPI Rank"]].copy()
    display_df["Report Frequency"] = display_df["Report Frequency"].astype(int)
    display_df["IPI"] = display_df["IPI"].round(3)
    display_df["IPI Rank"] = display_df["IPI Rank"].astype("Int64")
    st.dataframe(display_df.sort_values(["IPI", "Barangay"], ascending=[False, True]), hide_index=True, width="stretch")
    st.download_button(
        "Download barangay summary (CSV)",
        data=display_df.to_csv(index=False).encode("utf-8"),
        file_name="aegis_barangay_summary_august_2025.csv",
        mime="text/csv",
    )

    st.subheader("Index construction")
    st.latex(r"IPI_b = \frac{F'_b + A'_b + D'_b}{3}")
    st.markdown(
        "For barangays with reports, each indicator is transformed through min–max normalization using the "
        "reported-barangay minimum and maximum. Equal weighting preserves transparency and prevents any one "
        "indicator from defining documented burden by itself. Barangays without reports are displayed separately."
    )

    st.subheader("Responsible interpretation")
    st.markdown(
        "- **Monitoring prioritization:** use the IPI to organize which barangays receive earlier follow-up.\n"
        "- **Resource allocation:** combine the ranking with crop stage, access, staffing, and recent information.\n"
        "- **Field-assessment support:** confirm current conditions within barangays before management action.\n"
        "- **Information dissemination:** share barangay summaries while clearly stating their temporal and spatial limits."
    )
    st.warning(
        "The records were documented for insurance assessment during the August 2025 whitehead stage and are "
        "aggregated by barangay. The dashboard does not locate individual farms, predict future infestation, or "
        "prove pest absence in barangays with no report."
    )

st.divider()
st.caption(
    "Infestation source: Municipal Agriculture Office, Norala, August 2025. Boundary source: GADM 4.1 "
    "(indicative administrative boundaries), WGS 84. AEGIS supports monitoring decisions and does not replace field assessment."
)
