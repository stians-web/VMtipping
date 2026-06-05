# Spotify patch v5.2

Denne erstatter patchen som feilet med `NameError: name 'f' is not defined`.

## Bruk

Legg `spotify_patch_v5_2.py` i samme mappe som `app.py` fra v4 og kjør:

```powershell
python spotify_patch_v5_2.py
streamlit run app.py
```

Patchen legger inn Spotify-spilleren for låten etter at brukeren trykker **Prøv lykken!**.
