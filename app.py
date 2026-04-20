import altair as alt
import folium
import json
import math
import ssl
from pathlib import Path
from urllib.error import URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

import pandas as pd
import streamlit as st
from streamlit_folium import st_folium


st.set_page_config(page_title="Vie Etudiante Paris - MVP", layout="wide")

st.title("Dashboard Vie Etudiante - Region parisienne (MVP)")
st.caption("Classement dynamique, note finale /100, comparaison multicriteres.")

# Donnees MVP (scores de demonstration en attendant les APIs reelles)
universities = pd.DataFrame(
    [
        {"university": "Universite PSL", "lat": 48.848, "lon": 2.343, "housing": 54, "transport": 92, "food": 78, "green": 63, "social_life": 86, "student_reviews": 80, "url": "https://psl.eu"},
        {"university": "Sorbonne Universite", "lat": 48.847, "lon": 2.355, "housing": 57, "transport": 91, "food": 76, "green": 58, "social_life": 84, "student_reviews": 78, "url": "https://www.sorbonne-universite.fr"},
        {"university": "Universite Paris-Saclay", "lat": 48.711, "lon": 2.165, "housing": 67, "transport": 70, "food": 64, "green": 84, "social_life": 60, "student_reviews": 71, "url": "https://www.universite-paris-saclay.fr"},
        {"university": "Universite Paris Cite", "lat": 48.841, "lon": 2.337, "housing": 53, "transport": 89, "food": 74, "green": 61, "social_life": 81, "student_reviews": 75, "url": "https://u-paris.fr"},
        {"university": "Universite Paris 1 Pantheon-Sorbonne", "lat": 48.847, "lon": 2.341, "housing": 52, "transport": 90, "food": 75, "green": 56, "social_life": 83, "student_reviews": 76, "url": "https://www.pantheonsorbonne.fr"},
        {"university": "Universite Paris-Pantheon-Assas", "lat": 48.846, "lon": 2.338, "housing": 51, "transport": 89, "food": 73, "green": 57, "social_life": 82, "student_reviews": 75, "url": "https://www.u-paris2.fr"},
        {"university": "Universite Paris Est Creteil", "lat": 48.79, "lon": 2.455, "housing": 71, "transport": 77, "food": 68, "green": 74, "social_life": 66, "student_reviews": 70, "url": "https://www.u-pec.fr"},
        {"university": "Universite Paris Nanterre", "lat": 48.904, "lon": 2.214, "housing": 65, "transport": 83, "food": 69, "green": 72, "social_life": 68, "student_reviews": 72, "url": "https://www.parisnanterre.fr"},
        {"university": "Sorbonne Nouvelle", "lat": 48.838, "lon": 2.351, "housing": 55, "transport": 88, "food": 74, "green": 60, "social_life": 82, "student_reviews": 76, "url": "https://www.sorbonne-nouvelle.fr"},
        {"university": "Universite Sorbonne Paris Nord", "lat": 48.944, "lon": 2.364, "housing": 72, "transport": 79, "food": 67, "green": 69, "social_life": 64, "student_reviews": 69, "url": "https://www.univ-spn.fr"},
    ]
)

criteria_labels = {
    "housing": "Logement",
    "transport": "Transport",
    "food": "Food (courses, crous, alimentation)",
    "green": "Espaces verts",
    "social_life": "Vie sociale (restaurants, bars, activites)",
}

RADIUS_TO_KM = {"1 km": 1.0, "2.5 km": 2.5, "5 km": 5.0}
RADIUS_TO_METERS = {"1 km": 1000, "2.5 km": 2500, "5 km": 5000}
ANALYSIS_MIN_ZOOM = 10
LOCAL_CONFIG_PATH = Path(__file__).resolve().parent / ".streamlit" / "local_config.json"

POI_CATEGORY_CONFIG = {
    "transport": {
        "label": "Transport",
        "symbol": "T",
        "color": "#1f4e79",
        "types": [
            "subway_station",
            "train_station",
            "bus_station",
            "transit_station",
            "taxi_stand",
            "airport",
            "ferry_terminal",
            "parking",
            "car_rental",
        ],
    },
    "restauration": {
        "label": "Restauration",
        "symbol": "★",
        "color": "#f6c026",
        "types": [
            "restaurant",
            "bar",
            "cafe",
            "bakery",
            "meal_delivery",
            "meal_takeaway",
            "night_club",
        ],
    },
    "espaces_verts": {
        "label": "Espaces verts / nature",
        "symbol": "■",
        "color": "#2f8f3a",
        "types": [
            "park",
            "campground",
            "rv_park",
            "natural_feature",
            "tourist_attraction",
        ],
    },
    "food_courses": {
        "label": "Food / courses",
        "symbol": "◆",
        "color": "#ef8a17",
        "types": [
            "supermarket",
            "grocery_or_supermarket",
            "convenience_store",
            "department_store",
            "store",
        ],
    },
    "activites": {
        "label": "Activites",
        "symbol": "▲",
        "color": "#f06292",
        "types": [
            "museum",
            "art_gallery",
            "tourist_attraction",
            "stadium",
            "gym",
            "movie_theater",
            "bowling_alley",
            "amusement_park",
            "casino",
            "church",
            "mosque",
            "hindu_temple",
            "synagogue",
        ],
    },
}


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    earth_radius_km = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(math.radians(lat1))
        * math.cos(math.radians(lat2))
        * math.sin(dlon / 2) ** 2
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return earth_radius_km * c


def fetch_json(url: str, timeout_sec: int = 12) -> dict:
    req = Request(url, headers={"User-Agent": "student-life-dashboard-mvp/1.0"})
    try:
        with urlopen(req, timeout=timeout_sec) as response:
            return json.loads(response.read().decode("utf-8"))
    except Exception:
        # Fallback utile sur certaines machines avec certificats locaux incomplets.
        insecure_ctx = ssl._create_unverified_context()
        with urlopen(req, timeout=timeout_sec, context=insecure_ctx) as response:
            return json.loads(response.read().decode("utf-8"))


@st.cache_data(ttl=86400, show_spinner=False)
def fetch_crous_points() -> pd.DataFrame:
    # Endpoint Opendatasoft public du MESR (lieux de restauration CROUS).
    url = (
        "https://data.enseignementsup-recherche.gouv.fr/api/explore/v2.1/catalog/datasets/"
        "fr_crous_restauration_france_entiere/records?limit=100"
    )
    payload = fetch_json(url, timeout_sec=12)
    records = payload.get("results", [])
    if not records:
        return pd.DataFrame(columns=["name", "lat", "lon", "city"])

    rows = []
    for record in records:
        if not isinstance(record, dict):
            continue
        geo = record.get("geo_point_2d") or {}
        lat = geo.get("lat")
        lon = geo.get("lon")
        if lat is None or lon is None:
            lat = record.get("latitude")
            lon = record.get("longitude")
        if lat is None or lon is None:
            continue
        city = (record.get("commune") or record.get("ville") or "").strip()
        rows.append(
            {
                "name": record.get("libelle") or record.get("nom") or "Point CROUS",
                "lat": float(lat),
                "lon": float(lon),
                "city": city,
            }
        )
    return pd.DataFrame(rows)


def compute_crous_food_adjustment(
    uni_df: pd.DataFrame, crous_df: pd.DataFrame, selected_radius_km: float
) -> pd.Series:
    if crous_df.empty:
        return pd.Series([0] * len(uni_df), index=uni_df.index, dtype=float)
    boosts = []
    for _, uni in uni_df.iterrows():
        nearby = 0
        for _, crous in crous_df.iterrows():
            distance = haversine_km(uni["lat"], uni["lon"], crous["lat"], crous["lon"])
            if distance <= selected_radius_km:
                nearby += 1
        # Cap a +15 points pour garder un score food stable.
        boost = min(15, nearby * 4)
        boosts.append(boost)
    return pd.Series(boosts, index=uni_df.index, dtype=float)


@st.cache_data(ttl=21600, show_spinner=False)
def fetch_google_places_summary(
    lat: float, lon: float, radius_m: int, place_type: str, api_key: str
) -> tuple[float, int]:
    params = urlencode(
        {
            "location": f"{lat},{lon}",
            "radius": radius_m,
            "type": place_type,
            "key": api_key,
        }
    )
    url = f"https://maps.googleapis.com/maps/api/place/nearbysearch/json?{params}"
    payload = fetch_json(url, timeout_sec=14)
    if payload.get("status") not in {"OK", "ZERO_RESULTS"}:
        raise ValueError(payload.get("error_message", payload.get("status", "Google Places error")))

    ratings = []
    total_reviews = 0
    for item in payload.get("results", []):
        rating = item.get("rating")
        if rating is not None:
            ratings.append(float(rating))
        total_reviews += int(item.get("user_ratings_total", 0) or 0)
    avg_rating = sum(ratings) / len(ratings) if ratings else 0.0
    return avg_rating, total_reviews


@st.cache_data(ttl=21600, show_spinner=False)
def fetch_google_place_reviews(
    lat: float, lon: float, radius_m: int, api_key: str, limit_places: int = 5
) -> list[str]:
    params = urlencode(
        {
            "location": f"{lat},{lon}",
            "radius": radius_m,
            "type": "restaurant",
            "key": api_key,
        }
    )
    nearby_url = f"https://maps.googleapis.com/maps/api/place/nearbysearch/json?{params}"
    nearby_payload = fetch_json(nearby_url, timeout_sec=14)
    if nearby_payload.get("status") not in {"OK", "ZERO_RESULTS"}:
        return []

    comments = []
    for item in nearby_payload.get("results", [])[:limit_places]:
        place_id = item.get("place_id")
        if not place_id:
            continue
        details_params = urlencode(
            {
                "place_id": place_id,
                "fields": "name,reviews",
                "reviews_sort": "newest",
                "key": api_key,
            }
        )
        details_url = f"https://maps.googleapis.com/maps/api/place/details/json?{details_params}"
        details_payload = fetch_json(details_url, timeout_sec=14)
        result = details_payload.get("result", {})
        place_name = result.get("name", "Lieu")
        for review in result.get("reviews", [])[:1]:
            text = (review.get("text") or "").strip()
            if text:
                comments.append(f"{place_name}: {text[:180]}")
    return comments[:8]


def score_from_google(avg_rating: float, total_reviews: int, density_divider: int = 60) -> float:
    rating_score = max(0, min(100, avg_rating * 20))
    density_score = max(0, min(100, (total_reviews / density_divider) * 100))
    return round(0.7 * rating_score + 0.3 * density_score, 1)


def load_local_google_api_key() -> str:
    if not LOCAL_CONFIG_PATH.exists():
        return ""
    try:
        payload = json.loads(LOCAL_CONFIG_PATH.read_text(encoding="utf-8"))
        return str(payload.get("google_api_key", "")).strip()
    except Exception:
        return ""


def save_local_google_api_key(api_key: str) -> None:
    LOCAL_CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    payload = {"google_api_key": api_key.strip()}
    LOCAL_CONFIG_PATH.write_text(json.dumps(payload, ensure_ascii=True, indent=2), encoding="utf-8")


def normalize_place_record(place: dict, category_key: str) -> dict | None:
    geometry = place.get("geometry", {}).get("location", {})
    lat = geometry.get("lat")
    lon = geometry.get("lng")
    if lat is None or lon is None:
        return None
    rating = place.get("rating")
    user_ratings_total = place.get("user_ratings_total")
    place_id = place.get("place_id", "")
    return {
        "category_key": category_key,
        "category_label": POI_CATEGORY_CONFIG[category_key]["label"],
        "symbol": POI_CATEGORY_CONFIG[category_key]["symbol"],
        "color": POI_CATEGORY_CONFIG[category_key]["color"],
        "name": place.get("name", "Lieu sans nom"),
        "rating": float(rating) if rating is not None else None,
        "reviews_count": int(user_ratings_total) if user_ratings_total is not None else None,
        "lat": float(lat),
        "lon": float(lon),
        "place_id": place_id,
        "external_link": f"https://www.google.com/maps/place/?q=place_id:{place_id}" if place_id else "",
    }


@st.cache_data(ttl=3600, show_spinner=False)
def fetch_analysis_pois(lat: float, lon: float, radius_m: int, api_key: str) -> pd.DataFrame:
    poi_rows = []
    seen_place_ids = set()
    for category_key, cfg in POI_CATEGORY_CONFIG.items():
        for place_type in cfg["types"]:
            params = urlencode(
                {
                    "location": f"{lat},{lon}",
                    "radius": radius_m,
                    "type": place_type,
                    "key": api_key,
                }
            )
            url = f"https://maps.googleapis.com/maps/api/place/nearbysearch/json?{params}"
            payload = fetch_json(url, timeout_sec=16)
            status = payload.get("status")
            if status not in {"OK", "ZERO_RESULTS"}:
                continue
            for place in payload.get("results", []):
                normalized = normalize_place_record(place, category_key)
                if not normalized:
                    continue
                pid = normalized["place_id"] or f"{normalized['name']}-{normalized['lat']}-{normalized['lon']}"
                if pid in seen_place_ids:
                    continue
                if haversine_km(lat, lon, normalized["lat"], normalized["lon"]) <= radius_m / 1000:
                    seen_place_ids.add(pid)
                    poi_rows.append(normalized)
    if not poi_rows:
        return pd.DataFrame(
            columns=[
                "category_key",
                "category_label",
                "symbol",
                "color",
                "name",
                "rating",
                "reviews_count",
                "lat",
                "lon",
                "place_id",
                "external_link",
            ]
        )
    return pd.DataFrame(poi_rows)

st.sidebar.header("Parametres")

if "weight_objective" not in st.session_state:
    st.session_state["weight_objective"] = 0.8
if "criterion_raw_weights" not in st.session_state:
    st.session_state["criterion_raw_weights"] = {}
if "google_api_key_input" not in st.session_state:
    st.session_state["google_api_key_input"] = load_local_google_api_key()

selected_universities = st.sidebar.multiselect(
    "Universites a comparer",
    options=universities["university"].tolist(),
    default=universities["university"].tolist(),
)
radius = st.sidebar.selectbox("Rayon d'analyse", ["1 km", "2.5 km", "5 km"], index=1)
radius_km = RADIUS_TO_KM[radius]

active_criteria = st.sidebar.multiselect(
    "Criteres utilises pour le classement",
    options=list(criteria_labels.keys()),
    default=list(criteria_labels.keys()),
    format_func=lambda x: criteria_labels[x],
)

weight_objective = st.sidebar.slider(
    "Poids donnees objectives",
    0.5,
    0.95,
    float(st.session_state["weight_objective"]),
    0.05,
)
st.session_state["weight_objective"] = weight_objective
weight_subjective = round(1 - weight_objective, 2)

use_crous_api = st.sidebar.toggle("Activer donnees CROUS (API)", value=True)
use_google_api = st.sidebar.toggle("Activer Google Places API", value=False)
google_api_key = ""
if use_google_api:
    google_api_key = st.sidebar.text_input(
        "Google Places API key",
        type="password",
        key="google_api_key_input",
    ).strip()
    k1, k2 = st.sidebar.columns(2)
    if k1.button("Enregistrer cle"):
        if google_api_key:
            save_local_google_api_key(google_api_key)
            st.sidebar.success("Cle API enregistree localement.")
        else:
            st.sidebar.warning("Saisis une cle avant de l'enregistrer.")
    if k2.button("Charger cle"):
        loaded_key = load_local_google_api_key()
        if loaded_key:
            st.session_state["google_api_key_input"] = loaded_key
            st.sidebar.success("Cle API chargee.")
            st.rerun()
        else:
            st.sidebar.info("Aucune cle locale trouvee.")
offline_snapshot_mode = st.sidebar.toggle("Mode offline (snapshot CSV)", value=False)

st.sidebar.markdown("### Ponderation des criteres actifs")
raw_weights = {}
if active_criteria:
    default_raw = round(100 / len(active_criteria))

    if st.sidebar.button("Reinitialiser les ponderations"):
        st.session_state["weight_objective"] = 0.8
        st.session_state["criterion_raw_weights"] = {c: default_raw for c in active_criteria}
        st.rerun()

    for c in active_criteria:
        saved_value = st.session_state["criterion_raw_weights"].get(c, default_raw)
        raw_weights[c] = st.sidebar.slider(
            f"{criteria_labels[c]}",
            min_value=0,
            max_value=100,
            value=int(saved_value),
            step=5,
        )
    st.session_state["criterion_raw_weights"].update(raw_weights)
    total_raw = sum(raw_weights.values())
    if total_raw == 0:
        normalized_weights = {c: 1 / len(active_criteria) for c in active_criteria}
    else:
        normalized_weights = {c: raw_weights[c] / total_raw for c in active_criteria}
else:
    normalized_weights = {}

if selected_universities:
    filtered = universities[universities["university"].isin(selected_universities)].copy()
else:
    filtered = universities.copy()

crous_points = pd.DataFrame(columns=["name", "lat", "lon", "city"])
crous_error = None
if use_crous_api:
    try:
        crous_points = fetch_crous_points()
        # Filtrage simple Ile-de-France.
        crous_points = crous_points[
            (crous_points["lat"].between(48.1, 49.3))
            & (crous_points["lon"].between(1.3, 3.6))
        ].copy()
    except (URLError, ValueError, TimeoutError) as err:
        crous_error = str(err)

google_error = None
google_summary_rows = []
google_comments_rows = []
if use_google_api and google_api_key:
    food_types = ["restaurant", "cafe", "bakery", "supermarket", "meal_takeaway"]
    social_types = ["bar", "night_club", "movie_theater", "tourist_attraction", "store"]
    radius_m = RADIUS_TO_METERS[radius]
    try:
        for idx, uni in filtered.iterrows():
            food_ratings = []
            food_reviews = 0
            for place_type in food_types:
                avg_rating, reviews_count = fetch_google_places_summary(
                    float(uni["lat"]), float(uni["lon"]), radius_m, place_type, google_api_key
                )
                if avg_rating > 0:
                    food_ratings.append(avg_rating)
                food_reviews += reviews_count
            social_ratings = []
            social_reviews = 0
            for place_type in social_types:
                avg_rating, reviews_count = fetch_google_places_summary(
                    float(uni["lat"]), float(uni["lon"]), radius_m, place_type, google_api_key
                )
                if avg_rating > 0:
                    social_ratings.append(avg_rating)
                social_reviews += reviews_count

            food_avg = sum(food_ratings) / len(food_ratings) if food_ratings else 0.0
            social_avg = sum(social_ratings) / len(social_ratings) if social_ratings else 0.0
            food_api_score = score_from_google(food_avg, food_reviews)
            social_api_score = score_from_google(social_avg, social_reviews)

            filtered.at[idx, "food"] = round(0.6 * float(uni["food"]) + 0.4 * food_api_score, 1)
            filtered.at[idx, "social_life"] = round(
                0.6 * float(uni["social_life"]) + 0.4 * social_api_score, 1
            )

            google_summary_rows.append(
                {
                    "Universite": uni["university"],
                    "Food score API": food_api_score,
                    "Food avis": food_reviews,
                    "Vie sociale score API": social_api_score,
                    "Vie sociale avis": social_reviews,
                }
            )

            comments = fetch_google_place_reviews(
                float(uni["lat"]), float(uni["lon"]), radius_m, google_api_key
            )
            for text in comments:
                google_comments_rows.append({"Universite": uni["university"], "Commentaire": text})
    except (URLError, ValueError, TimeoutError) as err:
        google_error = str(err)


def save_google_snapshot(
    summary_rows: list[dict], comments_rows: list[dict], selected_radius: str
) -> tuple[Path, Path]:
    data_dir = Path(__file__).resolve().parent / "data"
    data_dir.mkdir(exist_ok=True)
    safe_radius = selected_radius.replace(" ", "").replace(".", "_")
    summary_path = data_dir / f"google_places_summary_{safe_radius}.csv"
    comments_path = data_dir / f"google_places_comments_{safe_radius}.csv"
    pd.DataFrame(summary_rows).to_csv(summary_path, index=False)
    pd.DataFrame(comments_rows).to_csv(comments_path, index=False)
    return summary_path, comments_path


def load_google_snapshot(selected_radius: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    data_dir = Path(__file__).resolve().parent / "data"
    safe_radius = selected_radius.replace(" ", "").replace(".", "_")
    summary_path = data_dir / f"google_places_summary_{safe_radius}.csv"
    comments_path = data_dir / f"google_places_comments_{safe_radius}.csv"
    summary_df = pd.read_csv(summary_path) if summary_path.exists() else pd.DataFrame()
    comments_df = pd.read_csv(comments_path) if comments_path.exists() else pd.DataFrame()
    return summary_df, comments_df

if not active_criteria:
    st.warning("Selectionne au moins un critere pour calculer une note.")
    st.stop()

def objective_score(row: pd.Series) -> float:
    return sum(row[c] * normalized_weights[c] for c in active_criteria)

if use_crous_api and not crous_points.empty:
    food_boost = compute_crous_food_adjustment(filtered, crous_points, radius_km)
    filtered["food"] = (filtered["food"] + food_boost).clip(upper=100)

filtered["objective_score"] = filtered.apply(objective_score, axis=1)
filtered["global_score"] = (
    filtered["objective_score"] * weight_objective
    + filtered["student_reviews"] * weight_subjective
).round(1)

sort_options = {
    "Note finale /100": "global_score",
    "Score objectif": "objective_score",
}
for criterion in active_criteria:
    sort_options[f"Critere - {criteria_labels[criterion]}"] = criterion

sort_label = st.sidebar.selectbox(
    "Classer les universites par",
    options=list(sort_options.keys()),
    index=0,
)

filtered = filtered.sort_values(sort_options[sort_label], ascending=False).reset_index(drop=True)

focus_university = st.sidebar.selectbox(
    "Universite focus (simule le clic sur un point)",
    options=filtered["university"].tolist(),
    index=0,
)

if offline_snapshot_mode:
    snapshot_summary_df, snapshot_comments_df = load_google_snapshot(radius)
    if snapshot_summary_df.empty:
        st.warning(
            "Mode offline actif, mais aucun snapshot CSV trouve pour ce rayon. "
            "Active Google Places puis enregistre un snapshot."
        )
    else:
        score_lookup = snapshot_summary_df.set_index("Universite")
        for idx, uni in filtered.iterrows():
            uni_name = uni["university"]
            if uni_name in score_lookup.index:
                filtered.at[idx, "food"] = min(
                    100,
                    round(0.6 * float(uni["food"]) + 0.4 * float(score_lookup.at[uni_name, "Food score API"]), 1),
                )
                filtered.at[idx, "social_life"] = min(
                    100,
                    round(
                        0.6 * float(uni["social_life"])
                        + 0.4 * float(score_lookup.at[uni_name, "Vie sociale score API"]),
                        1,
                    ),
                )
        filtered["objective_score"] = filtered.apply(objective_score, axis=1)
        filtered["global_score"] = (
            filtered["objective_score"] * weight_objective
            + filtered["student_reviews"] * weight_subjective
        ).round(1)
        filtered = filtered.sort_values(sort_options[sort_label], ascending=False).reset_index(drop=True)
        st.caption(
            f"Mode offline actif: snapshot charge pour {radius} "
            f"({len(snapshot_summary_df)} universites, {len(snapshot_comments_df)} commentaires)."
        )

focus_row = filtered[filtered["university"] == focus_university].iloc[0]

st.subheader("KPI")
k1, k2, k3, k4 = st.columns(4)
k1.metric("Universites analysees", len(filtered))
k2.metric("Rayon", radius)
k3.metric("Moyenne note finale", f"{filtered['global_score'].mean():.1f}/100")
k4.metric("Poids avis etudiants", f"{int(weight_subjective * 100)}%")

if use_crous_api:
    if crous_error:
        st.warning("API CROUS indisponible pour le moment: utilisation des scores de demonstration seulement.")
        st.caption(f"Detail erreur CROUS: {crous_error}")
    else:
        st.caption(
            f"API CROUS active: {len(crous_points)} points de restauration detectes en Ile-de-France (rayon analyse: {radius})."
        )

if use_google_api:
    if not google_api_key:
        st.info("Google Places API activee mais cle non renseignee: scores de demonstration conserves.")
    elif google_error:
        st.warning("Google Places API indisponible pour le moment: utilisation des scores de demonstration.")
        st.caption(f"Detail erreur Google Places: {google_error}")
    else:
        st.caption("Google Places API active: food et vie sociale ajustes avec ratings/avis autour des universites.")

if use_google_api and google_summary_rows and not google_error:
    if st.sidebar.button("Enregistrer snapshot Google CSV"):
        summary_path, comments_path = save_google_snapshot(
            google_summary_rows, google_comments_rows, radius
        )
        st.sidebar.success(
            f"Snapshots enregistres: {summary_path.name} et {comments_path.name}"
        )

st.markdown(f"### Universite selectionnee : **{focus_university}**")
st.markdown(f"[Acceder au site officiel de {focus_university}]({focus_row['url']})")

st.subheader("Profil de l'universite selectionnee (diagramme en batons)")
focus_metrics = active_criteria + ["student_reviews"]
focus_profile = pd.DataFrame(
    {
        "Critere": [criteria_labels.get(c, "Avis etudiants") if c != "student_reviews" else "Avis etudiants" for c in focus_metrics],
        "Score": [float(focus_row[c]) for c in focus_metrics],
    }
)
focus_chart = (
    alt.Chart(focus_profile)
    .mark_bar(color="#d62728", size=24)
    .encode(
        x=alt.X("Critere:N", sort=None, title="Critere"),
        y=alt.Y("Score:Q", scale=alt.Scale(domain=[0, 100]), title="Score"),
        tooltip=["Critere", "Score"],
    )
    .properties(height=320)
)
st.altair_chart(focus_chart, use_container_width=True)

st.subheader("Classement des universites (diagramme en batons couches)")
ranking_metric_options = {
    "Note globale /100": "global_score",
    "Score objectif": "objective_score",
    "Avis etudiants": "student_reviews",
}
for criterion in active_criteria:
    ranking_metric_options[f"Critere - {criteria_labels[criterion]}"] = criterion

selected_ranking_metric_label = st.selectbox(
    "Methode de classement pour le diagramme horizontal",
    options=list(ranking_metric_options.keys()),
    index=0,
)
selected_ranking_metric = ranking_metric_options[selected_ranking_metric_label]

ranking_chart_df = filtered[["university", selected_ranking_metric]].copy()
ranking_chart_df = ranking_chart_df.rename(columns={selected_ranking_metric: "ranking_value"})
ranking_chart_df["is_focus"] = ranking_chart_df["university"] == focus_university

ranking_chart = (
    alt.Chart(ranking_chart_df)
    .mark_bar()
    .encode(
        x=alt.X("ranking_value:Q", scale=alt.Scale(domain=[0, 100]), title=selected_ranking_metric_label),
        y=alt.Y("university:N", sort="-x", title="Universite"),
        color=alt.condition(
            alt.datum.is_focus,
            alt.value("#d62728"),
            alt.value("#7f7f7f"),
        ),
        tooltip=[
            alt.Tooltip("university:N", title="Universite"),
            alt.Tooltip("ranking_value:Q", title=selected_ranking_metric_label, format=".1f"),
        ],
    )
    .properties(height=420)
)
st.altair_chart(ranking_chart, use_container_width=True)

st.subheader("Carte des universites")

if "analysis_zone_enabled" not in st.session_state:
    st.session_state["analysis_zone_enabled"] = False
if "analysis_map_zoom" not in st.session_state:
    st.session_state["analysis_map_zoom"] = 12
if "selected_poi_name" not in st.session_state:
    st.session_state["selected_poi_name"] = ""

st.session_state["analysis_zone_enabled"] = st.toggle(
    "Zone d'analyse",
    value=st.session_state["analysis_zone_enabled"],
    help="Active/desactive l'affichage du cercle d'analyse et des points d'interet.",
)

zoom_for_render = int(st.session_state["analysis_map_zoom"])
analysis_radius_m = RADIUS_TO_METERS[radius]
focus_lat = float(focus_row["lat"])
focus_lon = float(focus_row["lon"])

map_obj = folium.Map(location=[focus_lat, focus_lon], zoom_start=zoom_for_render, tiles="CartoDB positron")

folium.Marker(
    location=[focus_lat, focus_lon],
    popup=folium.Popup(f"<b>{focus_university}</b>", max_width=280),
    tooltip=focus_university,
    icon=folium.Icon(color="red", icon="university", prefix="fa"),
).add_to(map_obj)

analysis_pois = pd.DataFrame()
analysis_error = None
if st.session_state["analysis_zone_enabled"] and use_google_api and google_api_key:
    try:
        analysis_pois = fetch_analysis_pois(focus_lat, focus_lon, analysis_radius_m, google_api_key)
    except (URLError, ValueError, TimeoutError) as err:
        analysis_error = str(err)

zone_visible = st.session_state["analysis_zone_enabled"] and zoom_for_render >= ANALYSIS_MIN_ZOOM
if st.session_state["analysis_zone_enabled"] and not zone_visible:
    st.info(
        f"Zoome davantage pour afficher la zone d'analyse (zoom actuel: {zoom_for_render}, minimum: {ANALYSIS_MIN_ZOOM})."
    )

if zone_visible:
    folium.Circle(
        location=[focus_lat, focus_lon],
        radius=analysis_radius_m,
        color="#2e86c1",
        weight=3,
        fill=True,
        fill_color="#85c1e9",
        fill_opacity=0.25,
        popup=f"Zone d'analyse {radius} autour de {focus_university}",
    ).add_to(map_obj)

    for _, poi in analysis_pois.iterrows():
        rating_txt = f"{poi['rating']:.1f}" if pd.notna(poi["rating"]) else "N/A"
        reviews_txt = int(poi["reviews_count"]) if pd.notna(poi["reviews_count"]) else "N/A"
        link_txt = poi["external_link"] if poi["external_link"] else "N/A"
        popup_html = (
            f"<b>{poi['symbol']} {poi['name']}</b><br>"
            f"Categorie: {poi['category_label']}<br>"
            f"Note: {rating_txt}<br>"
            f"Nombre d'avis: {reviews_txt}<br>"
            f"Coordonnees: {poi['lat']:.6f}, {poi['lon']:.6f}<br>"
            f"Lien: <a href='{link_txt}' target='_blank'>Ouvrir</a>"
        )
        folium.Marker(
            location=[float(poi["lat"]), float(poi["lon"])],
            popup=folium.Popup(popup_html, max_width=340),
            tooltip=f"{poi['symbol']} {poi['name']}",
            icon=folium.DivIcon(
                html=(
                    f"<div style='"
                    f"background:{poi['color']};"
                    "color:#111111;"
                    "border-radius:50%;"
                    "width:24px;height:24px;"
                    "display:flex;align-items:center;justify-content:center;"
                    "font-weight:900;font-size:14px;"
                    "border:2px solid #ffffff;"
                    "box-shadow:0 0 0 1px rgba(0,0,0,0.25);'>"
                    f"{poi['symbol']}</div>"
                )
            ),
        ).add_to(map_obj)

map_state = st_folium(
    map_obj,
    width=None,
    height=520,
    returned_objects=["zoom", "last_object_clicked"],
    key="analysis_map",
)
if map_state and map_state.get("zoom") is not None:
    st.session_state["analysis_map_zoom"] = map_state["zoom"]

if analysis_error:
    st.warning(f"Zone d'analyse indisponible: {analysis_error}")
elif st.session_state["analysis_zone_enabled"] and not use_google_api:
    st.info("Active Google Places API pour recuperer les points d'interet.")
elif st.session_state["analysis_zone_enabled"] and use_google_api and not google_api_key:
    st.info("Renseigne la cle Google Places API pour recuperer les points d'interet.")

legend_html = " | ".join(
    [f"<span style='color:{cfg['color']};font-weight:700'>{cfg['symbol']}</span> {cfg['label']}" for cfg in POI_CATEGORY_CONFIG.values()]
)
st.markdown(f"**Legende:** {legend_html}", unsafe_allow_html=True)

clicked_name = ""
clicked = map_state.get("last_object_clicked") if map_state else None
if clicked and not analysis_pois.empty:
    lat_clicked = clicked.get("lat")
    lon_clicked = clicked.get("lng")
    if lat_clicked is not None and lon_clicked is not None:
        proximity = (analysis_pois["lat"] - float(lat_clicked)).abs() + (
            analysis_pois["lon"] - float(lon_clicked)
        ).abs()
        nearest_idx = proximity.idxmin()
        # Evite de "selectionner" un lieu quand on clique juste sur la carte.
        if float(proximity.loc[nearest_idx]) < 0.003:
            clicked_name = str(analysis_pois.loc[nearest_idx, "name"])
            st.session_state["selected_poi_name"] = clicked_name

if zone_visible and not analysis_pois.empty:
    poi_options = ["-- Aucun --"] + sorted(analysis_pois["name"].unique().tolist())
    selected_from_list = st.sidebar.selectbox(
        "Choisir un lieu (zone d'analyse)",
        options=poi_options,
        index=0 if st.session_state["selected_poi_name"] not in poi_options else poi_options.index(st.session_state["selected_poi_name"]),
    )
    if selected_from_list != "-- Aucun --":
        st.session_state["selected_poi_name"] = selected_from_list

selected_poi = pd.Series(dtype="object")
if st.session_state["selected_poi_name"] and not analysis_pois.empty:
    matched = analysis_pois[analysis_pois["name"] == st.session_state["selected_poi_name"]]
    if not matched.empty:
        selected_poi = matched.iloc[0]

with st.sidebar.expander("Lieu selectionne (zone d'analyse)", expanded=False):
    if selected_poi.empty:
        st.write("Aucun lieu selectionne sur la carte.")
    else:
        st.markdown(f"**Nom:** {selected_poi['name']}")
        st.markdown(f"**Categorie:** {selected_poi['category_label']}")
        st.markdown(f"**Note:** {selected_poi['rating'] if pd.notna(selected_poi['rating']) else 'N/A'}")
        st.markdown(
            f"**Nombre d'avis:** {int(selected_poi['reviews_count']) if pd.notna(selected_poi['reviews_count']) else 'N/A'}"
        )
        st.markdown(f"**Coordonnees GPS:** {selected_poi['lat']:.6f}, {selected_poi['lon']:.6f}")
        if selected_poi["external_link"]:
            st.markdown(f"[Lien externe]({selected_poi['external_link']})")
        else:
            st.write("Lien externe: N/A")

st.subheader("Liste des lieux dans la zone d'analyse")
if not zone_visible:
    st.write("Active la zone d'analyse et zoome sur l'universite pour afficher les lieux.")
elif analysis_pois.empty:
    st.write("Aucun point d'interet trouve dans ce rayon.")
else:
    poi_list_df = analysis_pois[
        ["name", "category_label", "rating", "reviews_count", "lat", "lon", "external_link"]
    ].rename(
        columns={
            "name": "Nom",
            "category_label": "Categorie",
            "rating": "Note",
            "reviews_count": "Nombre d'avis",
            "lat": "Latitude",
            "lon": "Longitude",
            "external_link": "Lien externe",
        }
    )
    for category_name in poi_list_df["Categorie"].unique().tolist():
        subset = poi_list_df[poi_list_df["Categorie"] == category_name]
        st.markdown(f"**{category_name}**")
        st.dataframe(subset, use_container_width=True, hide_index=True)

st.subheader("Tableau de controle des scores")
score_table = filtered[
    ["university", "global_score", "objective_score", "student_reviews"] + active_criteria
].rename(
    columns={
        "university": "Universite",
        "global_score": "Note finale /100",
        "objective_score": "Score objectif",
        "student_reviews": "Avis etudiants",
        **{k: v for k, v in criteria_labels.items()},
    }
)
st.dataframe(score_table, use_container_width=True, hide_index=True)

export_df = filtered[
    ["university", "global_score", "objective_score", "student_reviews"] + active_criteria
].rename(
    columns={
        "university": "Universite",
        "global_score": "Note finale /100",
        "objective_score": "Score objectif",
        "student_reviews": "Avis etudiants",
        **{k: v for k, v in criteria_labels.items()},
    }
)
st.download_button(
    label="Exporter classement final CSV",
    data=export_df.to_csv(index=False).encode("utf-8"),
    file_name=f"classement_universites_{radius.replace(' ', '').replace('.', '_')}.csv",
    mime="text/csv",
)

if use_google_api and google_summary_rows and not google_error:
    st.subheader("Synthese Google Places (par universite)")
    st.dataframe(pd.DataFrame(google_summary_rows), use_container_width=True, hide_index=True)

if use_google_api and google_comments_rows and not google_error:
    st.subheader("Exemples de commentaires Google Places")
    st.dataframe(pd.DataFrame(google_comments_rows).head(50), use_container_width=True, hide_index=True)

st.subheader("References des criteres")
ref_table = pd.DataFrame(
    [
        {"Critere": "Logement", "Definition": "Prix, disponibilite, tension locative.", "Sources cibles": "MeilleursAgents, CROUS, open data loyers"},
        {"Critere": "Transport", "Definition": "Distance et accessibilite aux stations metro/bus/RER/tram.", "Sources cibles": "RATP, SNCF, IDFM GTFS"},
        {"Critere": "Food", "Definition": "Courses, alimentation, boulangeries, resto CROUS.", "Sources cibles": "Google Places, OSM, CROUS"},
        {"Critere": "Vie sociale", "Definition": "Restaurants, bars, activites, sorties.", "Sources cibles": "Google Places, OSM, open agenda local"},
        {"Critere": "Espaces verts", "Definition": "Proximite et densite de parcs/espaces verts.", "Sources cibles": "OSM, open data espaces verts"},
    ]
)
st.dataframe(ref_table, use_container_width=True, hide_index=True)

st.info(
    "Etat MVP: scores de demonstration. Etape suivante: brancher les APIs (Google Places, CROUS, RATP/SNCF, MeilleursAgents si acces), "
    "puis normaliser automatiquement les indicateurs par rayon (1, 2.5, 5 km)."
)
