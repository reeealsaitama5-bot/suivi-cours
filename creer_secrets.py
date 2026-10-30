"""Génère .streamlit/secrets.toml à partir du fichier JSON de Google Cloud."""
import json
from pathlib import Path

chemin_json = input("Chemin du fichier JSON (glisse-le ici) : ").strip().strip('"')
sheet_id = input("ID de ta feuille Google Sheet : ").strip()

cle = json.loads(Path(chemin_json).read_text(encoding="utf-8"))

lignes = [f"sheet_id = {json.dumps(sheet_id)}", "", "[gcp_service_account]"]
for nom, valeur in cle.items():
    lignes.append(f"{nom} = {json.dumps(valeur)}")

dossier = Path(__file__).parent / ".streamlit"
dossier.mkdir(exist_ok=True)
(dossier / "secrets.toml").write_text("\n".join(lignes) + "\n", encoding="utf-8")

print("\nFichier créé :", dossier / "secrets.toml")
print("Partage ta feuille Google Sheet (rôle Éditeur) avec cette adresse :")
print(cle["client_email"])
