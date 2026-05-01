#!/usr/bin/env python3
import os
import subprocess
import sys
from pathlib import Path
from urllib.parse import parse_qs

#script cgi pour recuperer le nom de la musique qu'on a selectioné
def read_form_value(field_name: str) -> str:
    request_method = os.environ.get("REQUEST_METHOD", "GET").upper()
    if request_method == "POST":
        content_length = int(os.environ.get("CONTENT_LENGTH", "0") or 0)
        raw_body = sys.stdin.buffer.read(content_length).decode("utf-8", errors="ignore")
        return parse_qs(raw_body).get(field_name, [""])[0]

    query_string = os.environ.get("QUERY_STRING", "")
    return parse_qs(query_string).get(field_name, [""])[0]

val = read_form_value("nom_musique").strip()

print("Content-Type: text/plain; charset=utf-8")
print()

if val:
    with open('/tmp/musique_demandee.txt', 'w', encoding='utf-8') as f:
        f.write(val)

    www_dir = Path(__file__).resolve().parent.parent
    sender_script = www_dir / "envoie_donnees.py"
    log_file = "/tmp/envoie_donnees.log"

    with open(log_file, "a", encoding="utf-8") as log:
        log.write(f"\n=== trigger: {val} ===\n")
        subprocess.Popen(
            [sys.executable, str(sender_script)],
            cwd=str(www_dir),
            stdout=log,
            stderr=log,
            start_new_session=True,
        )

    print(f"Nom de la musique enregistré: {val}")
    print("Lancement du convertisseur/envoi MQTT demande.")
    print(f"Logs: {log_file}")
else:
    print("Aucun nom de musique reçu.")