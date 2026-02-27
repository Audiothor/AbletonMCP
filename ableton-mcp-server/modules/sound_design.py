# modules/sound_design.py
# Exemple : "Ajoute de la Reverb sur la piste 2, et mets le Dry/Wet à 0.35 (35%)."
#           "Le synthé sur la piste 1 est trop agressif. Applique un filtre passe-bas à 800Hz avec une légère résonance."
#           "Mets un Delay sur la piste 0 et monte le Feedback à 0.6."

import logging

logger = logging.getLogger("AbletonUniversalServer.SoundDesign")

def register_tools(mcp, get_conn):
    
    @mcp.tool()
    def add_audio_effect(track_index: int, effect_name: str) -> str:
        """
        Charge un effet audio natif Ableton sur une piste.
        Exemples d'effect_name: "Auto Filter", "Reverb", "Delay", "EQ Eight", "Compressor", "Utility".
        """
        logger.info(f"🎛️ Chargement de l'effet '{effect_name}' sur la piste {track_index}")
        try:
            conn = get_conn()
            # On réutilise la fonction load_device qui cherche déjà dans les Audio Effects
            res = conn.send_command("load_device", {
                "track_index": track_index,
                "device_name": effect_name
            })
            return f"Résultat de l'ajout de l'effet : {res}"
        except Exception as e:
            logger.error(f"Erreur lors de l'ajout de l'effet : {str(e)}")
            return f"Erreur : {str(e)}"

    @mcp.tool()
    def tweak_effect_parameter(track_index: int, device_name: str, param_name: str, value: float) -> str:
        """
        Modifie un paramètre spécifique d'un effet audio.
        device_name: Le nom de l'effet (ex: "Auto Filter", "Reverb").
        param_name: Le nom du paramètre (ex: "Frequency", "Resonance", "Dry/Wet", "DecayTime").
        value: La valeur souhaitée (attention aux limites du plugin).
        """
        logger.info(f"🎚️ Réglage: Piste {track_index} > {device_name} > {param_name} = {value}")
        try:
            conn = get_conn()
            res = conn.send_command("set_device_param", {
                "track_index": track_index,
                "device_name": device_name,
                "param_name": param_name,
                "value": value
            })
            return res
        except Exception as e:
            return f"Erreur de paramétrage : {str(e)}"

    @mcp.tool()
    def apply_lowpass_filter(track_index: int, cutoff_hz: float = 500.0, resonance: float = 0.5) -> str:
        """
        Outil macro : Ajoute un Auto Filter et le configure immédiatement en passe-bas (Lowpass).
        cutoff_hz: Fréquence de coupure (ex: 200 pour étouffer le son, 2000 pour l'ouvrir).
        resonance: Résonance (Q) de 0.0 à 1.0.
        """
        logger.info(f"🎛️ Application Macro Lowpass (Cutoff: {cutoff_hz}Hz) sur piste {track_index}")
        try:
            conn = get_conn()
            
            # 1. On charge l'Auto Filter
            add_res = conn.send_command("load_device", {
                "track_index": track_index,
                "device_name": "Auto Filter"
            })
            
            # 2. On règle la fréquence
            freq_res = conn.send_command("set_device_param", {
                "track_index": track_index,
                "device_name": "Auto Filter",
                "param_name": "Frequency",
                "value": cutoff_hz
            })
            
            # 3. On règle la résonance
            res_res = conn.send_command("set_device_param", {
                "track_index": track_index,
                "device_name": "Auto Filter",
                "param_name": "Resonance",
                "value": resonance
            })
            
            return f"Macro Lowpass appliquée : {add_res} | {freq_res} | {res_res}"
        except Exception as e:
            return f"Erreur de la macro Lowpass : {str(e)}"