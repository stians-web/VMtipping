
# VM 2026 tippekonkurranse – Streamlit v4

Ny funksjon: **Prøv lykken!**

Knappen fyller ut hele tippekupongen automatisk:

- gruppespillresultater
- gruppetabeller
- 16-delsfinaler
- åttedelsfinaler
- kvartfinaler
- semifinaler
- bronsefinale
- finale
- mester

Forslagene er randomiserte, men vektet etter omtrentlige odds/styrker fra offentlige oddsoversikter. Derfor får du ulike resultater hver gang du trykker.

## Kjøring

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Viktig

Dette er laget for en sosial tippekonkurranse. Det er ikke bettingråd.

## JSON-import

v4 beholder fiksen fra v3: ved import av JSON tømmes gamle widget-keys, intern ui-versjon økes, og appen rerunner slik at importerte verdier vises.
