# modules/chords.py
# Exemple : "Sur la piste 1, crée un clip de 8 mesures. Ensuite, génère une progression d'accords R&B de 8 accords, où chaque accord dure 4 temps (beats_per_chord=4.0), en Do mineur (root_note=60)."
import logging

logger = logging.getLogger("AbletonUniversalServer.Chords")

# Dictionnaire des intervalles MIDI pour chaque type d'accord
CHORD_TYPES = {
    "maj": [0, 4, 7],             # Majeur
    "min": [0, 3, 7],             # Mineur
    "maj7": [0, 4, 7, 11],        # Majeur 7
    "min7": [0, 3, 7, 10],        # Mineur 7
    "dom7": [0, 4, 7, 10],        # Septième de dominante
    "min9": [0, 3, 7, 10, 14],    # Mineur 9 (très utilisé en R&B)
    "maj9": [0, 4, 7, 11, 14],    # Majeur 9
    "sus4": [0, 5, 7],            # Suspendu 4 (Trip-hop)
    "power": [0, 7],              # Power chord (Rock, juste fondamentale + quinte)
    "dim": [0, 3, 6]              # Diminué
}

def register_tools(mcp, get_conn):
    
    @mcp.tool()
    def generate_chord_progression(track_index: int, clip_index: int, genre: str, root_note: int = 60, num_chords: int = 4, beats_per_chord: float = 2.0) -> str:
        """
        Génère une progression d'accords MIDI selon un genre musical.
        genre: "jazz", "pop", "hip-hop", "r&b", "rock", "trip-hop".
        root_note: Note fondamentale (ex: 60 = Do central, 62 = Ré).
        num_chords: Nombre total d'accords à générer (la progression bouclera si nécessaire).
        beats_per_chord: Durée de chaque accord en temps (ex: 2.0 = une blanche, 4.0 = une ronde).
        """
        genre_key = genre.lower()
        logger.info(f"🎹 Génération progression {genre_key} ({num_chords} accords) sur piste {track_index}, base {root_note}")
        
        # Définition des progressions typiques 
        # Format : (Offset en demi-tons par rapport à la fondamentale, Type d'accord)
        patterns = {
            "pop": [(0, "maj"), (7, "maj"), (9, "min"), (5, "maj")],               # I - V - vi - IV
            "jazz": [(2, "min7"), (7, "dom7"), (0, "maj7"), (9, "dom7")],          # ii7 - V7 - Imaj7 - VI7
            "r&b": [(0, "min9"), (5, "min9"), (7, "min7"), (8, "maj7")],           # imin9 - ivmin9 - vmin7 - VImaj7
            "hip-hop": [(0, "min7"), (8, "maj7"), (10, "dom7"), (0, "min7")],      # i - VI - VII - i (Boucle sombre)
            "rock": [(0, "power"), (10, "power"), (5, "power"), (0, "power")],     # I - bVII - IV - I
            "trip-hop": [(0, "min"), (0, "sus4"), (8, "maj7"), (5, "min")]         # imin - isus4 - VImaj7 - ivmin
        }
        
        if genre_key not in patterns:
            return f"❌ Genre non reconnu : {genre}. Essaie 'jazz', 'pop', 'hip-hop', 'r&b', 'rock', ou 'trip-hop'."
            
        base_pattern = patterns[genre_key]
        notes_to_send = []
        
        # On génère le nombre d'accords demandé (en bouclant le pattern si besoin)
        for i in range(num_chords):
            # i % len(base_pattern) permet de boucler (ex: le 5ème accord sera le 1er du pattern)
            offset, chord_type = base_pattern[i % len(base_pattern)]
            
            # Calcul du timing
            start_time = i * beats_per_chord
            # On retire 0.05 temps à la durée pour un effet "legato" et éviter que les notes MIDI ne se chevauchent
            duration = beats_per_chord - 0.05 
            
            # Humanisation de la vélocité (les accords sur les temps forts sont légèrement plus appuyés)
            base_vel = 85 if i % 2 == 0 else 75
            
            # Construction de l'accord note par note
            intervals = CHORD_TYPES.get(chord_type, [0, 4, 7])
            for interval in intervals:
                pitch = root_note + offset + interval
                
                # Petits ajustements pour éviter que les notes n'aillent trop dans les aigus (inversions basiques)
                if pitch > root_note + 15 and chord_type not in ["min9", "maj9"]:
                    pitch -= 12
                    
                notes_to_send.append({
                    "pitch": pitch,
                    "start": start_time,
                    "dur": duration,
                    "vel": base_vel,
                    "mute": False
                })

        try:
            conn = get_conn()
            res = conn.send_command("add_midi_notes", {
                "track_index": track_index,
                "clip_index": clip_index,
                "notes": notes_to_send
            })
            return f"✅ Progression {genre_key} ({num_chords} accords, {beats_per_chord} temps/accord) générée avec succès !"
        except Exception as e:
            logger.error(f"Erreur Chord Gen: {str(e)}")
            return f"Erreur : {str(e)}"