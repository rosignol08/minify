#un fichier pour convertir la musique midi en frequences buzzer et envoyer progressivement à l'esp


from convertisseur_midi_esp import *

import paho.mqtt.client as mqtt

IP_BROKER = "192.168.1.69"

import os
import re
from pathlib import Path

nom_musique_a_jouer = None

def recup_nom_musique():
    try:
        with open('/tmp/musique_demandee.txt', 'r') as f:
            # On lit et on enlève les espaces/sauts de ligne éventuels
            nom = f.read().strip()
        print(f"nom de ma musique c'est {nom}")
        return nom
    except FileNotFoundError:
        print("Aucune musique demandée (fichier introuvable).")
        return None

def chercher_musique_dans_bdd(directory_path: str, nom_musique_a_jouer: str):
    #on cherche la musique dans le dossier de musique
    try:
        dir_path = Path(directory_path)
        if not dir_path.exists():
            print(f"Erreur: le dossier '{directory_path}' existe pas.")
            return None
        if not dir_path.is_dir():
            print(f"Error: '{directory_path}' is not a directory.")
            return None

        #loop dans les fichier du dossier
        for file in dir_path.iterdir():
            if file.is_file():  # juste les fichier pas les sous dossiers
                if file.name == nom_musique_a_jouer:
                    print(f"trouvé: {file.name}")
                    return file
            else:
                print(f"Skip le fichier: {file.name}")
        
        print(f"La musique '{nom_musique_a_jouer}' est pas dans le dossier.")
        return None
    except Exception as e:
        print(f"An error occurred: {e}")
        return None

###########le serveurrr MQTT ###########
def on_connect(client, userdata, flags, rc): # Callback connexion broker
    print("Connecté " + str(rc))
    
def on_message(client, userdata, msg): # Callback subscriber pas trop besoin mais bon
    print(f"Message reçu : {msg.topic} {msg.payload.decode()}") #decode pour enlever le b'' truc là    

#recup le nom de la musique voulue
nom_musique_a_jouer = recup_nom_musique()
fichiers_destination = "./musiques"

if nom_musique_a_jouer:
    #recup le chemin absolu du dossier du script (web/server/www)
    dossier_script = os.path.dirname(os.path.abspath(__file__))
    #le chemin absolu vers le dossier musiques local (web/server/www/musiques)
    dossier_musiques = os.path.abspath(os.path.join(dossier_script, 'musiques'))
    print(f"Recherche dans le dossier : {dossier_musiques}")

    #on garde que le nom du fichier (si la page web envoie '/musiques/Toto.mid', faut que 'Toto.mid')
    nom_fichier_seul = os.path.basename(nom_musique_a_jouer)

    #cherche
    fichier_trouve = chercher_musique_dans_bdd(dossier_musiques, nom_fichier_seul)

    if fichier_trouve:
        client = mqtt.Client() # Création d'une instance client

        client.on_connect = on_connect # Assignation des callbacks

        client.on_message = on_message

        client.connect(IP_BROKER, 1883, 60)
        client.loop_start()

        print(f"Fichier trouvé à convertir : {fichier_trouve}")
        #quand on a trouvé on la convertie en son buzzer
        convertis_midi_buzzer(str(fichier_trouve), fichiers_destination)
        #ici on a converti la musique en buzzer faut l'envoyer dans un dossier
        resultat = client.publish("musique", "rejoue", qos=1)
        resultat.wait_for_publish()
        client.loop_stop()
        client.disconnect()
        print("Signal MQTT 'musique' envoyé.")
    else:
        print("Fichier non trouvé.")
else:
    print("Rien à faire.")


