
from __future__ import annotations

import json
from pathlib import Path
import pandas as pd
import streamlit as st

from vm2026_logic import (
    GROUPS, GROUP_MATCHES, PHASE_ORDER, POINTS_EXACT_SCORE, POINTS_OUTCOME, POINTS_CHAMPION,
    new_prediction, new_actual_results, group_table, qualifiers, compute_bracket,
    slot_allowed_map, find_third_slot_assignment, normalise_score_obj, winner_from_score,
    all_matches_for_scoring, score_prediction, load_json_bytes, download_json
)

st.set_page_config(page_title="VM 2026 tipping", layout="wide")
st.title("VM 2026 tippekonkurranse")
st.caption("Ny versjon: korrekte norske sluttspillnavn, mål-tips i sluttspillet, JSON-eksport/import og ledertabell mot fasit.")

DATA_DIR = Path("data")
DATA_DIR.mkdir(exist_ok=True)
LOCAL_PARTICIPANT_FILE = DATA_DIR / "min_tippekupong.json"
LOCAL_ACTUAL_FILE = DATA_DIR / "actual_results.json"


def load_local(path: Path, fallback: dict) -> dict:
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return fallback
    return fallback


def save_local(path: Path, data: dict) -> None:
    path.write_text(download_json(data), encoding="utf-8")


def score_inputs(prefix: str, team_a: str, team_b: str, current: dict, allow_draw_winner: bool = False) -> dict:
    c1, c2, c3, c4 = st.columns([4, 1, 1, 4])
    c1.markdown(f"**{team_a or 'TBD'}**")
    goals_a = c2.number_input("Mål A", min_value=0, max_value=30, value=int(current.get("goals_a") or 0), key=f"{prefix}_ga", label_visibility="collapsed")
    goals_b = c3.number_input("Mål B", min_value=0, max_value=30, value=int(current.get("goals_b") or 0), key=f"{prefix}_gb", label_visibility="collapsed")
    c4.markdown(f"**{team_b or 'TBD'}**")
    winner = ""
    if allow_draw_winner and team_a and team_b and goals_a == goals_b:
        options = ["", team_a, team_b]
        old = current.get("winner", "")
        winner = st.selectbox("Vinner etter ekstraomganger/straffer", options, index=options.index(old) if old in options else 0, key=f"{prefix}_winner")
    else:
        winner = winner_from_score(team_a, team_b, goals_a, goals_b, "")
    return {"team_a": team_a, "team_b": team_b, "goals_a": int(goals_a), "goals_b": int(goals_b), "winner": winner}


def render_group_inputs(data: dict, key_name: str) -> None:
    target = data.setdefault(key_name, {})
    for group in GROUPS:
        with st.expander(f"Gruppe {group}", expanded=group in ["A", "B"]):
            for m in [x for x in GROUP_MATCHES if x["group"] == group]:
                key = str(m["match_no"])
                current = normalise_score_obj(target.get(key))
                st.write(f"Kamp {key}")
                target[key] = score_inputs(f"{key_name}_{key}", m["team_a"], m["team_b"], current, allow_draw_winner=False)


def render_tables_and_slots(data: dict) -> None:
    q = qualifiers(data.get("group_scores", {}))
    cols = st.columns(3)
    for i, group in enumerate(GROUPS):
        with cols[i % 3]:
            st.markdown(f"#### Gruppe {group}")
            st.dataframe(q["tables"][group].drop(columns=["Seed"]), hide_index=True, use_container_width=True)

    st.markdown("### Beste tredjeplasser")
    third_df = q["thirds"].copy()
    third_df.insert(0, "Rang", range(1, len(third_df) + 1))
    third_df["Videre"] = ["Ja" if i < 8 else "Nei" for i in range(len(third_df))]
    st.dataframe(third_df.rename(columns={"group": "Gruppe", "team": "Lag"}), hide_index=True, use_container_width=True)

    st.markdown("### Tredjeplass-slotter")
    st.caption("Auto finner en gyldig fordeling. Ved behov kan du overstyre for å matche offisiell kombinasjon nøyaktig.")
    overrides = data.setdefault("third_slot_overrides", {})
    adv_groups = q["advancing_thirds"]["group"].tolist()
    auto = find_third_slot_assignment(adv_groups, slot_allowed_map())
    for slot, allowed in slot_allowed_map().items():
        options = [""] + [g for g in allowed if g in adv_groups]
        old = overrides.get(slot, "")
        c1, c2, c3 = st.columns([2, 3, 3])
        c1.write(f"**{slot}**")
        c2.write(f"Auto: {auto.get(slot, '')}")
        val = c3.selectbox("Overstyr", options, index=options.index(old) if old in options else 0, key=f"slot_{slot}", label_visibility="collapsed")
        if val:
            overrides[slot] = val
        else:
            overrides.pop(slot, None)


def render_knockout_inputs(data: dict, key_name: str) -> None:
    target = data.setdefault(key_name, {})
    bracket = compute_bracket(data.get("group_scores", {}), data.get("third_slot_overrides", {}), target)
    for phase in PHASE_ORDER:
        st.markdown(f"### {phase}")
        phase_matches = [(no, m) for no, m in bracket.items() if m["phase"] == phase]
        for match_no, m in sorted(phase_matches):
            st.write(f"Kamp {match_no}: `{m['seed_a']}` vs `{m['seed_b']}`")
            current = normalise_score_obj(target.get(str(match_no)))
            target[str(match_no)] = score_inputs(f"{key_name}_{match_no}", m["team_a"], m["team_b"], current, allow_draw_winner=True)
        # Oppdater bracket etter hver runde slik at neste runde får riktige lag.
        bracket = compute_bracket(data.get("group_scores", {}), data.get("third_slot_overrides", {}), target)
    final_winner = bracket.get(104, {}).get("winner", "")
    data["champion"] = final_winner
    if final_winner:
        st.success(f"🏆 Mester: {final_winner}")


def participant_mode() -> None:
    st.header("Deltaker: lag tippekupong")
    uploaded = st.file_uploader("Last inn eksisterende JSON-tippekupong", type="json")
    if uploaded:
        data = load_json_bytes(uploaded)
    else:
        data = load_local(LOCAL_PARTICIPANT_FILE, new_prediction(""))

    name = st.text_input("Navn", value=data.get("participant", ""))
    data["participant"] = name.strip()

    tab1, tab2, tab3, tab4 = st.tabs(["1 Gruppespill", "2 Tabeller", "3 Sluttspill", "4 Lagre/eksporter"])
    with tab1:
        render_group_inputs(data, "group_scores")
    with tab2:
        render_tables_and_slots(data)
    with tab3:
        render_knockout_inputs(data, "knockout_predictions")
    with tab4:
        if st.button("Lagre lokalt"):
            save_local(LOCAL_PARTICIPANT_FILE, data)
            st.success(f"Lagret til {LOCAL_PARTICIPANT_FILE}")
        file_name = f"tips_{data.get('participant','deltaker').replace(' ', '_')}.json"
        st.download_button("Last ned min JSON-tippekupong", data=download_json(data), file_name=file_name, mime="application/json")
        st.json(data, expanded=False)


def admin_mode() -> None:
    st.header("Admin: fasit og ledertabell")
    actual = load_local(LOCAL_ACTUAL_FILE, new_actual_results())
    actual_upload = st.file_uploader("Last inn fasit-JSON hvis du har", type="json", key="actual_upload")
    if actual_upload:
        actual = load_json_bytes(actual_upload)

    tab1, tab2, tab3, tab4 = st.tabs(["1 Fasit gruppespill", "2 Fasit sluttspill", "3 Importer tips og ledertabell", "4 Eksporter fasit"])
    with tab1:
        st.info("Fyll inn virkelige gruppespillresultater etter hvert som kampene spilles.")
        render_group_inputs(actual, "group_scores")
        render_tables_and_slots(actual)
    with tab2:
        st.info("Sluttspill-lagene bygges fra fasit-gruppespillet. Ved uavgjort i sluttspill velger du vinner på straffer/ekstraomganger.")
        render_knockout_inputs(actual, "knockout_results")
    with tab3:
        st.markdown("### Samle deltakernes JSON-filer")
        st.write("Be alle deltakere laste ned sin JSON-tippekupong og sende den til deg. Last opp alle filene her samtidig.")
        uploads = st.file_uploader("Last opp alle deltakernes JSON-filer", type="json", accept_multiple_files=True)
        if uploads:
            scored = []
            details = {}
            for up in uploads:
                try:
                    pred = load_json_bytes(up)
                    res = score_prediction(pred, actual)
                    scored.append({
                        "Deltaker": res["participant"],
                        "Kamppoeng": res["match_points"],
                        "Mesterbonus": res["champion_bonus"],
                        "Totalt": res["total"],
                        "Mestertips": pred.get("champion", ""),
                    })
                    details[res["participant"]] = res["details"]
                except Exception as e:
                    st.error(f"Kunne ikke lese {up.name}: {e}")
            if scored:
                df = pd.DataFrame(scored).sort_values(["Totalt", "Kamppoeng"], ascending=[False, False]).reset_index(drop=True)
                df.insert(0, "Plass", range(1, len(df) + 1))
                st.dataframe(df, hide_index=True, use_container_width=True)
                csv = df.to_csv(index=False).encode("utf-8")
                st.download_button("Last ned ledertabell CSV", csv, file_name="ledertabell_vm2026.csv", mime="text/csv")
                with st.expander("Detaljer per deltaker"):
                    for participant, rows in details.items():
                        st.markdown(f"#### {participant}")
                        st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)
        else:
            st.info("Ingen deltakerfiler lastet opp ennå.")

        st.markdown("### Poengregler")
        st.write(f"- Riktig resultat: **{POINTS_EXACT_SCORE} poeng**")
        st.write(f"- Riktig utfall (H/U/B): **{POINTS_OUTCOME} poeng**")
        st.write(f"- Bonus riktig mester: **{POINTS_CHAMPION} poeng**")
        st.caption("For sluttspill gis kamppoeng bare hvis deltakerens lag i den aktuelle kampen matcher fasitkampen. Ved likt målresultat i sluttspill brukes valgt vinner kun til å føre bracketen videre og til mesterbonus.")
    with tab4:
        if st.button("Lagre fasit lokalt"):
            save_local(LOCAL_ACTUAL_FILE, actual)
            st.success(f"Lagret til {LOCAL_ACTUAL_FILE}")
        st.download_button("Last ned fasit-JSON", data=download_json(actual), file_name="actual_results_vm2026.json", mime="application/json")
        st.json(actual, expanded=False)


mode = st.sidebar.radio("Modus", ["Deltaker", "Admin / fasit og leaderboard"])
st.sidebar.markdown("### Poeng")
st.sidebar.write(f"Riktig resultat: {POINTS_EXACT_SCORE}")
st.sidebar.write(f"Riktig utfall: {POINTS_OUTCOME}")
st.sidebar.write(f"Mesterbonus: {POINTS_CHAMPION}")

if mode == "Deltaker":
    participant_mode()
else:
    admin_mode()
