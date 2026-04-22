from __future__ import annotations

import base64
from html import escape
from pathlib import Path
from textwrap import dedent

import pandas as pd
import requests
import streamlit as st

DEFAULT_LOCATION = {
    "name": "De Bilt",
    "admin1": "Utrecht",
    "country": "Nederland",
    "latitude": 52.11,
    "longitude": 5.18,
}

# Eigen nieuwsregels voor autoplay / voorlezen
EIGEN_NIEUWSREGELS = [
    "Dit is jouw weerupdate!",
    "Je luistert naar Radio Muziekstad.",
    "Hier is het weer van vandaag en de komende uren.",
    "Blijf luisteren voor muziek, actualiteit en lokale updates.",
]

st.set_page_config(
    page_title="Muziekstad Weer",
    page_icon="🌤️",
    layout="wide",
    initial_sidebar_state="collapsed",
)

DAGNAAM_VOL = ["maandag", "dinsdag", "woensdag", "donderdag", "vrijdag", "zaterdag", "zondag"]
DAGNAAM_KORT = ["ma", "di", "wo", "do", "vr", "za", "zo"]
MAAND_KORT = ["jan", "feb", "mrt", "apr", "mei", "jun", "jul", "aug", "sep", "okt", "nov", "dec"]

WEER_CODES = {
    0: ("Zonnig", "☀️"),
    1: ("Overwegend zonnig", "🌤️"),
    2: ("Half bewolkt", "⛅"),
    3: ("Bewolkt", "☁️"),
    45: ("Mist", "🌫️"),
    48: ("Rijpende mist", "🌫️"),
    51: ("Lichte motregen", "🌦️"),
    53: ("Motregen", "🌦️"),
    55: ("Dichte motregen", "🌧️"),
    56: ("Lichte ijzel", "🌨️"),
    57: ("IJzel", "🌨️"),
    61: ("Lichte regen", "🌦️"),
    63: ("Regen", "🌧️"),
    65: ("Zware regen", "🌧️"),
    66: ("Lichte ijzelregen", "🌨️"),
    67: ("Zware ijzelregen", "🌨️"),
    71: ("Lichte sneeuw", "🌨️"),
    73: ("Sneeuw", "❄️"),
    75: ("Zware sneeuw", "❄️"),
    77: ("Sneeuwkorrels", "🌨️"),
    80: ("Lichte buien", "🌦️"),
    81: ("Buien", "🌦️"),
    82: ("Zware buien", "⛈️"),
    85: ("Lichte sneeuwbuien", "🌨️"),
    86: ("Zware sneeuwbuien", "❄️"),
    95: ("Onweer", "⛈️"),
    96: ("Onweer met lichte hagel", "⛈️"),
    99: ("Onweer met hagel", "⛈️"),
}

CSS = dedent(
    """
    <style>
    header[data-testid="stHeader"],
    div[data-testid="stToolbar"],
    div[data-testid="stDecoration"],
    div[data-testid="stStatusWidget"],
    #MainMenu,
    footer {
        display: none !important;
        visibility: hidden !important;
    }

    .stApp {
        background:
            radial-gradient(circle at top left, rgba(41, 98, 255, 0.16), transparent 30%),
            linear-gradient(180deg, #06162d 0%, #061a38 45%, #07121e 100%);
    }

    .block-container {
        max-width: 1380px;
        padding-top: 0.5rem;
        padding-bottom: 2rem;
    }

    .hero, .ticker-card, .glass-card {
        background: rgba(8, 22, 46, 0.68);
        border: 1px solid rgba(255,255,255,0.08);
        border-radius: 24px;
        backdrop-filter: blur(12px);
        box-shadow: 0 10px 30px rgba(0,0,0,0.18);
    }

    .hero {
        display: flex;
        justify-content: space-between;
        align-items: center;
        gap: 20px;
        padding: 20px 24px;
        margin-bottom: 14px;
    }

    .hero-left {
        display: flex;
        align-items: center;
        min-height: 72px;
    }

    .logo-wrap img {
        max-height: 78px;
        width: auto;
        display: block;
    }

    .hero-now {
        text-align: right;
        color: #fff;
    }

    .hero-temp {
        font-size: 3rem;
        font-weight: 900;
        line-height: 1;
    }

    .hero-meta {
        margin-top: 8px;
        color: rgba(255,255,255,0.82);
        font-size: 1rem;
    }

    .ticker-card {
        padding: 15px 18px;
        margin-bottom: 18px;
        overflow: hidden;
    }

    .ticker-wrap {
        display: flex;
        align-items: center;
        gap: 16px;
    }

    .ticker-label {
        flex: 0 0 auto;
        color: #ff6b6b;
        font-weight: 900;
        text-transform: uppercase;
        letter-spacing: 0.04em;
        font-size: 0.92rem;
    }

    .ticker-marquee {
        overflow: hidden;
        white-space: nowrap;
        width: 100%;
    }

    .ticker-track {
        display: inline-block;
        white-space: nowrap;
        padding-left: 100%;
        animation: ticker-scroll 62s linear infinite;
        color: rgba(255,255,255,0.92);
        font-weight: 700;
        font-size: 1rem;
    }

    .ticker-item {
        display: inline-block;
        margin-right: 42px;
    }

    @keyframes ticker-scroll {
        0% { transform: translateX(0); }
        100% { transform: translateX(-100%); }
    }

    .glass-card {
        padding: 18px 22px;
        margin-bottom: 18px;
    }

    .location-note {
        color: rgba(255,255,255,0.78);
        margin-top: -6px;
        margin-bottom: 14px;
        font-size: 0.98rem;
    }

    .section-title {
        font-size: 1.9rem;
        font-weight: 900;
        color: #fff;
        margin-bottom: 14px;
    }

    .summary-grid, .hour-grid, .daily-grid {
        display: grid;
        gap: 16px;
    }

    .summary-grid { grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); }
    .hour-grid { grid-template-columns: repeat(auto-fit, minmax(170px, 1fr)); }
    .daily-grid { grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); }
    .daily-grid.compact { grid-template-columns: repeat(5, minmax(0, 1fr)); gap: 12px; }

    .summary-card, .hour-card, .daily-card {
        background: linear-gradient(180deg, rgba(255,255,255,0.07), rgba(255,255,255,0.035));
        border: 1px solid rgba(255,255,255,0.08);
        border-radius: 22px;
        padding: 18px;
        color: #fff;
        min-height: 100%;
    }

    .summary-label {
        font-size: 1rem;
        font-weight: 700;
        color: rgba(255,255,255,0.88);
        margin-bottom: 8px;
    }

    .summary-value {
        font-size: 1.35rem;
        font-weight: 900;
        margin-bottom: 6px;
    }

    .summary-desc {
        font-size: 0.98rem;
        color: rgba(255,255,255,0.78);
        line-height: 1.45;
    }

    .hour-time, .daily-day {
        font-size: 1.05rem;
        font-weight: 800;
        margin-bottom: 8px;
    }

    .hour-icon, .daily-icon {
        font-size: 1.9rem;
        margin-bottom: 6px;
    }

    .hour-temp, .daily-temp {
        font-size: 2rem;
        font-weight: 900;
        margin-bottom: 8px;
    }

    .daily-desc {
        font-size: 1.15rem;
        font-weight: 700;
        margin-bottom: 8px;
    }

    .daily-card.compact {
        border-radius: 18px;
        padding: 14px 14px 12px;
    }

    .daily-card.compact .daily-day {
        font-size: 0.96rem;
        margin-bottom: 4px;
    }

    .daily-card.compact .daily-icon {
        font-size: 1.45rem;
        margin-bottom: 2px;
    }

    .daily-card.compact .daily-desc {
        font-size: 0.96rem;
        margin-bottom: 4px;
    }

    .daily-card.compact .daily-temp {
        font-size: 1.35rem;
        margin-bottom: 4px;
    }

    .daily-card.compact .daily-meta {
        font-size: 0.9rem;
        line-height: 1.4;
    }

    .hour-meta, .daily-meta {
        color: rgba(255,255,255,0.84);
        font-size: 1rem;
        line-height: 1.55;
    }

    div[data-baseweb="tab-list"] button [data-testid="stMarkdownContainer"] p {
        font-size: 1.05rem;
        font-weight: 700;
    }

    .footer-note {
        text-align: center;
        color: rgba(255,255,255,0.74);
        font-size: 0.96rem;
        padding: 10px 0 4px;
    }

    .footer-note a {
        color: #ffffff;
        text-decoration: underline;
        text-underline-offset: 2px;
    }

    @media (max-width: 1180px) {
        .daily-grid.compact { grid-template-columns: repeat(3, minmax(0, 1fr)); }
    }

    @media (max-width: 760px) {
        .daily-grid.compact { grid-template-columns: repeat(2, minmax(0, 1fr)); }
    }
    </style>
    """
).strip()


def html_block(text: str) -> str:
    return dedent(text).strip()


def weer_info(code: int) -> tuple[str, str]:
    return WEER_CODES.get(int(code), ("Onbekend", "🌤️"))


def round_int(value) -> int:
    if pd.isna(value):
        return 0
    return int(round(float(value)))


def format_korte_datum(ts: pd.Timestamp) -> str:
    return f"{DAGNAAM_KORT[ts.weekday()]} {ts.day} {MAAND_KORT[ts.month - 1]}"


def format_dag_kop(ts: pd.Timestamp) -> str:
    return f"{DAGNAAM_VOL[ts.weekday()].capitalize()} · {format_korte_datum(ts)}"


def format_uur(ts: pd.Timestamp, include_day: bool = False) -> str:
    return f"{DAGNAAM_KORT[ts.weekday()].capitalize()} {ts.strftime('%H:%M')}" if include_day else ts.strftime("%H:%M")


def logo_base64() -> str | None:
    base = Path(__file__).resolve().parent
    candidates = [
        base / "muziekstad_weerbericht_logo_wit_transparant.png",
        base / "muziekstad_weer_logo.png",
        *sorted(base.glob("*logo*.png")),
    ]
    for path in candidates:
        if path.exists() and path.is_file():
            return base64.b64encode(path.read_bytes()).decode("utf-8")
    return None




def location_label(location: dict) -> str:
    parts = [location.get("name") or ""]
    if location.get("admin1"):
        parts.append(location["admin1"])
    if location.get("country"):
        parts.append(location["country"])
    return ", ".join([p for p in parts if p])


@st.cache_data(ttl=3600)
def search_locations(query: str) -> list[dict]:
    query = query.strip()
    if not query:
        return [DEFAULT_LOCATION]

    response = requests.get(
        "https://geocoding-api.open-meteo.com/v1/search",
        params={
            "name": query,
            "count": 10,
            "language": "nl",
            "format": "json",
        },
        timeout=20,
    )
    response.raise_for_status()
    data = response.json()
    results = data.get("results") or []
    locations: list[dict] = []
    for item in results:
        locations.append(
            {
                "name": item.get("name", "Onbekende plaats"),
                "admin1": item.get("admin1") or item.get("admin2") or "",
                "country": item.get("country", ""),
                "latitude": float(item["latitude"]),
                "longitude": float(item["longitude"]),
            }
        )
    return locations or [DEFAULT_LOCATION]


def render_location_picker() -> dict:
    st.markdown(
        html_block(
            """
            <div class='glass-card'>
                <div class='section-title'>Locatie</div>
            </div>
            """
        ),
        unsafe_allow_html=True,
    )
    search_default = st.session_state.get("location_query", DEFAULT_LOCATION["name"])
    query = st.text_input("Zoek op land, regio of plaats", value=search_default, key="location_query")
    results = search_locations(query)

    labels = [location_label(loc) for loc in results]
    current_label = st.session_state.get("selected_location_label", location_label(DEFAULT_LOCATION))
    default_index = labels.index(current_label) if current_label in labels else 0
    selected_label = st.selectbox("Kies locatie", labels, index=default_index, key="selected_location")
    selected = results[labels.index(selected_label)]
    st.caption(f"Standaardlocatie: {location_label(DEFAULT_LOCATION)}")
    st.session_state["selected_location_label"] = selected_label
    return selected


@st.cache_data(ttl=900)
def fetch_weather(lat: float, lon: float) -> tuple[pd.DataFrame, pd.DataFrame]:
    response = requests.get(
        "https://api.open-meteo.com/v1/forecast",
        params={
            "latitude": lat,
            "longitude": lon,
            "hourly": ",".join([
                "temperature_2m",
                "apparent_temperature",
                "precipitation_probability",
                "weather_code",
                "wind_speed_10m",
                "relative_humidity_2m",
            ]),
            "daily": ",".join([
                "weather_code",
                "temperature_2m_max",
                "temperature_2m_min",
                "precipitation_probability_max",
                "precipitation_sum",
                "wind_speed_10m_max",
                "sunrise",
                "sunset",
                "uv_index_max",
            ]),
            "timezone": "auto",
            "forecast_days": 10,
        },
        timeout=20,
    )
    response.raise_for_status()
    data = response.json()

    hourly = pd.DataFrame(data["hourly"])
    hourly["time"] = pd.to_datetime(hourly["time"])

    daily = pd.DataFrame(data["daily"])
    daily["time"] = pd.to_datetime(daily["time"])
    daily["sunrise"] = pd.to_datetime(daily["sunrise"])
    daily["sunset"] = pd.to_datetime(daily["sunset"])
    return hourly, daily


def render_hero(hourly_df: pd.DataFrame, location_name: str) -> None:
    now = hourly_df.iloc[0]
    omschrijving, icoon = weer_info(now["weather_code"])
    logo = logo_base64()

    left_html = "<div class='hero-left'></div>"
    if logo:
        left_html = (
            "<div class='hero-left'>"
            f"<div class='logo-wrap'><img src='data:image/png;base64,{logo}' alt='Muziekstad logo'></div>"
            "</div>"
        )

    st.markdown(
        html_block(
            f"""
            <div class="hero">
                {left_html}
                <div class="hero-now">
                    <div class="hero-temp">{round_int(now['temperature_2m'])}°C {icoon}</div>
                    <div class="hero-meta">{location_name} · {omschrijving} · Gevoel {round_int(now['apparent_temperature'])}°C · 💨 {round_int(now['wind_speed_10m'])} km/u</div>
                </div>
            </div>
            """
        ),
        unsafe_allow_html=True,
    )


def build_news_items(hourly_df: pd.DataFrame, daily_df: pd.DataFrame, location_name: str) -> list[str]:
    now = hourly_df.iloc[0]
    komende12 = hourly_df.head(12)
    komende24 = hourly_df.head(24)
    warmste = hourly_df.loc[hourly_df["temperature_2m"].idxmax()]
    natste = daily_df.loc[daily_df["precipitation_sum"].idxmax()]
    windy = hourly_df.loc[hourly_df["wind_speed_10m"].idxmax()]
    warmste_dag = daily_df.loc[daily_df["temperature_2m_max"].idxmax()]
    koudste_nacht = daily_df.loc[daily_df["temperature_2m_min"].idxmin()]

    nu_omschrijving, _ = weer_info(now["weather_code"])
    nat_omschrijving, _ = weer_info(natste["weather_code"])
    warmste_dag_omschrijving, _ = weer_info(warmste_dag["weather_code"])

    automatisch = [
        f"Nu in {location_name}: {nu_omschrijving.lower()} en {round_int(now['temperature_2m'])}°C.",
        f"Warmste moment: {format_korte_datum(warmste['time'])} rond {warmste['time'].strftime('%H:%M')} met {round_int(warmste['temperature_2m'])}°C.",
        f"Meeste neerslag: {format_dag_kop(natste['time'])} met {natste['precipitation_sum']:.1f} mm bij {nat_omschrijving.lower()}.",
        f"Meeste wind: rond {windy['time'].strftime('%H:%M')} met {round_int(windy['wind_speed_10m'])} km/u.",
        f"Komende 12 uur: tussen {round_int(komende12['temperature_2m'].min())}°C en {round_int(komende12['temperature_2m'].max())}°C.",
        f"Komende 24 uur: regenkans tot {round_int(komende24['precipitation_probability'].max())}% en wind tot {round_int(komende24['wind_speed_10m'].max())} km/u.",
        f"10-daagse lijn: warmste dag wordt {format_dag_kop(warmste_dag['time'])} met {round_int(warmste_dag['temperature_2m_max'])}°C bij {warmste_dag_omschrijving.lower()}.",
        f"Koudste nacht in zicht: {format_dag_kop(koudste_nacht['time'])} met ongeveer {round_int(koudste_nacht['temperature_2m_min'])}°C.",
    ]
    return EIGEN_NIEUWSREGELS + automatisch


def render_news_ticker(items: list[str]) -> None:
    spans = "".join(f"<span class='ticker-item'>{escape(item)}</span>" for item in items + items)
    st.markdown(
        html_block(
            f"""
            <div class="ticker-card">
                <div class="ticker-wrap">
                    <div class="ticker-label">Nieuws</div>
                    <div class="ticker-marquee">
                        <div class="ticker-track">{spans}</div>
                    </div>
                </div>
            </div>
            """
        ),
        unsafe_allow_html=True,
    )


def summary_card(label: str, value: str, desc: str) -> str:
    return html_block(
        f"""
        <div class="summary-card">
            <div class="summary-label">{label}</div>
            <div class="summary-value">{value}</div>
            <div class="summary-desc">{desc}</div>
        </div>
        """
    )


def render_summary(hourly_df: pd.DataFrame, daily_df: pd.DataFrame) -> None:
    warmste = hourly_df.loc[hourly_df["temperature_2m"].idxmax()]
    natste = daily_df.loc[daily_df["precipitation_sum"].idxmax()]
    windy = hourly_df.loc[hourly_df["wind_speed_10m"].idxmax()]
    komende = hourly_df.head(12)

    nat_omschrijving, _ = weer_info(natste["weather_code"])
    wind_omschrijving, _ = weer_info(windy["weather_code"])
    warm_omschrijving, _ = weer_info(warmste["weather_code"])
    nu_omschrijving, _ = weer_info(komende.iloc[0]["weather_code"])

    cards = [
        summary_card(
            "Warmste moment",
            f"{format_korte_datum(warmste['time'])} · {round_int(warmste['temperature_2m'])}°C",
            f"Verwacht rond {warmste['time'].strftime('%H:%M')} bij {warm_omschrijving.lower()}.",
        ),
        summary_card(
            "Meeste neerslag",
            f"{format_dag_kop(natste['time'])} · {natste['precipitation_sum']:.1f} mm",
            f"De dag met de meeste verwachte neerslag. {nat_omschrijving} met {round_int(natste['precipitation_probability_max'])}% kans.",
        ),
        summary_card(
            "Meeste wind",
            f"{format_korte_datum(windy['time'])} · {round_int(windy['wind_speed_10m'])} km/u",
            f"Waarschijnlijk de onstuimigste periode. Relevant voor buitenactiviteiten bij {wind_omschrijving.lower()}.",
        ),
        summary_card(
            "Komende uren",
            f"{nu_omschrijving} nu",
            f"Binnen de eerstvolgende 12 uur ligt de temperatuur grofweg tussen {round_int(komende['temperature_2m'].min())}°C en {round_int(komende['temperature_2m'].max())}°C.",
        ),
    ]

    st.markdown(
        html_block(
            f"""
            <div class="glass-card">
                <div class="summary-grid">{''.join(cards)}</div>
            </div>
            """
        ),
        unsafe_allow_html=True,
    )


def build_hour_card(row: pd.Series, include_day: bool = False) -> str:
    omschrijving, icoon = weer_info(row["weather_code"])
    return html_block(
        f"""
        <div class="hour-card">
            <div class="hour-time">{format_uur(row['time'], include_day=include_day)}</div>
            <div class="hour-icon">{icoon}</div>
            <div class="hour-temp">{round_int(row['temperature_2m'])}°C</div>
            <div class="hour-meta">
                {omschrijving}<br>
                🌡️ Gevoel {round_int(row['apparent_temperature'])}°C<br>
                ☔ {round_int(row['precipitation_probability'])}%<br>
                💨 {round_int(row['wind_speed_10m'])} km/u<br>
                💧 {round_int(row['relative_humidity_2m'])}%
            </div>
        </div>
        """
    )


def render_hours(df: pd.DataFrame, title: str, count: int, include_day: bool = False) -> None:
    cards = "".join(build_hour_card(row, include_day=include_day) for _, row in df.head(count).iterrows())
    st.markdown(
        html_block(
            f"""
            <div class="glass-card">
                <div class="section-title">{title}</div>
                <div class="hour-grid">{cards}</div>
            </div>
            """
        ),
        unsafe_allow_html=True,
    )


def build_daily_card(row: pd.Series) -> str:
    omschrijving, icoon = weer_info(row["weather_code"])
    return html_block(
        f"""
        <div class="daily-card">
            <div class="daily-day">{format_dag_kop(row['time'])}</div>
            <div class="daily-icon">{icoon}</div>
            <div class="daily-desc">{omschrijving}</div>
            <div class="daily-temp">{round_int(row['temperature_2m_min'])}° / {round_int(row['temperature_2m_max'])}°</div>
            <div class="daily-meta">
                ☔ {round_int(row['precipitation_probability_max'])}% kans<br>
                🌧️ {row['precipitation_sum']:.1f} mm<br>
                💨 {round_int(row['wind_speed_10m_max'])} km/u<br>
                🌅 {row['sunrise'].strftime('%H:%M')} · 🌇 {row['sunset'].strftime('%H:%M')}<br>
                😎 UV {row['uv_index_max']:.1f}
            </div>
        </div>
        """
    )


def build_daily_card_compact(row: pd.Series) -> str:
    omschrijving, icoon = weer_info(row["weather_code"])
    return html_block(
        f"""
        <div class="daily-card compact">
            <div class="daily-day">{format_dag_kop(row['time'])}</div>
            <div class="daily-icon">{icoon}</div>
            <div class="daily-desc">{omschrijving}</div>
            <div class="daily-temp">{round_int(row['temperature_2m_min'])}° / {round_int(row['temperature_2m_max'])}°</div>
            <div class="daily-meta">
                ☔ {round_int(row['precipitation_probability_max'])}% · 💨 {round_int(row['wind_speed_10m_max'])} km/u
            </div>
        </div>
        """
    )


def render_daily_compact(daily_df: pd.DataFrame, title: str = "Komende 5 dagen", count: int = 5) -> None:
    subset = daily_df.head(count)
    cards = "".join(build_daily_card_compact(row) for _, row in subset.iterrows())
    st.markdown(
        html_block(
            f"""
            <div class="glass-card">
                <div class="section-title">{title}</div>
                <div class="daily-grid compact">{cards}</div>
            </div>
            """
        ),
        unsafe_allow_html=True,
    )


def render_daily(daily_df: pd.DataFrame, title: str = "10-daagse verwachting", count: int | None = None) -> None:
    subset = daily_df.head(count) if count is not None else daily_df
    cards = "".join(build_daily_card(row) for _, row in subset.iterrows())
    st.markdown(
        html_block(
            f"""
            <div class="glass-card">
                <div class="section-title">{title}</div>
                <div class="daily-grid">{cards}</div>
            </div>
            """
        ),
        unsafe_allow_html=True,
    )


def render_footer() -> None:
    st.markdown(
        html_block(
            "<div class='footer-note'>Copyright: <a href='https://brandingtotaal.nl' target='_blank' rel='noopener noreferrer'>Branding Totaal</a></div>"
        ),
        unsafe_allow_html=True,
    )


def main() -> None:
    st.markdown(CSS, unsafe_allow_html=True)

    try:
        selected_location = render_location_picker()
        location_name = selected_location.get("name", DEFAULT_LOCATION["name"])
        hourly_df, daily_df = fetch_weather(selected_location["latitude"], selected_location["longitude"])

        render_hero(hourly_df, location_name)
        render_news_ticker(build_news_items(hourly_df, daily_df, location_name))

        tab1, tab2, tab3 = st.tabs(["Overzicht", "Uur per uur", "10 dagen"])

        with tab1:
            render_summary(hourly_df, daily_df)
            render_daily_compact(daily_df, title="Komende 5 dagen", count=5)
            render_hours(hourly_df, "Komende 12 uur", 12, include_day=False)

        with tab2:
            render_hours(hourly_df, "Uurverwachting komende 24 uur", 24, include_day=True)

        with tab3:
            render_daily(daily_df)

        render_footer()

    except requests.RequestException:
        st.error("Er ging iets mis bij het ophalen van de weerdata. Probeer het opnieuw.")
    except Exception as exc:
        st.error(f"Er ging iets mis: {exc}")


if __name__ == "__main__":
    main()
