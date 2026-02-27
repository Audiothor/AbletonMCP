# modules/core_tools.py
import json
from typing import Dict, Any, List, Union

def register_tools(mcp, get_conn):
    """Module de base : Fournit des raccourcis simples à Claude."""

    @mcp.tool()
    def create_midi_track(index: int = -1) -> str:
        """Crée une nouvelle piste MIDI dans Ableton."""
        try:
            get_conn().send_command("universal_accessor", {"action": "call", "path": "song.create_midi_track", "value": index})
            return "Piste MIDI créée avec succès."
        except Exception as e: 
            return f"Erreur LOM: {str(e)}"

    @mcp.tool()
    def create_audio_track(index: int = -1) -> str:
        """Crée une nouvelle piste Audio dans Ableton."""
        try:
            get_conn().send_command("universal_accessor", {"action": "call", "path": "song.create_audio_track", "value": index})
            return "Piste Audio créée avec succès."
        except Exception as e: 
            return f"Erreur LOM: {str(e)}"

    @mcp.tool()
    def create_clip(track_index: int, clip_index: int, length: float = 4.0) -> str:
        """Crée un clip MIDI de la longueur spécifiée sur une piste existante."""
        try:
            path = f"song.tracks[{track_index}].clip_slots[{clip_index}].create_clip"
            get_conn().send_command("universal_accessor", {"action": "call", "path": path, "value": float(length)})
            return f"Clip créé (Piste {track_index}, Slot {clip_index}, Longueur {length})"
        except Exception as e: 
            return f"Erreur LOM: {str(e)}"

    @mcp.tool()
    def fire_clip(track_index: int, clip_index: int) -> str:
        """Lance la lecture d'un clip spécifique."""
        try:
            path = f"song.tracks[{track_index}].clip_slots[{clip_index}].fire"
            get_conn().send_command("universal_accessor", {"action": "call", "path": path})
            return f"Lecture du clip {clip_index} sur la piste {track_index} démarrée."
        except Exception as e: 
            return f"Erreur LOM: {str(e)}"

    @mcp.tool()
    def set_tempo(tempo: float) -> str:
        """Modifie le tempo global du projet."""
        try:
            get_conn().send_command("universal_accessor", {"action": "set", "path": "song.tempo", "value": float(tempo)})
            return f"Tempo réglé sur {tempo} BPM."
        except Exception as e: 
            return f"Erreur LOM: {str(e)}"

    @mcp.tool()
    def get_clip_length(track_index: int, clip_index: int) -> str:
        """
        Permet de connaitre la longueur exacte d'un clip en beats (temps).
        OBLIGATOIRE : Utilise TOUJOURS cet outil avant d'utiliser add_notes_to_clip 
        pour savoir exactement combien de mesures tu dois remplir avec tes notes !
        """
        try:
            path = f"song.tracks[{track_index}].clip_slots[{clip_index}].clip.length"
            res = get_conn().send_command("universal_accessor", {"action": "get", "path": path})
            return f"La longueur du clip est de {res} beats."
        except Exception as e: 
            return f"Erreur : {str(e)} (Le clip n'existe peut-être pas ou est vide)"
            
    @mcp.tool()
    def add_notes_to_clip(track_index: int, clip_index: int, notes: List[Dict[str, Union[int, float, bool]]]) -> str:
        """
        Ajoute des notes MIDI a un clip existant.
        INSTRUCTIONS MUSICALES STRICTES : 
        1. Chaque note doit avoir : 'pitch', 'start', 'dur', 'vel', 'mute'. L'unite est le Beat.
        2. REGLE ANTI-PARESSE : Avant d'utiliser cet outil, utilise 'get_clip_length' ! 
           Si le clip fait 16 beats, tu DOIS generer des notes jusqu'a start=16. 
           Ne laisse jamais la fin d'un clip vide, duplique tes patterns mathématiquement.
        """
        try:
            get_conn().send_command("add_midi_notes", {"track_index": track_index, "clip_index": clip_index, "notes": notes})
            return f"Succès: {len(notes)} notes ajoutées."
        except Exception as e: 
            return f"Erreur MIDI: {str(e)}"

    @mcp.tool()
    def read_midi_notes(track_index: int, clip_index: int) -> str:
        """Lit et retourne toutes les notes MIDI présentes dans un clip existant."""
        try:
            res = get_conn().send_command("read_midi_notes", {"track_index": track_index, "clip_index": clip_index})
            return json.dumps(res, indent=2)
        except Exception as e: 
            return f"Erreur de lecture MIDI: {str(e)}"

    @mcp.tool()
    def clear_midi_notes(track_index: int, clip_index: int) -> str:
        """
        Efface toutes les notes MIDI d'un clip. 
        INDISPENSABLE à utiliser avant de réécrire une nouvelle progression d'accords.
        """
        try:
            res = get_conn().send_command("clear_midi_notes", {"track_index": track_index, "clip_index": clip_index})
            return res
        except Exception as e: 
            return f"Erreur: {str(e)}"
            
    @mcp.tool()
    def load_instrument(track_index: int, instrument_name: str) -> str:
        """
        Charge un instrument (Natif ou VST) sur une piste via le navigateur.
        
        REGLES MUSICALES ET TECHNIQUES OBLIGATOIRES :
        1. DRUMS / BATTERIE : Ne demande JAMAIS "Drum Rack" (c'est un dossier, cela va planter). 
           Tu DOIS demander EXACTEMENT l'un de ces kits natifs : 
           "808 Core Kit", "909 Core Kit", "707 Core Kit", "505 Core Kit".
        2. SYNTHES : Utilise "Analog", "Wavetable", "Operator", "Tension", ou "Impulse".
        3. TIMING : Charge les instruments STRICTEMENT UN PAR UN. Attends la reponse avant le suivant.
        """
        try:
            res = get_conn().send_command("load_device", {"track_index": track_index, "device_name": instrument_name})
            return f"Résultat du chargement: {res}"
        except Exception as e: 
            return f"Erreur: {str(e)}"