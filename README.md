
# VM 2026 tippekonkurranse – Streamlit v3

Denne versjonen fikser problemet der innlastet JSON ikke oppdaterte feltene i skjemaet.

## Hvorfor skjedde feilen?

Streamlit lagrer widget-verdier i `st.session_state` når widgets har `key`. Når en JSON-fil senere lastes inn, kan gamle widget-verdier overstyre verdiene som kommer fra JSON.

v3 løser dette ved å:

1. lagre deltakerdata og fasit i `st.session_state`
2. bruke en importknapp for JSON
3. øke en intern `ui_version` etter import
4. slette gamle widget-keys
5. kjøre `st.rerun()`

Da bygges skjemaet på nytt, og importerte resultater vises riktig.

## Kjøring

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Arbeidsflyt

### Deltaker

1. Velg **Deltaker**.
2. Fyll inn tips eller importer eksisterende JSON.
3. Last ned JSON-tippekupong.
4. Send filen til administrator.

### Admin

1. Velg **Admin / fasit og leaderboard**.
2. Fyll inn fasit eller importer fasit-JSON.
3. Last opp alle deltaker-JSON-filer.
4. Appen lager ledertabell.

## Poengregler

- Riktig resultat: 3 poeng
- Riktig utfall (H/U/B): 1 poeng
- Bonus riktig mester: 5 poeng

## Rundenavn

- Round of 32 = 16-delsfinaler
- Round of 16 = Åttedelsfinaler
- Deretter kvartfinaler, semifinaler, bronsefinale og finale
