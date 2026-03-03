# modules/core_tools.py
import json
import time
import logging
from typing import Dict, Any, List, Union

logger = logging.getLogger("AbletonUniversalServer.CoreTools")

def register_tools(mcp, get_conn):
    """Module de base : Fournit des raccourcis simples et des macros à Claude."""

    @mcp.tool()
    def batch_multiple_ableton_actions(actions: List[Dict[str, Any]]) -> str:
        results = []
        conn = get_conn()
        
        for i, action in enumerate(actions):
            cmd = action.get("command") or action.get("type")
            p = action.get("params", {})
            
            try:
                # Pour CHAQUE action de chargement, on impose un délai de sécurité
                # Cela laisse le temps au Remote Script de finir son cycle schedule_message
                if cmd in ["load_device", "load_sample"]:
                    time.sleep(0.5) # Pause cruciale pour laisser l'UI d'Ableton respirer 
                
                res = conn.send_command(cmd, p)
                results.append(f"[{i+1}] {cmd}: {res}")
                
                # Pause après l'action pour stabiliser le focus
                time.sleep(0.2) 
                
            except Exception as e:
                results.append(f"[{i+1}] {cmd} ERREUR: {str(e)}")
                
        return "\n".join(results)
        
    @mcp.tool()
    def create_midi_track(index: int = -1) -> str:
        """Crée une nouvelle piste MIDI dans Ableton."""
        try:
            get_conn().send_command("universal_accessor", {"action": "call", "path": "song.create_midi_track", "value": index})
            return "Piste MIDI créée."
        except Exception as e: 
            return f"Erreur : {str(e)}"

    @mcp.tool()
    def create_audio_track(index: int = -1) -> str:
        """Crée une nouvelle piste Audio dans Ableton."""
        try:
            get_conn().send_command("universal_accessor", {"action": "call", "path": "song.create_audio_track", "value": index})
            return "Piste Audio créée."
        except Exception as e: 
            return f"Erreur : {str(e)}"

    @mcp.tool()
    def create_clip(track_index: int, clip_index: int, length: float = 4.0) -> str:
        """Crée un clip MIDI (Piste MIDI uniquement)."""
        try:
            path = f"song.tracks[{track_index}].clip_slots[{clip_index}].create_clip"
            get_conn().send_command("universal_accessor", {"action": "call", "path": path, "value": float(length)})
            return f"Clip créé (T:{track_index} C:{clip_index})"
        except Exception as e: 
            return f"Erreur : {str(e)}"

    @mcp.tool()
    def set_tempo(tempo: float) -> str:
        """Modifie le tempo global."""
        try:
            get_conn().send_command("universal_accessor", {"action": "set", "path": "song.tempo", "value": float(tempo)})
            return f"BPM : {tempo}"
        except Exception as e: 
            return f"Erreur : {str(e)}"

    @mcp.tool()
    def get_clip_length(track_index: int, clip_index: int) -> str:
        """Retourne la longueur du clip en beats."""
        try:
            path = f"song.tracks[{track_index}].clip_slots[{clip_index}].clip.length"
            res = get_conn().send_command("universal_accessor", {"action": "get", "path": path})
            return f"Longueur : {res} beats"
        except Exception as e: 
            return f"Erreur : {str(e)}"
            
    @mcp.tool()
    def add_notes_to_clip(track_index: int, clip_index: int, notes: List[Dict[str, Union[int, float, bool]]]) -> str:
        """Ajoute des notes MIDI à un clip existant."""
        try:
            get_conn().send_command("add_midi_notes", {"track_index": track_index, "clip_index": clip_index, "notes": notes})
            return f"{len(notes)} notes ajoutées."
        except Exception as e: 
            return f"Erreur : {str(e)}"

    @mcp.tool()
    def clear_midi_notes(track_index: int, clip_index: int) -> str:
        """Efface les notes d'un clip."""
        try:
            return get_conn().send_command("clear_midi_notes", {"track_index": track_index, "clip_index": clip_index})
        except Exception as e: 
            return f"Erreur : {str(e)}"

    @mcp.tool()
    def load_instrument(track_index: int, instrument_name: str) -> str:
        """Charge un instrument sur une piste spécifique."""
        try:
            # On force le focus même hors macro pour la cohérence
            get_conn().send_command("universal_accessor", {
                "action": "set", "path": "song.view.selected_track", "value": track_index
            })
            time.sleep(0.1)
            return get_conn().send_command("load_device", {"track_index": track_index, "device_name": instrument_name})
        except Exception as e: 
            return f"Erreur : {str(e)}"