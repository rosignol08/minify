#!/usr/bin/env python3
import json

#la bdd
#un dictionnaire Python avec nos albums et les vrais chemins vers les fichiers midi
db_albums = {
    "album_80s": {
        "artist": "les annes 80",
        "title": "80s",
        "cover": "/img/80_album.jpeg",
        "songs": [
            {"title": "Bohemian Rhapsody", "duration": "17:30", "file": "/musiques/Bohemian_Rhapsody.mid"},
            {"title": "Beat It", "duration": "4:13", "file": "/musiques/Beat_It.mid"},
            {"title": "Billie Jean", "duration": "4:55", "file": "/musiques/Billie-Jean.mid"}
        ]
    },
    "album_anime": {
        "artist": "Ost danime",
        "title": "Anime",
        "cover": "/img/anime_cover.jpg",
        "songs": [
            {"title": "OnePiece", "duration": "0:52", "file": "/musiques/OnePiece-MinatoMura.mid"},
            {"title": "Pirate", "duration": "1:21", "file": "/musiques/pirate.mid"},
            {"title": "Evangelion", "duration": "3:57", "file": "/musiques/Evangelion-CruelAngelsThesis.mid"},
            {"title": "Tokyo Ghoul", "duration": "1:23", "file": "/musiques/TokyoGhoul-Unravel.mid"}
        ]
    },
    "album_jeu": {
        "artist": "Son de jeux vidéo",
        "title": "Jeu",
        "cover": "/img/jeu_cover.webp",
        "songs": [
            {"title": "Zelda Theme", "duration": "1:35", "file": "/musiques/The_Legend_of_Zelda.mid"},
            {"title": "sandstorm", "duration": "5:37", "file": "/musiques/darude-sandstorm.mid"},
            {"title": "Skyrim", "duration": "3:06", "file": "/musiques/Skyrim.mid"},
            {"title": "Tetris Theme", "duration": "1:00", "file": "/musiques/Tetris_Theme.mid"}
        ]
    }
}

#conversion de la bdd Python en format texte JSON pour le donner au JavaScript
db_json = json.dumps(db_albums)


print("Content-Type: text/html; charset=utf-8")
print()

#le site html css et javascript fait par un llm
html = """<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <title>Minify</title>
    <style>
        /* --- RESET ET LAYOUT DE BASE --- */
        * { margin: 0; padding: 0; box-sizing: border-box; font-family: 'Segoe UI', sans-serif; }
        body { background-color: #000; color: white; overflow: hidden; }
        .container { display: flex; height: 100vh; }

        /* --- SIDEBAR --- */
        .sidebar { width: 240px; background-color: #000; padding: 20px; display: flex; flex-direction: column; }
        .logo { display: flex; align-items: center; font-size: 24px; font-weight: bold; margin-bottom: 25px; gap: 10px; }
        .logo img { width: 32px; height: 32px; }
        .sidebar ul { list-style: none; }
        .sidebar li { padding: 10px 0; color: #b3b3b3; cursor: pointer; transition: 0.3s; }
        .sidebar li:hover { color: white; }

        /* --- MAIN CONTENT --- */
        .main-content { flex: 1; background: linear-gradient(to bottom, #1e1e1e, #121212); padding: 20px; overflow-y: auto; padding-bottom: 100px; position: relative; }
        
        /* Classe utilitaire pour cacher les éléments via JavaScript */
        .hidden { display: none !important; }

        /* Bouton Retour commun */
        .back-btn { background: transparent; border: none; color: #b3b3b3; font-size: 16px; cursor: pointer; margin-bottom: 20px; display: flex; align-items: center; gap: 10px; }
        .back-btn:hover { color: white; }

        /* --- VUE 1 : GRILLE DES ALBUMS --- */
        .grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(180px, 1fr)); gap: 20px; margin-top: 20px; }
        .card { background: #181818; padding: 15px; border-radius: 8px; position: relative; transition: background 0.3s; cursor: pointer; }
        .card:hover { background: #282828; }
        .card img.album-art { width: 100%; border-radius: 5px; margin-bottom: 15px; }
        
        .play-btn { 
            position: absolute; right: 20px; bottom: 80px; 
            background: #1db954; width: 45px; height: 45px; 
            border-radius: 50%; display: flex; align-items: center; 
            justify-content: center; opacity: 0; transition: 0.3s; 
            box-shadow: 0 8px 16px rgba(0,0,0,0.3); 
        }
        .play-btn img { width: 20px; height: 20px; }
        .card:hover .play-btn { opacity: 1; transform: translateY(-5px); }

        /* --- VUE 2 : LISTE DES MUSIQUES --- */
        .album-header { display: flex; align-items: flex-end; gap: 20px; margin-bottom: 30px; }
        .album-header img { width: 150px; height: 150px; box-shadow: 0 4px 20px rgba(0,0,0,0.5); }
        .song-list { list-style: none; margin-top: 20px; }
        .song-item { display: flex; justify-content: space-between; padding: 10px 15px; border-radius: 5px; cursor: pointer; color: #b3b3b3; }
        .song-item:hover { background-color: #2a2a2a; color: white; }

        /* --- VUE 3 : LECTEUR EN GRAND --- */
        .big-player { display: flex; flex-direction: column; align-items: center; justify-content: center; height: 70vh; text-align: center; }
        .big-player img { width: 300px; height: 300px; border-radius: 10px; box-shadow: 0 10px 30px rgba(0,0,0,0.5); margin-bottom: 30px; }
        .big-player h2 { font-size: 32px; margin-bottom: 10px; }
        .big-player p { color: #b3b3b3; font-size: 18px; margin-bottom: 30px; }
        .big-controls { display: flex; gap: 20px; align-items: center; }
        .big-play-btn { background: #1db954; width: 70px; height: 70px; border-radius: 50%; display: flex; align-items: center; justify-content: center; cursor: pointer; }
        .big-play-btn img { width: 30px; height: 30px; }

        /* --- MINI PLAYER (BAS) --- */
        .player { position: fixed; bottom: 0; left: 0; width: 100%; height: 90px; background: #181818; border-top: 1px solid #282828; display: flex; align-items: center; padding: 0 20px; z-index: 10; }
        audio { margin-top: 20px; width: 100%; max-width: 400px; outline: none; }
    </style>
</head>
<body>
    <div class="container">
        <aside class="sidebar">
            <div class="logo">
                <img src="/img/logo.svg" alt="Logo"> 
                <span>Minify</span>
            </div>
            <nav>
                <ul>
                    <li onclick="showView('view-albums')">Accueil</li>
                    <li>Rechercher</li>
                    <li onclick="showView('view-albums')">Bibliothèque</li>
                </ul>
            </nav>
        </aside>

        <main class="main-content">
    
    <section id="view-albums">
        <h2>Albums recommandés</h2>
        <div class="grid">
            <div class="card" onclick="openAlbum('album_80s')">
                <img src="/img/80_album.jpeg" class="album-art">
                <h4>80s</h4>
                <p>les annes 80</p>
                <div class="play-btn"><img src="/img/play.svg" alt="Play"></div>
            </div>
            
            <div class="card" onclick="openAlbum('album_anime')">
                <img src="/img/anime_cover.jpg" class="album-art">
                <h4>Anime</h4>
                <p>Ost danime</p>
                <div class="play-btn"><img src="/img/play.svg" alt="Play"></div>
            </div>
            
            <div class="card" onclick="openAlbum('album_jeu')">
                <img src="/img/jeu_cover.webp" class="album-art">
                <h4>Jeu</h4>
                <p>Son de jeux vidéo</p>
                <div class="play-btn"><img src="/img/play.svg" alt="Play"></div>
            </div>
        </div>
    </section>

    <section id="view-songs" class="hidden">
        <button class="back-btn" onclick="showView('view-albums')">⬅ Retour aux albums</button>
        
        <div class="album-header">
            <img id="current-album-img" src="" alt="Album Cover">
            <div>
                <p>Album</p>
                <h1 id="current-album-title">Titre de l'album</h1>
                <p id="current-album-artist" style="color: #b3b3b3;">Artiste</p>
            </div>
        </div>

        <ul class="song-list" id="song-list-container">
        </ul>
    </section>

    <section id="view-player" class="hidden">
        <button class="back-btn" onclick="showView('view-songs')">⬅ Retour à l'album</button>
        
        <div class="big-player">
            <img id="big-player-img" src="" alt="Album Cover">
            <h2 id="big-player-song">Nom de la musique</h2>
            <p id="big-player-artist">Artiste</p>
            
            <audio id="audio-player" controls autoplay>
                Votre navigateur ne supporte pas la balise audio.
            </audio>
        </div>
    </section>
    <iframe style="display: none;" name="cache_iframe">
    </iframe>
    <form id="form_musique" action="recup_nom_musique.py" target="cache_iframe" method="POST">
    <input type=hidden id ="mus" name="nom_musique">
    </form>

</main>

        <footer class="player">
            <p style="color: #b3b3b3; font-size: 14px;">Mini lecteur en attente...</p>
        </footer>
    </div>

    <script>
        // --- 3. INJECTION DE LA BASE DE DONNÉES EN JS ---
        // Le Python va remplacer le mot-clé ci-dessous par les vraies données
        const database = DATABASE_JSON_INJECT;

        function showView(viewId) {
            document.getElementById('view-albums').classList.add('hidden');
            document.getElementById('view-songs').classList.add('hidden');
            document.getElementById('view-player').classList.add('hidden');
            document.getElementById(viewId).classList.remove('hidden');
        }

        // Fonction quand on clique sur un Album (utilise la BDD)
        function openAlbum(albumKey) {
            const albumData = database[albumKey]; // On récupère les infos depuis la base
            
            document.getElementById('current-album-title').innerText = albumData.title;
            document.getElementById('current-album-artist').innerText = albumData.artist;
            document.getElementById('current-album-img').src = albumData.cover;

            const songList = document.getElementById('song-list-container');
            songList.innerHTML = ''; // On vide l'ancienne liste
            
            // On boucle sur les VRAIES musiques de la base de données
            albumData.songs.forEach((song, index) => {
                let li = document.createElement('li');
                li.className = 'song-item';
                li.innerHTML = `<span>${index + 1}. ${song.title}</span> <span>${song.duration}</span>`;
                
                // Au clic, on lance la musique
                li.onclick = function() {
                    openPlayer(song.title, albumData.artist, albumData.cover, song.file);
                };
                songList.appendChild(li);
            });

            showView('view-songs');
        }

        // Fonction quand on clique sur une musique pour l'écouter
        function openPlayer(songTitle, artist, imageSrc, audioFileUrl) {
            document.getElementById('big-player-song').innerText = songTitle;
            document.getElementById('big-player-artist').innerText = artist;
            document.getElementById('big-player-img').src = imageSrc;

            showView('view-player');
            //pour mettre dans le formulaire automatiquement
            let inputElem = document.getElementById("mus");
            console.log("valeur avant");
            console.log(inputElem.value);
            inputElem.value = audioFileUrl; //TODO voir si c'est bon
            console.log("valeur apres");
            console.log(inputElem.value);
            document.getElementById("form_musique").submit();
        }
    </script>
</body>
</html>
"""

#pour remplacer le mot-clé "DATABASE_JSON_INJECT" par notre vrai JSON qu'on a fait au dessus
html_final = html.replace("DATABASE_JSON_INJECT", db_json)
print(html_final)