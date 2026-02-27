# modules/core_tools.py
import json
from typing import Dict, Any, List, Union

def register_tools(mcp, get_conn):
    """Module de base : Fournit des raccourcis simples à Claude."""

    @mcp.tool()
    def batch_multiple_ableton_actions(actions: List[Dict[str, Any]]) -> str:
        """
        ⚠️ ATTENTION : Si tu as PLUSIEURS actions à faire à la suite, tu DOIS utiliser cet outil.
        
        Exécute une série de commandes Ableton en une seule fois (Macro).
        Commandes supportées : "load_device" (ou "load_instrument"), "add_midi_notes", "clear_midi_notes", "delete_device", "create_clip", "set_tempo", "rename_track".
        
        REGLE IMPORTANTE : Si tu veux charger un instrument ou créer un clip MIDI, ASSURE-TOI d'abord que la piste est bien une piste MIDI, sinon Ableton rejettera la commande !
        """
        results = []
        for i, action in enumerate(actions):
            cmd = action.get("command")
            p = action.get("params", {})
            
            # --- CORRECTION DU SYNONYME ---
            if cmd == "load_instrument":
                cmd = "load_device"
                
            try:
                if cmd == "create_clip":
                    path = f"song.tracks[{p['track_index']}].clip_slots[{p['clip_index']}].create_clip"
                    res = get_conn().send_command("universal_accessor", {"action": "call", "path": path, "value": float(p.get('length', 4.0))})
                
                elif cmd == "set_tempo":
                    res = get_conn().send_command("universal_accessor", {"action": "set", "path": "song.tempo", "value": float(p.get('tempo', 120.0))})
                
                elif cmd == "rename_track":
                    path = f"song.tracks[{p['track_index']}].name"
                    res = get_conn().send_command("universal_accessor", {"action": "set", "path": path, "value": str(p.get('name', 'Piste'))})

                elif cmd == "load_device":
                    track_idx = p.get('track_index')
                    path_devs = f"song.tracks[{track_idx}].devices"
                    
                    devs_before = get_conn().send_command("universal_accessor", {"action": "get", "path": path_devs})
                    count_before = len(devs_before) if isinstance(devs_before, list) else 0
                    
                    res = get_conn().send_command(cmd, p)
                    
                    if "Loaded" in str(res):
                        timeout = 10.0
                        start_time = time.time()
                        loaded = False
                        while time.time() - start_time < timeout:
                            devs_now = get_conn().send_command("universal_accessor", {"action": "get", "path": path_devs})
                            count_now = len(devs_now) if isinstance(devs_now, list) else 0
                            if count_now > count_before:
                                loaded = True
                                break
                            time.sleep(0.5)
                        if loaded: res += " [Vérification : Succès]"
                        else: res += " [Vérification : Timeout]"

                elif cmd in ["add_midi_notes", "clear_midi_notes", "delete_device"]:
                    res = get_conn().send_command(cmd, p)
                    
                else:
                    res = f"Commande ignorée: {cmd} n'est pas supportée dans la macro."
                
                results.append(f"[{i+1}/{len(actions)}] {cmd} : {res}")
            except Exception as e:
                # --- CORRECTION DE L'EFFET DOMINO ---
                # On note l'erreur mais on ENLEVE le 'break' pour que la macro continue ses autres tâches !
                results.append(f"[{i+1}/{len(actions)}] {cmd} ERREUR : {str(e)}")
                continue 
                
        return "\n".join(results)
        
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
        ⚠️ ATTENTION : Pour toute suite de plusieurs actions (ex: créer des pistes, charger des instruments, ajouter des notes), N'UTILISE PAS cet outil individuellement. 
        Utilise OBLIGATOIREMENT la macro 'batch_multiple_ableton_actions' ! La macro est spécialement programmée pour charger les instruments en toute sécurité.
        
        Charge un instrument (Natif ou VST) sur une piste via le navigateur.
        
        REGLES MUSICALES ET TECHNIQUES OBLIGATOIRES :
        1. DRUMS / BATTERIE : Ne demande JAMAIS "Drum Rack" (c'est un dossier). Demande EXACTEMENT : "808 Core Kit", "909 Core Kit", "707 Core Kit", ou "505 Core Kit".
        2. SYNTHES : Utilise "Analog", "Wavetable", "Operator", "Tension", ou "Impulse".
        """
        try:
            res = get_conn().send_command("load_device", {"track_index": track_index, "device_name": instrument_name})
            return f"Résultat du chargement: {res}"
        except Exception as e: 
            return f"Erreur: {str(e)}"