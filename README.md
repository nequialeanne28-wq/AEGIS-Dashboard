# AEGIS Streamlit Dashboard

Deployment-ready Streamlit dashboard for the August 2025 barangay-level rice stem borer records of Norala, South Cotabato.

## Run locally

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Deploy

Upload `app.py`, `norala_barangay.geojson`, and `requirements.txt` to the repository connected to Streamlit Community Cloud, then reboot the app.

## Interpretation

The IPI is a relative monitoring-priority index based on documented report frequency, affected area, and mean damage. It is not a farm-level risk prediction or a statistically confirmed biological hotspot analysis.

Data source: Municipal Agriculture Office, Norala, August 2025. Boundary source: GADM 4.1, WGS 84 (indicative administrative boundary).
