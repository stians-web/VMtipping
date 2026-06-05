"""Spotify patch v5.2 for VM 2026 Streamlit app v4."""
from pathlib import Path

APP = Path("app.py")
if not APP.exists():
    raise FileNotFoundError("Fant ikke app.py. Legg denne filen i samme mappe som app.py.")

text = APP.read_text(encoding="utf-8")

# 1) Importer Streamlit components
if "import streamlit.components.v1 as components" not in text:
    text = text.replace("import streamlit as st\n", "import streamlit as st\nimport streamlit.components.v1 as components\n")

# 2) Spotify-blokk. Bruker vanlig streng-bygging for å unngå f-string/triple-quote-feil.
spotify_block = "\n".join([
    "",
    "# Spotify-spiller som vises etter at brukeren trykker Prøv lykken!",
    "# Merk: Brukeren må normalt trykke Play i Spotify-spilleren selv.",
    "SPOTIFY_EMBED_URL = \"https://open.spotify.com/embed/track/6z5sjLABC6XkNviIYeFUqF?utm_source=generator\"",
    "",
    "def show_spotify_player():",
    "    st.markdown(\"### 🎵 Prøv lykken-sang\")",
    "    components.iframe(",
    "        SPOTIFY_EMBED_URL,",
    "        height=152,",
    "        scrolling=False,",
    "    )",
    "",
])

if "SPOTIFY_EMBED_URL" not in text:
    pos = text.find("DATA_DIR = Path")
    if pos == -1:
        raise RuntimeError("Fant ikke stedet der Spotify-blokken skal settes inn. Sjekk at dette er v4 app.py.")
    text = text[:pos] + spotify_block + "\n" + text[pos:]

# 3) Legg til session flag hvis mulig
if "play_luck_song" not in text:
    text = text.replace("\"actual_ui_version\": 0}", "\"actual_ui_version\": 0, \"play_luck_song\": False}")

# 4) Sett flagget når Prøv lykken kjøres
if "st.session_state.play_luck_song = True" not in text:
    old = "st.toast(\"Prøv lykken er kjørt – ny kupong generert!\")\n        st.rerun()"
    new = "st.session_state.play_luck_song = True\n        st.toast(\"Prøv lykken er kjørt – ny kupong generert!\")\n        st.rerun()"
    if old not in text:
        raise RuntimeError("Fant ikke toast/rerun-blokken. Sjekk at dette er v4 app.py.")
    text = text.replace(old, new)

# 5) Vis Spotify-spilleren etter deltaker-knappen
needle = "try_luck_button(\"Prøv lykken!\", \"participant\", f\"{prefix}_try_luck\")"
insert = needle + "\n    if st.session_state.get(\"play_luck_song\", False):\n        show_spotify_player()"
if "show_spotify_player()" in text and "play_luck_song" in text and insert not in text:
    if needle not in text:
        raise RuntimeError("Fant ikke deltaker-knappen Prøv lykken. Sjekk at dette er v4 app.py.")
    text = text.replace(needle, insert)

APP.write_text(text, encoding="utf-8")
print("OK: app.py er patchet med Spotify-spilleren.")
print("Start appen med: streamlit run app.py")
