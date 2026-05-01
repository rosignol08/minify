# Compte‑rendu Chaffray — `projet_ioc`

## 0) introduction
Mon projet est un Mini “Spotify” pour jouer une musique sur le buzzer de l'ESP32.
Le **Raspberry Pi** sert de **serveur web (CGI)** + scripts Python + **broker MQTT**  et envoie les notres en flux vers l’ESP32 pour faire communiquer l'ordinateur et l'esp32.

---

## 1) Architecture (qui fait quoi)

### Web (le site et son interface)
- `web/server/server.py`
  c'est le Serveur HTTP Python (port 8000) avec `CGIHTTPRequestHandler`.
  CGI servis depuis `/cgi-bin`.
- `web/server/www/index.html`  
  Il redirige directement vers `cgi-bin/main.py`.
- `web/server/www/cgi-bin/main.py`  
  Génère la page jolie HTML/CSS/JS (albums, liste de titres).
  La “BDD” c'est un dictionaire Python `db_albums` qu'on transforme en bdd JSON (pour le donner au javascript) avec des entrées `file: "/musiques/xxx.mid"`.

  Quand on clique un morceau, ça soumet un formulaire caché vers `recup_nom_musique.py` avec le champ `nom_musique` ça sert à recuperer le nom et chemin de la musique choisie par le pc sur la rpi.

### Pi (conversion + orchestration)
- `web/server/www/cgi-bin/recup_nom_musique.py`
  - Elle récupère `nom_musique` (POST/GET),
  - écrit la valeur dans `/tmp/musique_demandee.txt`,
  - lance `web/server/www/envoie_donnees.py` en arrière‑plan,
  - log dans `/tmp/envoie_donnees.log`.

- `web/server/www/envoie_donnees.py`
  - lit la musique demandée dans `/tmp/musique_demandee.txt`,
  - retrouve le `.mid` dans `web/server/www/musiques/`,
  - convertit MIDI → `melody.h` via `convertisseur_midi_esp.py` (code trouvé sur github),
  - publie MQTT sur le topic `musique` (payload: `"rejoue"`) pour dire à l'esp qu'on arrete la musique en cours et qu'on joue celle là.

- `web/server/www/convertisseur_midi_esp.py`
  Convertisseur MIDI → header C++ (`musiques/melody.h`) contenant:
  - `const int melody[]` (macros NOTE_*)
  - `const int durations[]` (ms)
  + backup auto dans `musiques/Backups/`.

- `web/server/www/envoye_musique_mqtt.py` (script tourne en continue)
  Abonné à:
  - `musique` (nouvelle musique dispo → reset état, attente “play”)
  - `control` (commandes de l'esp32 envoyé au rpi)
  
  Quand il reçoit `"joue"` (topic `control`):
  - charge `musiques/melody.h`,
  - découpe en paquets de taille défini avec `PACKET_SIZE`,
  - convertit NOTE_* → Hz via `pitches.h`,
  - publie sur `flux` des strings du type:
    - 1er paquet: `"NomDeMusique.mid;12345."` pour que l'esp puisse conaitre le nom et la longeur de la musique pour un affichage future ?
    - suivants: `"440,250;392,250;...;"` (un `.` à la fin du dernier paquet pour que l'esp32 sache que c'est la fin de la musique)

### ESP32 (réception + lecture hardware)
- `esp32/code_esp_32.ino`
  - se connecte au WiFi + broker MQTT,
  - subscribe sur `flux`,
  - parse et stocke la partition (`partition[]` Hz, `temps[]` ms),
  - bouton (pin 23) toggle play/stop:
    - envoie `"joue"` ou `"stop"` sur le topic `control`,
  - joue le son via `ledcWriteTone` (pin attaché: 17),
  - OLED + photoresistance/LED présents (multi‑tâches coop).

---

## 2) Comment lancer

### Pré‑requis
- Mosquitto (ou autre broker MQTT) sur le Raspberry Pi.
- Python 3 + `paho-mqtt` + `mido` côté Pi.
- ESP32 flashé avec le code `esp32/code_esp_32.ino`.

### Ordre de lancement recommandé (Pi)
1) Démarrer le broker MQTT (ex Mosquitto).
2) Se placer dans `web/server/www/` et lancer le serveur web:
   - `python3 ../server.py`
3) Dans un autre terminal, depuis `web/server/www/` lancer le sender:
   - `python3 envoye_musique_mqtt.py`

### Côté navigateur
- Ouvrir: `http://<IP_DU_PI>:8000/`
- Choisir un album puis un titre (ça déclenche conversion + signal MQTT `musique`).

### Côté ESP32
- Une fois la musique reçue (après la conversion), appuyer sur le bouton:
  - envoie `"joue"` sur `control`
  - le Pi commence à streamer sur `flux`
  - l’ESP32 joue

---

## 3) Les channels MQTT
Topics:
- `musique` : “nouvelle musique convertie / rejoue” (Pi → Pi sender)
- `control` : commandes (ESP32 ↔ Pi)
  - `"joue"` : charge + stream
  - `"stop"` : stop + reset curseur
- `flux` : flux des notes à jouer (Pi → ESP32)

Format `flux`:
- Paquet 0: `"<nom>;<duree_ms>."`
- Paquets notes: `"<hz>,<ms>;<hz>,<ms>;..."`
- `.` = dernier paquet

---

## 4) Problèmes

1) IP/wifi en dur
- ESP32: `ssid`, `password`, `mqttServer` sont hardcodés ducoup si ça change faut reecrire les fichier à la main.
- Pi: `BROKER_HOST` / `IP_BROKER` hardcodés dans plusieurs scripts pareil faut chercher à chaque fois (je pourrait voir si on peut pas faire un partage de connexion avec la rpi pour que ça change jamais).

2) Le clic web ne “joue” pas
Le clic fait que:
- écrire `/tmp/musique_demandee.txt`
- lancer conversion
- envoyer `"rejoue"` sur `musique`
Le vrai “play” démarre quand l’ESP32 envoie `"joue"` sur `control` c'est un reflex a avoir parce que j'ai de nombreuses fois cru que c'etait un problème de diffusion.

3) Le serveur et CGI
- faut vérifier que `server.py` est lancé depuis `web/server/www`
- pour debuger regarder `/tmp/envoie_donnees.log` a pas mal aidé

4) RAM ESP32
La partition est stockée entièrement en RAM (2 vecteurs). Gros MIDI = risque mais c'est ultra rare.

5) MQTT Esp32
 - j'ai du aussi prendre le reflexe d'allumer l'esp APRES avoir lancé les deux programmes sur la rpi car si il arrive pas à se connecter il abandonne dès la première tentative.
---

## 5) Idées d’amélioration 
- Mettre toute la config réseau (broker, ssid, topics) dans un seul fichier (ou `.env`).
- Afficher dans l’UI web un message “conversion lancée / prête” (lire `/tmp/envoie_donnees.log` par exemple).
 - Afficher le nom de la musique ou une progress bar ou les deux ? ça peut etre cool mais faut que je vois le coté graphique. 
P2
---

## 6) resumé de l'architecture 
- Site jolie: `web/server/www/cgi-bin/main.py`
- Déclencheur : `web/server/www/cgi-bin/recup_nom_musique.py`
- Conversion : `web/server/www/envoie_donnees.py` + `web/server/www/convertisseur_midi_esp.py`
- envoie de la musque en flux : `web/server/www/envoye_musique_mqtt.py`
- L'ESP32 : `esp32/code_esp_32.ino`

```text
projet_ioc/
├─ rapport.md
├─ esp32/
│  └─ code_esp_32.ino (le code pour l'esp32)
└─ web/
   ├─ client_pc.py
   └─ server/
      ├─ server.py
      └─ www/
         ├─ index.html (le site de base)
         ├─ pitches.h (les notes en buzzer de reference )
         ├─ convertisseur_midi_esp.py (le code github)
         ├─ envoie_donnees.py (script utilisé par le cgi)
         ├─ envoye_musique_mqtt.py (tourne en continue pour diffuser la musique)
         ├─ cgi-bin/
         │  ├─ main.py (le site jolie)
         │  └─ recup_nom_musique.py (script cgi qui appelle "envoie_donnees.py")
         ├─ img/ (les image des albums et icon du site)
         │  ├─ 80_album.jpeg
         │  ├─ anime_cover.jpg
         │  ├─ cover_jackson.webp
         │  ├─ jeu_cover.jpg
         │  ├─ jeu_cover.webp
         │  ├─ logo.svg
         │  ├─ peri.png
         │  └─ play.svg
         └─ musiques/ (les musique de notre bdd sur la rpi)
            ├─ Backups/
            ├─ melody_data.h
            ├─ Beat_It.mid
            ├─ Billie-Jean.mid
            ├─ Bohemian_Rhapsody.mid
            ├─ Evangelion-CruelAngelsThesis.mid
            ├─ OnePiece-MinatoMura.mid
            ├─ One_More_Time.mid
            ├─ Skyrim.mid
            ├─ Tetris_Theme.mid
            ├─ The_Legend_of_Zelda.mid
            ├─ TokyoGhoul-Unravel.mid
            ├─ darude-sandstorm.mid
            └─ pirate.mid
```