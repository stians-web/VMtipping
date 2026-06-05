
# VM 2026 tippekonkurranse – v5 Spotify

Dette er en ren, GitHub-klar pakke. Ingen patchfiler trengs.

## Filer

- `app.py`
- `vm2026_logic.py`
- `requirements.txt`
- `README.md`

## Funksjoner

- Prøv lykken! fyller ut hele tippekupongen med randomiserte, oddsvektede tips.
- Spotify-spilleren for `6z5sjLABC6XkNviIYeFUqF` vises etter Prøv lykken.
- Deltakere kan laste ned JSON.
- Admin kan laste opp JSON-filer og beregne ledertabell.

## Kjøring

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Streamlit Cloud

Legg alle fire filene i repo-root eller samme mappe, og sett main file path til `app.py`.

Merk: Spotify embed autoplay er normalt blokkert av nettleser/Spotify. Brukeren må vanligvis trykke Play i spilleren.
