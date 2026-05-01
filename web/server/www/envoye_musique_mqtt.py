"""Lecture de melody_data.h et envoi progressif en MQTT.

Commandes recues sur le topic `control`:
- "joue" : charge la melodie depuis le fichier .h et demarre l'envoi
- "stop" : stoppe l'envoi et remet le curseur au debut
"""

import json
import queue
import re
import time
from pathlib import Path
import os
import paho.mqtt.client as mqtt


BROKER_HOST = "192.168.1.69"
BROKER_PORT = 1883

CONTROL_TOPIC = "control"
DATA_TOPIC = "flux"
#STATUS_TOPIC = "flux"

#flux c'est le channel du flux de musique donc python envoye -> esp32
#control c'est le channel des boutons de l'esp 32 qui jouent ou pas la musique

PACKET_SIZE = 30
PACKET_SEND_DELAY_SEC = 0.15
MELODY_HEADER_PATH = "musiques/melody.h" #Path(__file__).with_name("melody.h")

file_dattente = queue.Queue() # j'ai vu que ça pose bien moin de problèmes pour pas que le traitement se fasse dans 'on_message' psk il est lourd et c'est facile pour la synchro

class Paquet:
    def __init__(self, tableau, duree, nom):
        self.tableau = tableau
        self.duree = duree
        self.nom = nom

def charge_musique(header_path=MELODY_HEADER_PATH):
    """fonction pour charger les tableau de notes en ram et les coiper etc"""
    #déjà faut charger le tableau "melody"
    """Lit melody[] et durations[] dans le fichier .h et retire les virgules finales."""
    tableaux = {"melody": [], "durations": []}
    tableau_courant = None
    temps_total = 0
    nom = ""
    with open(header_path, "r", encoding="utf8", errors="ignore") as fichier:
        for ligne in fichier:
            ligne = ligne.strip()

            if ligne.startswith("// MUSIC_NAME:"):
                match = re.search(r"//\s*MUSIC_NAME:\s*(.+)", ligne)
                if match is not None:
                    nom = match.group(1).strip()
                print(f"nom de la musique: {nom}")
                continue

            if tableau_courant is None:
                if ligne.startswith("const int melody[]"):
                    tableau_courant = "melody"
                    continue
                if ligne.startswith("const int durations[]"):
                    tableau_courant = "durations"
                    continue
                continue

            if ligne.startswith("};"):
                tableau_courant = None
                continue

            if not ligne:
                continue

            valeur = ligne.rstrip(",")
            tableaux[tableau_courant].append(valeur)
            if tableau_courant == "durations":
                try:
                    temps_total += int(valeur)
                except ValueError:
                    pass

    print(f"melody: {len(tableaux['melody'])} valeurs")
    print(f"durations: {len(tableaux['durations'])} valeurs")
    print(f"ca prend {temps_total} millisecondes")
    return Paquet(tableaux, temps_total, nom)

def decoupeur(paquet_global, PACKET_SIZE, index):
    """ça c'est une fonction qui doit couper les paquets en vrai elle va juste recuperer un index et envoyer un truc à envoyer avec mqtt
    format : NOTE_C3 etc sépares de , puis temps separé de ; puis note,temps etc  . à la fin
    """
    
    if paquet_global is None:
        return None
    
    melody = paquet_global.tableau.get("melody", [])
    durations = paquet_global.tableau.get("durations", [])
    total = min(len(melody), len(durations))
    
    if (index == 0):
        #on envoye que le nom de la musique et sa durée au debut
        return f"{paquet_global.nom};{paquet_global.duree}."
        
    start = (index - 1) * PACKET_SIZE
    if start >= total:
        return None

    end = min(start + PACKET_SIZE, total)

    morceaux = []
    for i in range(start, end):
        morceaux.append(f"{melody[i]},{durations[i]};")

    paquet = "".join(morceaux)
    #fin
    if end >= total:
        paquet += "."

    return paquet
    

def charger_table_notes(pitches_path: str):
    """
    Lit un fichier pitches.h et retourne un dict:
    {"NOTE_C4": 262, "NOTE_CS4": 277, ...}
    """
    contenu = Path(pitches_path).read_text(encoding="utf-8", errors="ignore")
    table = {}
    for nom, val in re.findall(r"#define\s+(NOTE_[A-Z0-9]+)\s+(\d+)", contenu):
        table[nom] = int(val)
    return table



def convertir_paquet_notes_en_hz(paquet: str | None, table_notes: dict) -> str | None:
    if paquet is None:
        return None

    #paquet de base c'est : "Nom;12345."
    if "," not in paquet:
        return paquet

    fin = paquet.endswith(".")
    body = paquet[:-1] if fin else paquet

    out = []
    for item in body.split(";"):
        item = item.strip()
        if not item:
            continue
        note, duree = item.split(",", 1)
        hz = table_notes.get(note.strip().upper(), 0)
        out.append(f"{hz},{duree.strip()};")

    return "".join(out) + ("." if fin else "")

def on_connect(client, userdata, flags, rc):
    print("Connecte au broker, code = " + str(rc))
    client.subscribe("musique")#on ecoute si il y a une nouvelle musique ou pas
    client.subscribe(CONTROL_TOPIC)

def on_message(client, userdata, msg):
    text = msg.payload.decode(errors="ignore").strip().lower()
    print(f"Message recu: topic={msg.topic}, payload={text}")
    if(msg.topic == CONTROL_TOPIC):
        if (text == "joue"):
            file_dattente.put(text)
        if (text == "stop"):
            file_dattente.put(text)
    else:
        #on a recu une nouvelle musique faut recharger et vider la queue
        while True:
            try:
                file_dattente.get_nowait()
            except queue.Empty:
                break
        file_dattente.put("rejoue")



def main():
    
    client = mqtt.Client()
    client.on_connect = on_connect
    client.on_message = on_message
    client.connect(BROKER_HOST, BROKER_PORT, 60)
    client.loop_start()
    table_notes = charger_table_notes("pitches.h")

    a_commence = False
    joue = False
    paquet_a_envoyer = None
    indexe = 0
    packets = ""
    while True:
        try:
            command = file_dattente.get(timeout=0.05)
        except queue.Empty:
            command = None

        if command == "joue":
            joue = True

        if command == "rejoue":
            a_commence = False
            joue = False
            paquet_a_envoyer = None
            indexe = 0
            packets = ""
            print("on rejoue")
        elif command == "stop":
            #si on recoit un stop on dit qu'on arrete de jouer de la musique
            joue = False
            a_commence = False
            paquet_a_envoyer = None
            indexe = 0
            print("On a recu stop par commande control donc on arrete")
            #on vide la queue
            while True:
                try:
                    file_dattente.get_nowait()
                except queue.Empty:
                    break

        if joue:
            try:
                if not a_commence:
                    a_commence = True
                    indexe = 0
                    paquet_a_envoyer = charge_musique(MELODY_HEADER_PATH)

                packets = decoupeur(paquet_a_envoyer, PACKET_SIZE, indexe)
                packets_hz = convertir_paquet_notes_en_hz(packets, table_notes)

                if packets_hz is None:
                    joue = False
                    a_commence = False
                    paquet_a_envoyer = None
                    indexe = 0
                    print("Musique terminee, en attente d'une nouvelle musique")
                else:
                    client.publish(DATA_TOPIC, packets_hz, qos=1)
                    indexe += 1
                    time.sleep(PACKET_SEND_DELAY_SEC)

            except Exception as exc:
                while True:
                    try:
                        file_dattente.get_nowait()
                    except queue.Empty:
                        break
                joue = False
                a_commence = False
                paquet_a_envoyer = None
                indexe = 0
                print(f"Erreur chargement melodie: {exc}")
    client.loop_stop()
    client.disconnect()

if __name__ == "__main__":
    main()
