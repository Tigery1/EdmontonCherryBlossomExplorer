import streamlit as st
import pandas as pd
import json
import plotly.graph_objects as go
import os
import requests
from st_keyup import st_keyup

st.set_page_config(layout="wide", page_title="Edmonton Cherry Blossom Navigator", page_icon="🌸")

# --- THEME STYLING ---
st.markdown('''
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Playfair+Display:wght@800&family=Lato:wght@400;700&display=swap');

    header[data-testid="stHeader"]::before {
        content: "";
        position: absolute;
        top: 0; left: 0; width: 100%; height: 8px;
        background-color: #ff69b4;
        z-index: 999;
    }
    .stApp { background-color: #ffcbd1; font-family: 'Lato', sans-serif; } 
    [data-testid="stSidebar"] { display: none; }
    .block-container {
        padding-top: 3rem !important;
        padding-left: 5rem !important;
        padding-right: 5rem !important;
        padding-bottom: 0rem !important;
    }
    /* Collapse gap between header and search */
    [data-testid="stVerticalBlock"] > [data-testid="stVerticalBlock"] {
        gap: 0rem !important;
    }
    div[data-testid="column"] > div { gap: 0 !important; }
    /* Pull search row up under the subtitle */
    [data-testid="stVerticalBlock"] > div:has([data-testid="stCustomComponentV1"]) {
        margin-top: -1.2rem !important;
    }
    /* Collapse keyup iframe wrapper */
    [data-testid="stCustomComponentV1"] {
        min-height: 0 !important;
        margin-top: -0.5rem !important;
        margin-bottom: -0.75rem !important;
    }
    .main-title {
        font-family: 'Playfair Display', serif;
        font-size: 2.4rem !important;
        font-weight: 800;
        color: #70103b;
        margin-bottom: 0rem;
        letter-spacing: -1px;
        text-align: center;
    }
    .sub-title {
        font-family: 'Lato', sans-serif;
        color: #ad1457;
        font-weight: 700;
        font-size: 1.05rem;
        margin-top: -0.3rem;
        margin-bottom: 0rem;
        letter-spacing: 0.5px;
        text-align: center;
    }
    /* Search input */
    [data-testid="stTextInput"] input {
        background: #fff !important;
        border: 1.5px solid #f48fb1 !important;
        border-radius: 10px !important;
        color: #ad1457 !important;
        font-size: 1rem !important;
        font-weight: 600 !important;
        padding: 0.5rem 1rem !important;
        box-shadow: 0 2px 12px rgba(255,105,180,0.12) !important;
    }
    [data-testid="stTextInput"] input::placeholder {
        color: #f48fb1 !important;
        opacity: 1 !important;
        font-weight: 400 !important;
    }
    [data-testid="stTextInput"] input:focus {
        border-color: #c2185b !important;
        box-shadow: 0 3px 16px rgba(194,24,91,0.18) !important;
        outline: none !important;
    }
    /* Suggestion list */
    [data-testid="stRadio"] input[type="radio"] { display: none !important; }
    [data-testid="stRadio"] > div {
        flex-direction: column !important;
        gap: 0 !important;
        background: #fff !important;
        border: 1.5px solid #f48fb1 !important;
        border-radius: 10px !important;
        overflow: hidden !important;
        box-shadow: 0 4px 16px rgba(255,105,180,0.15) !important;
        margin-top: 0.25rem !important;
    }
    [data-testid="stRadio"] label {
        display: flex !important;
        align-items: center !important;
        padding: 0.55rem 1rem !important;
        border-bottom: 1px solid #fce4ec !important;
        border-radius: 0 !important;
        background: #fff !important;
        color: #ad1457 !important;
        font-weight: 600 !important;
        font-size: 0.95rem !important;
        cursor: pointer !important;
        border-left: none !important;
        border-right: none !important;
        border-top: none !important;
    }
    [data-testid="stRadio"] label:last-of-type { border-bottom: none !important; }
    [data-testid="stRadio"] label:hover { background: #fce4ec !important; }
    [data-testid="stRadio"] label:hover * { color: #c2185b !important; }
    [data-testid="stRadio"] label * { color: #ad1457 !important; font-weight: 600 !important; }
    /* Map style buttons — inactive */
    [data-testid="stBaseButton-secondary"] {
        background: #fff !important;
        color: #70103b !important;
        border: 2px solid #c2185b !important;
        border-radius: 6px !important;
        font-weight: 700 !important;
        font-size: 0.68rem !important;
        padding: 0.2rem 0.4rem !important;
        width: 100% !important;
    }
    [data-testid="stBaseButton-secondary"]:hover {
        background: #fce4ec !important;
        color: #70103b !important;
    }
    /* Map style buttons — active */
    [data-testid="stBaseButton-primary"] {
        background: #c2185b !important;
        color: #fff !important;
        border: 2px solid #c2185b !important;
        border-radius: 6px !important;
        font-weight: 700 !important;
        font-size: 0.68rem !important;
        padding: 0.2rem 0.4rem !important;
        width: 100% !important;
    }
    </style>
    ''', unsafe_allow_html=True)

@st.cache_data
def load_data():
    file_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "Trees_Filtered.geojson")
    if not os.path.exists(file_path):
        st.error(f"File not found: {file_path}")
        st.stop()
    with open(file_path, 'r') as f:
        data = json.load(f)

    rows = []
    for feature in data['features']:
        props = feature['properties']
        if feature['geometry']:
            props['longitude'] = feature['geometry']['coordinates'][0]
            props['latitude'] = feature['geometry']['coordinates'][1]
            rows.append(props)

    df = pd.DataFrame(rows)
    df['diameter_breast_height'] = pd.to_numeric(df['diameter_breast_height'], errors='coerce')
    return df[df['diameter_breast_height'] >= 15].dropna(subset=['latitude', 'longitude'])

@st.cache_data(show_spinner=False, ttl=300)
def get_suggestions(query):
    try:
        import re
        base_headers = {"User-Agent": "EdmontonCherryBlossomApp/1.0 contact:mike_baran@shaw.ca"}

        if re.match(r'^\d+', query.strip()):
            # House-number query → structured search (more precise)
            params = {
                "street": query.strip(),
                "city": "Edmonton",
                "state": "Alberta",
                "country": "Canada",
                "format": "json",
                "limit": 4,
                "addressdetails": 1,
            }
        else:
            # Neighbourhood / street-name query → freeform search
            params = {
                "q": f"{query}, Edmonton, Alberta",
                "format": "json",
                "limit": 4,
                "countrycodes": "ca",
                "bounded": 1,
                "viewbox": "-113.72,53.35,-113.27,53.72",
                "addressdetails": 1,
            }

        resp = requests.get(
            "https://nominatim.openstreetmap.org/search",
            params=params,
            headers=base_headers,
            timeout=5
        )
        results = []
        for item in resp.json():
            lat, lon = float(item["lat"]), float(item["lon"])
            addr = item.get("address", {})
            num  = addr.get("house_number", "")
            road = addr.get("road", "")
            hood = addr.get("suburb") or addr.get("neighbourhood") or addr.get("quarter") or ""
            if num and road:
                street = f"{num} {road}"
            elif road:
                # house_number missing from structured data — pull from display_name
                first = item.get("display_name", "").split(",")[0].strip()
                street = first if first[0].isdigit() else road
            else:
                street = item.get("display_name", "").split(",")[0].strip()
            label = f"{street}  ·  {hood}" if hood else street
            if label:
                results.append({"label": label, "lat": lat, "lon": lon})
        return results
    except Exception as e:
        try:
            snippet = resp.text[:120]
        except Exception:
            snippet = "no response"
        return [{"label": f"⚠ {resp.status_code} – {snippet}", "lat": 53.5447, "lon": -113.4901}]


df = load_data()

if "map_center" not in st.session_state:
    st.session_state.map_center = {"lat": 53.5447, "lon": -113.4901}
    st.session_state.map_zoom = 11.0
if "map_style" not in st.session_state:
    st.session_state.map_style = "Street"

_, title_col, style_col = st.columns([1, 5, 1])
with title_col:
    st.markdown('<div class="main-title">🌸 Edmonton Cherry Blossom Navigator</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-title">Exploring Pink &amp; Rose City-Owned Flowering Trees in Alberta\'s Capital</div>', unsafe_allow_html=True)
with style_col:
    for opt in ["Street", "Satellite", "Hybrid"]:
        is_active = st.session_state.map_style == opt
        if st.button(opt, key=f"style_{opt}",
                     type="primary" if is_active else "secondary",
                     use_container_width=True):
            st.session_state.map_style = opt
            st.rerun()
map_style = st.session_state.map_style

_, search_col, _ = st.columns([1, 3, 1])
with search_col:
    if "addr_selected" not in st.session_state:
        st.session_state.addr_selected = False
    if "last_addr" not in st.session_state:
        st.session_state.last_addr = ""

    address_input = st_keyup("", placeholder="🔍  Type a street, neighbourhood or postal code…", debounce=400)

    if address_input != st.session_state.last_addr:
        st.session_state.addr_selected = False
        st.session_state.last_addr = address_input

    if address_input and len(address_input) >= 4 and not st.session_state.addr_selected:
        suggestions = get_suggestions(address_input)
        if suggestions:
            labels = [s["label"] for s in suggestions[:4]]
            choice = st.radio("", labels, index=None, label_visibility="collapsed")
            if choice:
                match = next(s for s in suggestions if s["label"] == choice)
                st.session_state.map_center = {"lat": match["lat"], "lon": match["lon"]}
                st.session_state.map_zoom = 15.0
                st.session_state.addr_selected = True
                st.rerun()

map_center = st.session_state.map_center
map_zoom = st.session_state.map_zoom

ESRI_IMAGERY = "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"
ESRI_LABELS  = "https://server.arcgisonline.com/ArcGIS/rest/services/Reference/World_Boundaries_and_Places/MapServer/tile/{z}/{y}/{x}"

if map_style == "Street":
    mapbox_style = "carto-positron"
    tile_layers = [{"below": "traces", "sourcetype": "raster",
                    "source": ["https://basemaps.cartocdn.com/light_all/{z}/{x}/{y}.png"],
                    "opacity": 0.35}]
elif map_style == "Satellite":
    mapbox_style = "white-bg"
    tile_layers = [{"below": "traces", "sourcetype": "raster",
                    "source": [ESRI_IMAGERY], "opacity": 1.0}]
else:  # Hybrid
    mapbox_style = "white-bg"
    tile_layers = [
        {"below": "traces", "sourcetype": "raster", "source": [ESRI_IMAGERY], "opacity": 1.0},
        {"below": "traces", "sourcetype": "raster", "source": [ESRI_LABELS],  "opacity": 1.0},
    ]

sakura_palette = [
    [0, 'rgba(255, 245, 247, 0)'], 
    [0.15, '#ffdae9'], 
    [0.4, '#ffb6c1'],  
    [0.7, '#ff69b4'],  
    [1.0, '#da1b81']   
]

fig = go.Figure()

fig.add_trace(go.Densitymapbox(
    lat=df["latitude"], lon=df["longitude"], z=[1]*len(df),
    radius=20,
    colorscale=sakura_palette,
    showscale=False,
    opacity=0.85
))

fig.add_trace(go.Scattermapbox(
    lat=df["latitude"], lon=df["longitude"],
    mode='markers', marker=dict(size=15, opacity=0),
    text=df.apply(lambda r: (
        f"<b>{r.get('neighbourhood_name','Edmonton')}</b><br>"
        f"Diameter: {int(round(r['diameter_breast_height']))} cm"
    ), axis=1),
    hoverinfo='text'
))



fig.update_layout(
    mapbox=dict(
        style=mapbox_style,
        center=map_center,
        zoom=map_zoom,
        layers=tile_layers,
    ),
    margin={"r":0,"t":0,"l":0,"b":0},
    height=850,
    paper_bgcolor='rgba(0,0,0,0)',
    plot_bgcolor='rgba(0,0,0,0)',
    hoverlabel=dict(
        bgcolor="white", 
        font_size=18, 
        font_family="Lato", 
        font_color="#70103b", 
        bordercolor="#ff69b4"
    )
)

st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': True, 'scrollZoom': True})

st.markdown(
    '<div style="text-align:center; color:#c2749a; font-size:0.78rem; padding: 0.4rem 0 0.1rem;">'
    'Tree data: <a href="https://data.edmonton.ca" target="_blank" style="color:#c2749a;">City of Edmonton Open Data Portal</a>'
    '</div>'
    '<div style="text-align:center; color:#c2749a; font-size:0.78rem; padding: 0.1rem 0 0.8rem;">© 2026 Mike Baran</div>',
    unsafe_allow_html=True
)
