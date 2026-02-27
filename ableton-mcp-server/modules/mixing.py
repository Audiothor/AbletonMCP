# modules/mixing.py
# Exemple : "Tu peux faire une analyse de mon mixage ?"

import logging
import json

logger = logging.getLogger("AbletonUniversalServer.Mixing")

def register_tools(mcp, get_conn):
    
    @mcp.tool()
    def analyze_mix() -> str:
        """
        Analyse les niveaux de mixage actuels de toutes les pistes et du Master.
        Détecte les faders réglés trop hauts (risque de saturation) et les déséquilibres.
        Demande à l'utilisateur de lancer la lecture du morceau avant d'utiliser cet outil pour obtenir les crêtes audio (peaks).
        """
        logger.info("🎛️ Analyse du mixage en cours...")
        conn = get_conn()
        report = []
        
        try:
            # 1. Obtenir le nombre de pistes
            session_info = conn.send_command("get_session_info")
            track_count = session_info.get("tracks", 0)
            
            # 2. Analyser le Master
            master_vol = conn.send_command("universal_accessor", {
                "action": "get", "path": "song.master_track.mixer_device.volume.value"
            })
            master_peak = conn.send_command("universal_accessor", {
                "action": "get", "path": "song.master_track.output_meter_level"
            })
            
            report.append(f"👑 MASTER - Fader Volume: {float(master_vol):.2f} (Max 1.0) | Crête audio actuelle: {float(master_peak):.2f}")
            if float(master_peak) >= 0.99:
                report.append("  ⚠️ ALERTE : Le Master sature ou est dangereusement proche du 0 dB !")

            # 3. Analyser chaque piste individuelle
            for i in range(track_count):
                name = conn.send_command("universal_accessor", {
                    "action": "get", "path": f"song.tracks[{i}].name"
                })
                vol = conn.send_command("universal_accessor", {
                    "action": "get", "path": f"song.tracks[{i}].mixer_device.volume.value"
                })
                peak = conn.send_command("universal_accessor", {
                    "action": "get", "path": f"song.tracks[{i}].output_meter_level"
                })
                
                track_status = f"Piste {i} ({name}) - Fader: {float(vol):.2f} | Crête audio: {float(peak):.2f}"
                
                # Détection de déséquilibre / saturation
                if float(vol) > 0.85:
                    track_status += " ⚠️ Fader très haut (Baisse le gain de l'instrument)"
                if float(peak) >= 0.95:
                    track_status += " 🚨 PIC DÉTECTÉ (Saturation possible)"
                    
                report.append(track_status)

            # Formatage du retour pour Claude
            final_report = "\n".join(report)
            logger.info("✅ Analyse de mixage terminée.")
            return f"Rapport de mixage :\n{final_report}\n\nNote: Si les crêtes audio sont toutes à 0.00, demande à l'utilisateur de lancer la lecture (Play) et relance l'analyse."
            
        except Exception as e:
            logger.error(f"Erreur lors de l'analyse du mix: {str(e)}")
            return f"Erreur d'analyse : {str(e)}"