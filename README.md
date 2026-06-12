# VM 2026 tippekonkurranse – v7.1

Denne versjonen fikser Streamlit secrets-feilen når ingen `.streamlit/secrets.toml` finnes lokalt.

## Viktig scoring

Kun kamper som er markert som **Kamp ferdig/spilt** gir poeng. Ikke-spilte kamper gir 0 poeng, selv om resultatfeltet står på 0–0.

## API-Football

API-nøkkel kan legges inn manuelt i appen, eller som secret på Streamlit Cloud:

```toml
API_FOOTBALL_KEY = "din_api_nøkkel"
```

## Kjøring

```bash
pip install -r requirements.txt
streamlit run app.py
```
