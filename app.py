
from __future__ import annotations
import json
from pathlib import Path
import pandas as pd
import streamlit as st
from vm2026_logic import (
    GROUPS, GROUP_MATCHES, PHASE_ORDER, POINTS_EXACT_SCORE, POINTS_OUTCOME, POINTS_CHAMPION,
    new_prediction, new_actual_results, qualifiers, compute_bracket, slot_allowed_map,
    find_third_slot_assignment, normalize_score, winner_from_score, score_prediction,
    load_json_bytes, download_json
)

st.set_page_config(page_title="VM 2026 tipping", layout="wide")
st.title("VM 2026 tippekonkurranse")
st.caption("v3: JSON-import fikset med session_state, versjonerte widget keys og rerun.")

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


def init_session():
    defaults = {
        "participant_data": load_local(LOCAL_PARTICIPANT_FILE, new_prediction("")),
        "actual_data": load_local(LOCAL_ACTUAL_FILE, new_actual_results()),
        "participant_ui_version": 0,
        "actual_ui_version": 0,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


def clear_widget_keys(prefix: str):
    for key in list(st.session_state.keys()):
        if str(key).startswith(prefix):
            del st.session_state[key]


def import_box(label: str, target: str, key: str):
    uploaded = st.file_uploader(label, type="json", key=f"{key}_uploader")
    if uploaded and st.button("Importer JSON", key=f"{key}_button"):
        try:
            data = load_json_bytes(uploaded)
        except Exception as exc:
            st.error(f"Kunne ikke lese JSON: {exc}")
            return
        if target == "participant":
            st.session_state.participant_data = data
            st.session_state.participant_ui_version += 1
            clear_widget_keys("p_")
        else:
            st.session_state.actual_data = data
            st.session_state.actual_ui_version += 1
            clear_widget_keys("a_")
        st.success(f"Importerte {uploaded.name}")
        st.rerun()


def score_inputs(prefix: str, team_a: str, team_b: str, current: dict, allow_draw_winner: bool = False) -> dict:
    c1, c2, c3, c4 = st.columns([4, 1, 1, 4])
    c1.markdown(f"**{team_a or 'TBD'}**")
    ga_value = 0 if current.get("goals_a") is None else int(current.get("goals_a"))
    gb_value = 0 if current.get("goals_b") is None else int(current.get("goals_b"))
    ga = c2.number_input("Mål A", 0, 30, ga_value, key=f"{prefix}_ga", label_visibility="collapsed")
    gb = c3.number_input("Mål B", 0, 30, gb_value, key=f"{prefix}_gb", label_visibility="collapsed")
    c4.markdown(f"**{team_b or 'TBD'}**")
    if allow_draw_winner and team_a and team_b and ga == gb:
        options = ["", team_a, team_b]
        old = current.get("winner", "")
        winner = st.selectbox("Vinner etter ekstraomganger/straffer", options, index=options.index(old) if old in options else 0, key=f"{prefix}_winner")
    else:
        winner = winner_from_score(team_a, team_b, ga, gb, "")
    return {"team_a": team_a, "team_b": team_b, "goals_a": int(ga), "goals_b": int(gb), "winner": winner}


def render_group_inputs(data: dict, key_name: str, prefix: str):
    target = data.setdefault(key_name, {})
    for group in GROUPS:
        with st.expander(f"Gruppe {group}", expanded=group in ["A", "B"]):
            for m in [x for x in GROUP_MATCHES if x["group"] == group]:
                mk = str(m["match_no"])
                st.write(f"Kamp {mk}")
                current = normalize_score(target.get(mk))
                target[mk] = score_inputs(f"{prefix}_{key_name}_{mk}", m["team_a"], m["team_b"], current, False)


def render_tables_and_slots(data: dict, prefix: str):
    q = qualifiers(data.get("group_scores", {}))
    cols = st.columns(3)
    for i, group in enumerate(GROUPS):
        with cols[i % 3]:
            st.markdown(f"#### Gruppe {group}")
            st.dataframe(q["tables"][group].drop(columns=["Seed"]), hide_index=True, use_container_width=True)
    st.markdown("### Beste tredjeplasser")
    thirds = q["thirds"].copy()
    thirds.insert(0, "Rang", range(1, len(thirds) + 1))
    thirds["Videre"] = ["Ja" if i < 8 else "Nei" for i in range(len(thirds))]
    st.dataframe(thirds.rename(columns={"group": "Gruppe", "team": "Lag"}), hide_index=True, use_container_width=True)
    st.markdown("### Tredjeplass-slotter")
    overrides = data.setdefault("third_slot_overrides", {})
    adv = q["advancing_thirds"]["group"].tolist()
    auto = find_third_slot_assignment(adv, slot_allowed_map())
    for slot, allowed in slot_allowed_map().items():
        options = [""] + [g for g in allowed if g in adv]
        old = overrides.get(slot, "")
        c1, c2, c3 = st.columns([2, 3, 3])
        c1.write(f"**{slot}**")
        c2.write(f"Auto: {auto.get(slot, '')}")
        val = c3.selectbox("Overstyr", options, index=options.index(old) if old in options else 0, key=f"{prefix}_slot_{slot}", label_visibility="collapsed")
        if val: overrides[slot] = val
        else: overrides.pop(slot, None)


def render_knockout_inputs(data: dict, key_name: str, prefix: str):
    target = data.setdefault(key_name, {})
    bracket = compute_bracket(data.get("group_scores", {}), data.get("third_slot_overrides", {}), target)
    for phase in PHASE_ORDER:
        st.markdown(f"### {phase}")
        for no, m in sorted([(no, x) for no, x in bracket.items() if x["phase"] == phase]):
            st.write(f"Kamp {no}: `{m['seed_a']}` vs `{m['seed_b']}`")
            current = normalize_score(target.get(str(no)))
            target[str(no)] = score_inputs(f"{prefix}_{key_name}_{no}", m["team_a"], m["team_b"], current, True)
        bracket = compute_bracket(data.get("group_scores", {}), data.get("third_slot_overrides", {}), target)
    data["champion"] = bracket.get(104, {}).get("winner", "")
    if data["champion"]: st.success(f"🏆 Mester: {data['champion']}")


def participant_mode():
    st.header("Deltaker: lag tippekupong")
    import_box("Last inn eksisterende JSON-tippekupong", "participant", "participant_import")
    data = st.session_state.participant_data
    prefix = f"p_{st.session_state.participant_ui_version}"
    data["participant"] = st.text_input("Navn", value=data.get("participant", ""), key=f"{prefix}_name").strip()
    tab1, tab2, tab3, tab4 = st.tabs(["1 Gruppespill", "2 Tabeller", "3 Sluttspill", "4 Lagre/eksporter"])
    with tab1: render_group_inputs(data, "group_scores", prefix)
    with tab2: render_tables_and_slots(data, prefix)
    with tab3: render_knockout_inputs(data, "knockout_predictions", prefix)
    with tab4:
        if st.button("Lagre lokalt", key=f"{prefix}_save"):
            save_local(LOCAL_PARTICIPANT_FILE, data); st.success(f"Lagret til {LOCAL_PARTICIPANT_FILE}")
        if st.button("Nullstill deltakerdata", key=f"{prefix}_reset"):
            st.session_state.participant_data = new_prediction(""); st.session_state.participant_ui_version += 1; clear_widget_keys("p_"); st.rerun()
        fname = f"tips_{data.get('participant','deltaker').replace(' ', '_')}.json"
        st.download_button("Last ned min JSON-tippekupong", download_json(data), fname, "application/json", key=f"{prefix}_download")
        st.json(data, expanded=False)


def admin_mode():
    st.header("Admin: fasit og ledertabell")
    import_box("Last inn fasit-JSON", "actual", "actual_import")
    actual = st.session_state.actual_data
    prefix = f"a_{st.session_state.actual_ui_version}"
    tab1, tab2, tab3, tab4 = st.tabs(["1 Fasit gruppespill", "2 Fasit sluttspill", "3 Importer tips og ledertabell", "4 Eksporter fasit"])
    with tab1:
        render_group_inputs(actual, "group_scores", prefix)
        render_tables_and_slots(actual, prefix)
    with tab2:
        render_knockout_inputs(actual, "knockout_results", prefix)
    with tab3:
        uploads = st.file_uploader("Last opp alle deltakernes JSON-filer", type="json", accept_multiple_files=True, key=f"{prefix}_participant_uploads")
        if uploads:
            scored, details = [], {}
            for up in uploads:
                try:
                    pred = load_json_bytes(up)
                    res = score_prediction(pred, actual)
                    scored.append({"Deltaker": res["participant"], "Kamppoeng": res["match_points"], "Mesterbonus": res["champion_bonus"], "Totalt": res["total"], "Mestertips": pred.get("champion", "")})
                    details[res["participant"]] = res["details"]
                except Exception as exc:
                    st.error(f"Kunne ikke lese {up.name}: {exc}")
            if scored:
                df = pd.DataFrame(scored).sort_values(["Totalt", "Kamppoeng"], ascending=[False, False]).reset_index(drop=True)
                df.insert(0, "Plass", range(1, len(df)+1))
                st.dataframe(df, hide_index=True, use_container_width=True)
                st.download_button("Last ned ledertabell CSV", df.to_csv(index=False).encode("utf-8"), "ledertabell_vm2026.csv", "text/csv", key=f"{prefix}_csv")
                with st.expander("Detaljer per deltaker"):
                    for participant, rows in details.items():
                        st.markdown(f"#### {participant}"); st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)
        st.markdown("### Poengregler")
        st.write(f"- Riktig resultat: **{POINTS_EXACT_SCORE} poeng**")
        st.write(f"- Riktig utfall (H/U/B): **{POINTS_OUTCOME} poeng**")
        st.write(f"- Bonus riktig mester: **{POINTS_CHAMPION} poeng**")
    with tab4:
        if st.button("Lagre fasit lokalt", key=f"{prefix}_save_actual"):
            save_local(LOCAL_ACTUAL_FILE, actual); st.success(f"Lagret til {LOCAL_ACTUAL_FILE}")
        if st.button("Nullstill fasit", key=f"{prefix}_reset_actual"):
            st.session_state.actual_data = new_actual_results(); st.session_state.actual_ui_version += 1; clear_widget_keys("a_"); st.rerun()
        st.download_button("Last ned fasit-JSON", download_json(actual), "actual_results_vm2026.json", "application/json", key=f"{prefix}_download_actual")
        st.json(actual, expanded=False)


init_session()
mode = st.sidebar.radio("Modus", ["Deltaker", "Admin / fasit og leaderboard"])
st.sidebar.markdown("### Poeng")
st.sidebar.write(f"Riktig resultat: {POINTS_EXACT_SCORE}")
st.sidebar.write(f"Riktig utfall: {POINTS_OUTCOME}")
st.sidebar.write(f"Mesterbonus: {POINTS_CHAMPION}")
st.sidebar.caption("v3 fikser JSON-import ved å gi widgets nye keys etter import.")
participant_mode() if mode == "Deltaker" else admin_mode()
