
from __future__ import annotations
import json
from pathlib import Path
import pandas as pd
import requests
import streamlit as st
import streamlit.components.v1 as components
from vm2026_logic import *

st.set_page_config(page_title="VM 2026 tipping", layout="wide")
st.title("VM 2026 tippekonkurranse")
st.caption("v7.1: bare spilte kamper rettes + API-Football uten secrets-feil + Spotify")
SPOTIFY_EMBED_URL="https://open.spotify.com/embed/track/6z5sjLABC6XkNviIYeFUqF?utm_source=generator"
def show_spotify_player(): st.markdown("### 🎵 Prøv lykken-sang"); components.iframe(SPOTIFY_EMBED_URL,height=152,scrolling=False)
DATA_DIR=Path("data"); DATA_DIR.mkdir(exist_ok=True)
LOCAL_PARTICIPANT_FILE=DATA_DIR/"min_tippekupong.json"; LOCAL_ACTUAL_FILE=DATA_DIR/"actual_results.json"
def load_local(path,fallback):
    if path.exists():
        try: return json.loads(path.read_text(encoding="utf-8"))
        except Exception: return fallback
    return fallback
def save_local(path,data): path.write_text(download_json(data),encoding="utf-8")
def get_secret(name, default=""):
    try: return st.secrets.get(name, default)
    except Exception: return default
def init_session():
    defaults={"participant_data":load_local(LOCAL_PARTICIPANT_FILE,new_prediction("")),"actual_data":load_local(LOCAL_ACTUAL_FILE,new_actual_results()),"participant_ui_version":0,"actual_ui_version":0,"play_luck_song":False}
    for k,v in defaults.items():
        if k not in st.session_state: st.session_state[k]=v
def clear_widget_keys(prefix):
    for key in list(st.session_state.keys()):
        if str(key).startswith(prefix): del st.session_state[key]
def import_box(label,target,key):
    uploaded=st.file_uploader(label,type="json",key=f"{key}_uploader")
    if uploaded and st.button("Importer JSON",key=f"{key}_button"):
        data=load_json_bytes(uploaded)
        if target=="participant": st.session_state.participant_data=data; st.session_state.participant_ui_version+=1; clear_widget_keys("p_")
        else: st.session_state.actual_data=data; st.session_state.actual_ui_version+=1; clear_widget_keys("a_")
        st.rerun()
def try_luck_button(label,target,key):
    if st.button(label,key=key,type="primary"):
        if target=="participant":
            name=st.session_state.participant_data.get("participant",""); fill_try_luck(st.session_state.participant_data,"knockout_predictions"); st.session_state.participant_data["participant"]=name; st.session_state.participant_ui_version+=1; clear_widget_keys("p_")
        else:
            fill_try_luck(st.session_state.actual_data,"knockout_results"); st.session_state.actual_ui_version+=1; clear_widget_keys("a_")
        st.session_state.play_luck_song=True; st.toast("Prøv lykken er kjørt – ny kupong generert!"); st.rerun()
def score_inputs(prefix,a,b,current,allow_draw_winner=False, actual_mode=False):
    current=normalize_score(current); played=current.get("played",False)
    if actual_mode: played=st.checkbox("Kamp ferdig/spilt",value=played,key=f"{prefix}_played")
    c1,c2,c3,c4=st.columns([4,1,1,4]); c1.markdown(f"**{a or 'TBD'}**")
    ga=c2.number_input("Mål A",0,30,0 if current.get("goals_a") is None else int(current.get("goals_a")),key=f"{prefix}_ga",label_visibility="collapsed")
    gb=c3.number_input("Mål B",0,30,0 if current.get("goals_b") is None else int(current.get("goals_b")),key=f"{prefix}_gb",label_visibility="collapsed"); c4.markdown(f"**{b or 'TBD'}**")
    if actual_mode and not played: return {"team_a":a,"team_b":b,"goals_a":None,"goals_b":None,"winner":"","played":False,"date":current.get("date",""),"status":current.get("status","")}
    if allow_draw_winner and a and b and ga==gb:
        opts=["",a,b]; old=current.get("winner",""); w=st.selectbox("Vinner etter ekstraomganger/straffer",opts,index=opts.index(old) if old in opts else 0,key=f"{prefix}_winner")
    else: w=winner_from_score(a,b,ga,gb,"")
    return {"team_a":a,"team_b":b,"goals_a":int(ga),"goals_b":int(gb),"winner":w,"played":bool(played),"date":current.get("date",""),"status":current.get("status","")}
def render_group_inputs(data,key_name,prefix,actual_mode=False):
    target=data.setdefault(key_name,{})
    for g in GROUPS:
        with st.expander(f"Gruppe {g}",expanded=g in ["A","B"]):
            for m in [x for x in GROUP_MATCHES if x["group"]==g]:
                mk=str(m["match_no"]); cur=normalize_score(target.get(mk)); label=f"Kamp {mk}"
                if actual_mode and cur.get("played"): label += f" ✅ {format_score(cur)}"
                elif actual_mode: label += " ⏳ ikke rettet"
                st.write(label); target[mk]=score_inputs(f"{prefix}_{key_name}_{mk}",m["team_a"],m["team_b"],cur,False,actual_mode)
def render_tables_and_slots(data,prefix):
    q=qualifiers(data.get("group_scores",{})); cols=st.columns(3)
    for i,g in enumerate(GROUPS):
        with cols[i%3]: st.markdown(f"#### Gruppe {g}"); st.dataframe(q["tables"][g].drop(columns=["Seed"]),hide_index=True,use_container_width=True)
    st.markdown("### Beste tredjeplasser"); thirds=q["thirds"].copy(); thirds.insert(0,"Rang",range(1,len(thirds)+1)); thirds["Videre"]=["Ja" if i<8 else "Nei" for i in range(len(thirds))]
    st.dataframe(thirds.rename(columns={"group":"Gruppe","team":"Lag"}),hide_index=True,use_container_width=True)
    overrides=data.setdefault("third_slot_overrides",{}); adv=q["advancing_thirds"]["group"].tolist(); auto=find_third_slot_assignment(adv,slot_allowed_map())
    with st.expander("Tredjeplass-slotter"):
        for slot,allowed in slot_allowed_map().items():
            options=[""]+[g for g in allowed if g in adv]; old=overrides.get(slot,""); c1,c2,c3=st.columns([2,3,3]); c1.write(f"**{slot}**"); c2.write(f"Auto: {auto.get(slot,'')}")
            val=c3.selectbox("Overstyr",options,index=options.index(old) if old in options else 0,key=f"{prefix}_slot_{slot}",label_visibility="collapsed")
            if val: overrides[slot]=val
            else: overrides.pop(slot,None)
def render_knockout_inputs(data,key_name,prefix,actual_mode=False):
    target=data.setdefault(key_name,{}); br=compute_bracket(data.get("group_scores",{}),data.get("third_slot_overrides",{}),target)
    for phase in PHASE_ORDER:
        st.markdown(f"### {phase}")
        for no,m in sorted([(no,x) for no,x in br.items() if x["phase"]==phase]):
            cur=normalize_score(target.get(str(no))); st.write(f"Kamp {no}: `{m['seed_a']}` vs `{m['seed_b']}`")
            target[str(no)]=score_inputs(f"{prefix}_{key_name}_{no}",m["team_a"],m["team_b"],cur,True,actual_mode)
        br=compute_bracket(data.get("group_scores",{}),data.get("third_slot_overrides",{}),target)
    data["champion"]=br.get(104,{}).get("winner","")
    if data["champion"]: st.success(f"🏆 Mester: {data['champion']}")
def fetch_api_football_fixtures(api_key):
    url="https://v3.football.api-sports.io/fixtures"; headers={"x-apisports-key":api_key}; params={"league":1,"season":2026}
    r=requests.get(url,headers=headers,params=params,timeout=30); r.raise_for_status(); return r.json().get("response",[])
def participant_mode():
    st.header("Deltaker: lag tippekupong"); import_box("Last inn eksisterende JSON-tippekupong","participant","participant_import")
    data=st.session_state.participant_data; prefix=f"p_{st.session_state.participant_ui_version}"; data["participant"]=st.text_input("Navn",value=data.get("participant",""),key=f"{prefix}_name").strip()
    try_luck_button("Prøv lykken!","participant",f"{prefix}_try_luck")
    if st.session_state.get("play_luck_song",False): show_spotify_player()
    tab1,tab2,tab3,tab4=st.tabs(["1 Gruppespill","2 Tabeller","3 Sluttspill","4 Lagre/eksporter"])
    with tab1: render_group_inputs(data,"group_scores",prefix,False)
    with tab2: render_tables_and_slots(data,prefix)
    with tab3: render_knockout_inputs(data,"knockout_predictions",prefix,False)
    with tab4:
        if st.button("Nullstill deltakerdata",key=f"{prefix}_reset"): st.session_state.participant_data=new_prediction(""); st.session_state.participant_ui_version+=1; st.session_state.play_luck_song=False; clear_widget_keys("p_"); st.rerun()
        fname=f"tips_{data.get('participant','deltaker').replace(' ','_')}.json"; st.download_button("Last ned min JSON-tippekupong",download_json(data),fname,"application/json",key=f"{prefix}_download"); st.json(data,expanded=False)
def admin_mode():
    st.header("Admin: fasit og ledertabell"); import_box("Last inn fasit-JSON","actual","actual_import")
    actual=st.session_state.actual_data; prefix=f"a_{st.session_state.actual_ui_version}"
    with st.expander("API-Football automatisk fasit",expanded=False):
        st.write("Henter VM 2026 med league=1 og season=2026. Kun kamper med status FT/AET/PEN markeres som spilt.")
        api_key=st.text_input("API-nøkkel",value=get_secret("API_FOOTBALL_KEY",""),type="password")
        if st.button("Hent resultater fra API-Football",disabled=not api_key,key=f"{prefix}_api_fetch"):
            try:
                fixtures=fetch_api_football_fixtures(api_key); res=apply_api_fixtures(actual,fixtures); st.success(f"Oppdatert: {res['updated']} kamper. Hoppet over: {res['skipped']}"); st.session_state.actual_ui_version+=1; clear_widget_keys("a_"); st.rerun()
            except Exception as exc: st.error(f"API-feil: {exc}")
    tab1,tab2,tab3,tab4=st.tabs(["1 Fasit gruppespill","2 Fasit sluttspill","3 Importer tips og ledertabell","4 Eksporter fasit"])
    with tab1: render_group_inputs(actual,"group_scores",prefix,True); render_tables_and_slots(actual,prefix)
    with tab2: render_knockout_inputs(actual,"knockout_results",prefix,True)
    with tab3:
        played=sum(1 for m in all_matches_for_scoring(actual,True).values() if m.get("played")); st.info(f"Kamper som rettes nå: {played} av 104")
        uploads=st.file_uploader("Last opp alle deltakernes JSON-filer",type="json",accept_multiple_files=True,key=f"{prefix}_participant_uploads")
        if uploads:
            scored=[]; details={}; raw={}
            for up in uploads:
                try:
                    pred=load_json_bytes(up); res=score_prediction(pred,actual); p=res["participant"]
                    scored.append({"Deltaker":p,"Kamppoeng":res["match_points"],"Mesterbonus":res["champion_bonus"],"Totalt":res["total"],"Rettede kamper":res["corrected_matches"],"Mestertips":pred.get("champion","")}); details[p]=res["details"]; raw[p]=pred
                except Exception as exc: st.error(f"Kunne ikke lese {up.name}: {exc}")
            if scored:
                df=pd.DataFrame(scored).sort_values(["Totalt","Kamppoeng"],ascending=[False,False]).reset_index(drop=True); df.insert(0,"Plass",range(1,len(df)+1)); st.dataframe(df,hide_index=True,use_container_width=True)
                st.download_button("Last ned ledertabell CSV",df.to_csv(index=False).encode("utf-8"),"ledertabell_vm2026.csv","text/csv",key=f"{prefix}_csv")
                st.markdown("### Deltakernes valg"); chosen=st.selectbox("Velg deltaker",list(details.keys()),key=f"{prefix}_details_participant")
                if chosen: ddf=pd.DataFrame(details[chosen]); st.dataframe(ddf,hide_index=True,use_container_width=True)
                with st.expander("Rå JSON per deltaker"):
                    p=st.selectbox("Velg deltaker for rå JSON",list(raw.keys()),key=f"{prefix}_raw_json_participant"); st.json(raw[p],expanded=False)
    with tab4:
        if st.button("Lagre fasit lokalt",key=f"{prefix}_save_actual"): save_local(LOCAL_ACTUAL_FILE,actual); st.success("Lagret fasit lokalt")
        if st.button("Nullstill fasit",key=f"{prefix}_reset_actual"): st.session_state.actual_data=new_actual_results(); st.session_state.actual_ui_version+=1; clear_widget_keys("a_"); st.rerun()
        st.download_button("Last ned fasit-JSON",download_json(actual),"actual_results_vm2026.json","application/json",key=f"{prefix}_download_actual"); st.json(actual,expanded=False)
init_session(); mode=st.sidebar.radio("Modus",["Deltaker","Admin / fasit og leaderboard"])
st.sidebar.markdown("### Poeng"); st.sidebar.write(f"Riktig resultat: {POINTS_EXACT_SCORE}"); st.sidebar.write(f"Riktig utfall: {POINTS_OUTCOME}"); st.sidebar.write(f"Mesterbonus: {POINTS_CHAMPION}")
participant_mode() if mode=="Deltaker" else admin_mode()
