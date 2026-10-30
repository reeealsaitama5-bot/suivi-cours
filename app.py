import html
import re
import uuid

import gspread
import streamlit as st
from google.oauth2.service_account import Credentials

STATUTS = ["À faire", "En cours", "Terminé"]
PRIOS = {0: "Sans priorité", 1: "Basse", 2: "Moyenne", 3: "Haute"}
PRIO_ICONES = {0: "⚪", 1: "🔵", 2: "🟠", 3: "🔴"}
PRIO_COULEURS = {1: "#4A6FA5", 2: "#B7791F", 3: "#C2410C"}
PALETTE = ["#0F766E", "#C2410C", "#4A6FA5", "#B7791F", "#2F855A", "#B83280"]
HEX = re.compile(r"^#[0-9a-fA-F]{6}$")
EMOJIS = [
    ("math", "📐"), ("franç", "📖"), ("fran", "📖"), ("angl", "🇬🇧"), ("hist", "🏛️"),
    ("géo", "🌍"), ("geo", "🌍"), ("phys", "⚛️"), ("chim", "🧪"), ("bio", "🧬"),
    ("svt", "🧬"), ("info", "💻"), ("philo", "💭"), ("sport", "🏃"), ("musi", "🎵"),
    ("art", "🎨"), ("écon", "📈"), ("econ", "📈"), ("droit", "⚖️"), ("espa", "🇪🇸"),
    ("allem", "🇩🇪"), ("stat", "📊"),
]
EN_TETES = {
    "matieres": ["id", "nom", "couleur", "image"],
    "taches": ["id", "matiere", "titre", "statut", "prio"],
}
SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

st.set_page_config(page_title="Mon suivi de cours", page_icon="📚", layout="centered")

CSS = """
@import url('https://fonts.googleapis.com/css2?family=Bricolage+Grotesque:wght@400;600;800&display=swap');
.stApp, .stApp p, .stApp label, .stApp button, .stApp input {font-family:'Bricolage Grotesque',system-ui,sans-serif}
#MainMenu, footer {visibility:hidden}
.block-container {max-width:860px; padding-top:1.5rem}
.hero {display:flex; align-items:center; justify-content:space-between; gap:16px; background:#16273B; color:#fff; border-radius:20px; padding:24px 28px; margin-bottom:16px}
.hero .ht {font-size:2.3rem; font-weight:800; letter-spacing:-.02em; line-height:1.1; margin-bottom:8px}
.hero .hp {color:#C9D6E2; font-size:1.05rem}
.hero .art {width:190px; flex:none}
.stats {display:grid; grid-template-columns:1.2fr 1fr 1fr 1fr; gap:12px; margin-bottom:18px}
.stat {background:#fff; border:1px solid #D3DDD9; border-radius:16px; padding:14px 16px; display:flex; align-items:center; gap:12px; transition:transform .2s, box-shadow .2s}
.stat:hover {transform:translateY(-3px); box-shadow:0 8px 20px rgba(22,39,59,.12)}
.stat b {font-size:1.8rem; line-height:1; display:block; color:#16273B}
.stat small {color:#5D6B7A}
.ring {width:68px; height:68px; flex:none; border-radius:50%; display:grid; place-items:center; background:conic-gradient(#0F766E var(--p), #D3DDD9 0)}
.ring span {width:52px; height:52px; border-radius:50%; background:#fff; display:grid; place-items:center; font-weight:800; font-size:.95rem; color:#16273B}
.cover {border-radius:14px; padding:16px 18px 14px; color:#fff; margin-bottom:6px}
.cov {display:flex; align-items:center; gap:12px}
.cov .emo {font-size:2rem}
.cov .cn {font-size:1.3rem; font-weight:800; line-height:1.15}
.cov small {opacity:.92}
.cov .pct {margin-left:auto; font-size:1.8rem; font-weight:800}
.bar {height:8px; background:rgba(255,255,255,.32); border-radius:99px; margin-top:12px; overflow:hidden}
.bar i {display:block; height:100%; background:#fff; border-radius:99px; animation:grow .9s ease-out}
@keyframes grow {from {width:0}}
.tt {padding:7px 0; line-height:1.35; color:#16273B}
.tt.done {text-decoration:line-through; color:#8A97A4}
.pill {display:inline-block; margin-left:8px; font-size:.75rem; font-weight:600; padding:1px 9px; border-radius:99px; border:1px solid currentColor; text-decoration:none}
@media (max-width:640px) {.hero .art {display:none} .stats {grid-template-columns:1fr 1fr}}
"""
st.markdown(f"<style>{CSS}</style>", unsafe_allow_html=True)

ART = """<svg class="art" viewBox="0 0 220 140" aria-hidden="true">
<circle cx="172" cy="34" r="22" fill="#F2C14E"/>
<rect x="30" y="96" width="140" height="20" rx="4" fill="#0F766E"/>
<rect x="42" y="74" width="116" height="22" rx="4" fill="#E4572E"/>
<rect x="24" y="54" width="124" height="20" rx="4" fill="#4A6FA5"/>
<rect x="36" y="118" width="150" height="6" rx="3" fill="#000" opacity=".25"/>
<g transform="rotate(-28 170 100)"><rect x="150" y="92" width="64" height="12" rx="2" fill="#F2C14E"/>
<polygon points="214,92 234,98 214,104" fill="#F4D9B0"/><rect x="150" y="92" width="10" height="12" fill="#E08E8E"/></g>
</svg>"""


# ---------- Google Sheets ----------
@st.cache_resource
def get_classeur():
    creds = Credentials.from_service_account_info(
        dict(st.secrets["gcp_service_account"]), scopes=SCOPES
    )
    return gspread.authorize(creds).open_by_key(st.secrets["sheet_id"])


def get_feuille(nom):
    classeur = get_classeur()
    try:
        return classeur.worksheet(nom)
    except gspread.WorksheetNotFound:
        ws = classeur.add_worksheet(title=nom, rows=200, cols=len(EN_TETES[nom]))
        ws.update(range_name="A1", values=[EN_TETES[nom]])
        return ws


def charger():
    matieres = get_feuille("matieres").get_all_records(numericise_ignore=["all"])
    taches = get_feuille("taches").get_all_records(numericise_ignore=["all"])
    for i, m in enumerate(matieres):
        if not HEX.match(str(m.get("couleur", ""))):
            m["couleur"] = PALETTE[i % len(PALETTE)]
        m["image"] = str(m.get("image", ""))
    for t in taches:
        t["statut"] = int(t["statut"] or 0)
        t["prio"] = int(t["prio"] or 0)
    return {"matieres": matieres, "taches": taches}


def sauvegarder(*tables):
    """Réécrit les feuilles indiquées avec l'état actuel."""
    try:
        for nom in tables:
            cols = EN_TETES[nom]
            lignes = [[row.get(c, "") for c in cols] for row in st.session_state.data[nom]]
            ws = get_feuille(nom)
            ws.clear()
            ws.resize(rows=max(100, len(lignes) + 20), cols=len(cols))
            ws.update(range_name="A1", values=[cols] + lignes)
    except Exception as e:
        st.error(f"Échec de l'enregistrement dans Google Sheets : {e}")


# ---------- Connexion ----------
def secrets_ok():
    try:
        return "gcp_service_account" in st.secrets and "sheet_id" in st.secrets
    except Exception:
        return False


if not secrets_ok():
    st.error(
        "Secrets introuvables. Créez le fichier `.streamlit/secrets.toml` dans le "
        "dossier d'où vous lancez `streamlit run app.py`."
    )
    st.stop()

if "data" not in st.session_state:
    try:
        st.session_state.data = charger()
    except Exception as e:
        if isinstance(e, gspread.SpreadsheetNotFound):
            st.error(
                "Feuille introuvable : vérifiez `sheet_id` et le partage (rôle Éditeur) avec "
                f"`{st.secrets['gcp_service_account']['client_email']}`."
            )
        else:
            st.error(f"Connexion à Google Sheets impossible ({type(e).__name__}) : {e!r}")
        st.stop()

data = st.session_state.data

if "flash" in st.session_state:
    st.toast(st.session_state.pop("flash"), icon="✅")


# ---------- Utilitaires ----------
def avancement(taches):
    """0 à 100 : 'En cours' compte pour moitié."""
    if not taches:
        return 0
    return round(sum(t["statut"] for t in taches) / (2 * len(taches)) * 100)


def emoji_de(nom):
    n = nom.lower()
    for cle, emo in EMOJIS:
        if cle in n:
            return emo
    return "📘"


def fond_couverture(m):
    img = m.get("image", "").strip()
    if img.lower().startswith(("http://", "https://")):
        for a, b in (("'", "%27"), ('"', "%22"), (")", "%29"), ("<", "%3C"), (">", "%3E"), (" ", "%20")):
            img = img.replace(a, b)
        return (
            "background-image:linear-gradient(rgba(10,20,30,.55),rgba(10,20,30,.55)),"
            f"url('{img}');background-size:cover;background-position:center"
        )
    return f"background:{m['couleur']}"


def trouver(tid):
    return next(t for t in data["taches"] if t["id"] == tid)


# ---------- Actions (callbacks) ----------
def maj_statut(tid):
    t = trouver(tid)
    nouveau = st.session_state.get(f"statut_{tid}")
    if nouveau is None:  # clic sur l'option déjà active : on la garde
        st.session_state[f"statut_{tid}"] = STATUTS[t["statut"]]
        return
    t["statut"] = STATUTS.index(nouveau)
    sauvegarder("taches")
    if t["statut"] == 2:
        reste = [x for x in data["taches"] if x["matiere"] == t["matiere"] and x["statut"] != 2]
        if reste:
            st.toast("Tâche terminée, bien joué !", icon="✅")
        else:
            st.balloons()
            st.toast("Matière terminée, bravo !", icon="🎉")


def maj_prio(tid):
    trouver(tid)["prio"] = st.session_state[f"prio_{tid}"]
    sauvegarder("taches")


def supprimer_tache(tid):
    data["taches"] = [t for t in data["taches"] if t["id"] != tid]
    sauvegarder("taches")


def supprimer_matiere(mid):
    data["matieres"] = [m for m in data["matieres"] if m["id"] != mid]
    data["taches"] = [t for t in data["taches"] if t["matiere"] != mid]
    sauvegarder("matieres", "taches")


def recharger():
    for k in list(st.session_state):
        if str(k).startswith(("statut_", "prio_")):
            del st.session_state[k]
    st.session_state.data = charger()


# ---------- En-tête ----------
total = len(data["taches"])
terminees = sum(1 for t in data["taches"] if t["statut"] == 2)
en_cours = sum(1 for t in data["taches"] if t["statut"] == 1)
urgentes = sum(1 for t in data["taches"] if t["prio"] == 3 and t["statut"] != 2)
restantes = total - terminees
pct_global = avancement(data["taches"])

if not data["matieres"]:
    message = "Ajoute ta première matière pour commencer."
elif total == 0:
    message = "Tes matières sont prêtes : ajoute tes premières tâches."
elif restantes == 0:
    message = "Tout est terminé, bravo !"
else:
    message = f"Il te reste {restantes} tâche{'s' if restantes > 1 else ''} à terminer."
    if urgentes:
        message += f" Dont {urgentes} très prioritaire{'s' if urgentes > 1 else ''}."

st.markdown(
    f'<div class="hero"><div><div class="ht">Mon suivi de cours</div>'
    f'<div class="hp">{html.escape(message)}</div></div>{ART}</div>',
    unsafe_allow_html=True,
)
st.markdown(
    f"""<div class="stats">
<div class="stat"><div class="ring" style="--p:{pct_global * 3.6}deg"><span>{pct_global}%</span></div><small>avancement<br>global</small></div>
<div class="stat"><div><b>{terminees}</b><small>terminée{'s' if terminees > 1 else ''}</small></div></div>
<div class="stat"><div><b>{en_cours}</b><small>en cours</small></div></div>
<div class="stat"><div><b>{urgentes}</b><small>très prioritaire{'s' if urgentes > 1 else ''}</small></div></div>
</div>""",
    unsafe_allow_html=True,
)

tab_matieres, tab_ajout = st.tabs(["Mes matières", "Ajouter"])

# ---------- Onglet : matières ----------
with tab_matieres:
    if data["matieres"]:
        noms = {m["id"]: m["nom"] for m in data["matieres"]}
        c_filtre, c_reload = st.columns([6, 1])
        choix = c_filtre.pills(
            "Filtrer",
            options=["all"] + list(noms),
            format_func=lambda x: "Toutes" if x == "all" else noms[x],
            default="all",
            label_visibility="collapsed",
        )
        c_reload.button("↻", on_click=recharger, help="Recharger depuis Google Sheets")
        choix = choix or "all"
    else:
        choix = "all"
        st.info("Aucune matière pour l'instant. Rendez-vous dans l'onglet « Ajouter ».")

    for m in data["matieres"]:
        if choix != "all" and m["id"] != choix:
            continue
        taches = [t for t in data["taches"] if t["matiere"] == m["id"]]
        taches.sort(key=lambda t: (t["statut"] == 2, -t["prio"]))
        pct = avancement(taches)
        faites = sum(1 for t in taches if t["statut"] == 2)

        with st.container(border=True):
            st.markdown(
                f'<div class="cover" style="{fond_couverture(m)}"><div class="cov">'
                f'<span class="emo">{emoji_de(m["nom"])}</span>'
                f'<div><div class="cn">{html.escape(m["nom"])}</div>'
                f"<small>{faites} sur {len(taches)} terminée{'s' if faites > 1 else ''}</small></div>"
                f'<div class="pct">{pct}%</div></div>'
                f'<div class="bar"><i style="width:{pct}%"></i></div></div>',
                unsafe_allow_html=True,
            )
            if not taches:
                st.caption("Aucune tâche pour cette matière.")
            for t in taches:
                c_titre, c_statut, c_prio, c_suppr = st.columns([5, 5, 3, 1], vertical_alignment="center")
                pastille = ""
                if t["prio"]:
                    pastille = (
                        f'<span class="pill" style="color:{PRIO_COULEURS[t["prio"]]}">'
                        f'{PRIOS[t["prio"]]}</span>'
                    )
                classe = "tt done" if t["statut"] == 2 else "tt"
                c_titre.markdown(
                    f'<div class="{classe}">{html.escape(t["titre"])}{pastille}</div>',
                    unsafe_allow_html=True,
                )
                c_statut.segmented_control(
                    "État",
                    STATUTS,
                    default=STATUTS[t["statut"]],
                    key=f"statut_{t['id']}",
                    label_visibility="collapsed",
                    on_change=maj_statut,
                    args=(t["id"],),
                )
                c_prio.selectbox(
                    "Priorité",
                    list(PRIOS),
                    index=t["prio"],
                    format_func=lambda x: f"{PRIO_ICONES[x]} {PRIOS[x]}",
                    key=f"prio_{t['id']}",
                    label_visibility="collapsed",
                    on_change=maj_prio,
                    args=(t["id"],),
                )
                c_suppr.button("✕", key=f"del_{t['id']}", on_click=supprimer_tache, args=(t["id"],), help="Supprimer la tâche")

            with st.popover("Supprimer la matière"):
                st.write("Cette action supprime aussi toutes les tâches de la matière.")
                st.button("Confirmer la suppression", key=f"delm_{m['id']}", on_click=supprimer_matiere, args=(m["id"],))

# ---------- Onglet : ajouter ----------
with tab_ajout:
    col_m, col_t = st.columns(2)

    with col_m:
        with st.form("form_matiere", clear_on_submit=True):
            st.markdown("**Nouvelle matière**")
            nom = st.text_input("Nom", placeholder="Ex. Mathématiques")
            couleur = st.color_picker("Couleur", PALETTE[len(data["matieres"]) % len(PALETTE)])
            image = st.text_input(
                "Image de couverture (lien, facultatif)",
                placeholder="https://images.unsplash.com/...",
                help="Sur Unsplash, clic droit sur une photo puis « Copier l'adresse de l'image ».",
            )
            if st.form_submit_button("Ajouter la matière", type="primary"):
                if nom.strip():
                    data["matieres"].append(
                        {"id": uuid.uuid4().hex[:8], "nom": nom.strip(), "couleur": couleur, "image": image.strip()}
                    )
                    sauvegarder("matieres")
                    st.session_state["flash"] = f"Matière « {nom.strip()} » ajoutée"
                    st.rerun()
                else:
                    st.warning("Donnez un nom à la matière.")

    with col_t:
        if data["matieres"]:
            noms = {m["id"]: m["nom"] for m in data["matieres"]}
            with st.form("form_tache", clear_on_submit=True):
                st.markdown("**Nouvelle tâche**")
                titre = st.text_input("Tâche", placeholder="Ex. Exercices du chapitre 3")
                mid = st.selectbox("Matière", list(noms), format_func=lambda x: noms[x])
                prio = st.selectbox(
                    "Priorité (facultative)",
                    list(PRIOS),
                    format_func=lambda x: f"{PRIO_ICONES[x]} {PRIOS[x]}",
                )
                if st.form_submit_button("Ajouter la tâche", type="primary"):
                    if titre.strip():
                        data["taches"].append(
                            {"id": uuid.uuid4().hex[:8], "matiere": mid, "titre": titre.strip(), "statut": 0, "prio": prio}
                        )
                        sauvegarder("taches")
                        st.session_state["flash"] = "Tâche ajoutée"
                        st.rerun()
                    else:
                        st.warning("Écrivez la tâche.")
        else:
            st.caption("Créez d'abord une matière pour pouvoir ajouter des tâches.")
