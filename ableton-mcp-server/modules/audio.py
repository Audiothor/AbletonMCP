# modules/audio.py
import json

def register_tools(mcp, get_conn):
    """Module spécifique pour manipuler les pistes et clips Audio dans Ableton."""

    @mcp.tool()
    def arm_and_record_audio(track_index: int, clip_index: int) -> str:
        """
        Arme une piste audio (ou MIDI) et lance l'enregistrement en direct dans un slot spécifique.
        Utile pour dire 'Lance l'enregistrement sur la piste 1'.
        """
        try:
            # Armer la piste
            get_conn().send_command("universal_accessor", {"action": "set", "path": f"song.tracks[{track_index}].arm", "value": True})
            # Lancer l'enregistrement (fire du slot)
            get_conn().send_command("universal_accessor", {"action": "call", "path": f"song.tracks[{track_index}].clip_slots[{clip_index}].fire"})
            return f"Piste {track_index} armée et enregistrement lancé sur le clip {clip_index}."
        except Exception as e:
            return f"Erreur d'enregistrement: {str(e)}"

    @mcp.tool()
    def edit_audio_clip_loop(track_index: int, clip_index: int, looping: bool, loop_start: float, loop_end: float) -> str:
        """
        Active/Désactive la boucle (Loop) sur un clip audio existant et définit ses points.
        Les unités loop_start et loop_end sont en Beats (temps).
        """
        try:
            base_path = f"song.tracks[{track_index}].clip_slots[{clip_index}].clip"
            get_conn().send_command("universal_accessor", {"action": "set", "path": f"{base_path}.looping", "value": looping})
            if looping:
                get_conn().send_command("universal_accessor", {"action": "set", "path": f"{base_path}.loop_start", "value": float(loop_start)})
                get_conn().send_command("universal_accessor", {"action": "set", "path": f"{base_path}.loop_end", "value": float(loop_end)})
            return f"Boucle audio modifiée (Loop={looping}, Start={loop_start}, End={loop_end})."
        except Exception as e:
            return f"Erreur de boucle: {str(e)}"

    @mcp.tool()
    def edit_audio_clip_warp(track_index: int, clip_index: int, warping: bool) -> str:
        """
        Active ou désactive le Warping (synchronisation au tempo du projet) sur un clip audio.
        """
        try:
            base_path = f"song.tracks[{track_index}].clip_slots[{clip_index}].clip"
            get_conn().send_command("universal_accessor", {"action": "set", "path": f"{base_path}.warping", "value": warping})
            return f"Warping réglé sur {'Activé' if warping else 'Désactivé'}."
        except Exception as e:
            return f"Erreur de warping: {str(e)}"

    @mcp.tool()
    def edit_audio_clip_pitch(track_index: int, clip_index: int, pitch_coarse: int) -> str:
        """
        Transpose (Pitch) un clip audio existant.
        pitch_coarse : Demi-tons entiers (ex: -12 pour 1 octave plus bas, +7 pour une quinte).
        """
        try:
            base_path = f"song.tracks[{track_index}].clip_slots[{clip_index}].clip"
            # Sécurité pour limiter la transposition à des valeurs acceptables par Ableton (-48 à +48)
            safe_pitch = max(-48, min(48, int(pitch_coarse)))
            get_conn().send_command("universal_accessor", {"action": "set", "path": f"{base_path}.pitch_coarse", "value": safe_pitch})
            return f"Pitch audio modifié à {safe_pitch} demi-tons."
        except Exception as e:
            return f"Erreur de pitch: {str(e)}"

    @mcp.tool()
    def load_sample(track_index: int, clip_index: int, sample_name: str) -> str:
        """
        Cherche un fichier audio (.wav, .aif) dans la Bibliothèque Utilisateur d'Ableton 
        ou les dossiers ajoutés (Places), et le charge dans un clip audio spécifique.
        OBLIGATOIRE : La piste ciblée doit être une piste AUDIO (utilise create_audio_track si besoin).
        Exemple de sample_name : "80s Beat 90 bpm" ou "Ambient Swells"
        """
        try:
            res = get_conn().send_command("load_sample", {
                "track_index": track_index,
                "clip_index": clip_index,
                "sample_name": sample_name
            })
            return res
        except Exception as e:
            return f"Erreur de chargement de sample: {str(e)}"