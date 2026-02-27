# modules/automation.py
# Exemple : "Ajoute un Auto Filter sur le synthé de la piste 2. Fais une automation de forme 'expo_riser' sur le paramètre 'Frequency' pour faire monter la tension sur 8 mesures !"
#           "Mets un effet 'Utility' sur la piste de la basse (piste 1), et applique la forme 'gater' sur le paramètre 'Gain' pour qu'elle hache le son de manière rythmique."
#           "Mets une forme 'glitch' sur le paramètre 'Pan' (panoramique) pour que le son saute de gauche à droite de façon aléatoire."

import logging
import math
import random

logger = logging.getLogger("AbletonUniversalServer.Automation")

def register_tools(mcp, get_conn):
    
    @mcp.tool()
    def draw_automation_shape(track_index: int, clip_index: int, device_name: str, param_name: str, shape: str, length_beats: float = 4.0) -> str:
        """
        Génère une courbe d'automation sur un paramètre d'effet ou d'instrument.
        device_name: Nom de l'effet (ex: "Auto Filter", "Utility").
        param_name: Nom du paramètre (ex: "Frequency", "Gain").
        shape: Forme de la courbe parmi : 
               "sweep_up" (Ouverture progressive),
               "sweep_down" (Fermeture progressive),
               "wobble" (LFO en triangle, monte et descend),
               "gater" (Hachage rythmique carré on/off),
               "expo_riser" (Montée exponentielle pour les drops),
               "glitch" (Valeurs aléatoires Sample & Hold).
        length_beats: Longueur de la boucle d'automation en temps (ex: 4.0 = 1 mesure).
        """
        shape = shape.lower()
        logger.info(f"📈 Génération automation '{shape}' sur {device_name} > {param_name}")
        
        points = []
        
        # 1. Ouverture classique (Min vers Max)
        if shape == "sweep_up":
            points = [
                {"time": 0.0, "value": 0.0},
                {"time": length_beats, "value": 1.0}
            ]
            
        # 2. Fermeture classique (Max vers Min)
        elif shape == "sweep_down":
            points = [
                {"time": 0.0, "value": 1.0},
                {"time": length_beats, "value": 0.0}
            ]
            
        # 3. Wobble LFO (Triangle qui monte et descend à la noire)
        elif shape == "wobble":
            steps = int(length_beats) # 1 bosse par temps
            for i in range(steps + 1):
                # Alterne entre 0.1 et 0.9
                val = 0.9 if i % 2 != 0 else 0.1
                points.append({"time": float(i), "value": val})
                
        # 4. Trance Gater (Hachage binaire en croches)
        elif shape == "gater":
            steps = int(length_beats * 2) # Croches
            for i in range(steps):
                time_start = float(i) * 0.5
                time_end = time_start + 0.25 # Laisse un silence de 0.25
                points.append({"time": time_start, "value": 1.0})
                points.append({"time": time_end, "value": 1.0})
                points.append({"time": time_end + 0.01, "value": 0.0}) # Chute instantanée
                points.append({"time": time_start + 0.49, "value": 0.0})
                
        # 5. Expo Riser (Montée exponentielle lente puis rapide)
        elif shape == "expo_riser":
            resolution = 16 # Nombre de points pour dessiner la courbe
            for i in range(resolution + 1):
                time = (i / resolution) * length_beats
                # Math.pow crée la courbe exponentielle
                val = math.pow(i / resolution, 3) 
                points.append({"time": time, "value": val})
                
        # 6. Random Glitch (Valeurs aléatoires en doubles croches)
        elif shape == "glitch":
            steps = int(length_beats * 4) # Doubles croches
            for i in range(steps):
                time = float(i) * 0.25
                # Valeur aléatoire maintenue jusqu'au prochain point (Sample & Hold)
                val = random.uniform(0.1, 0.9)
                points.append({"time": time, "value": val})
                points.append({"time": time + 0.24, "value": val}) # Maintient la valeur plateau
                
        else:
            return f"❌ Forme inconnue : {shape}. Choisis parmi : sweep_up, sweep_down, wobble, gater, expo_riser, glitch."

        # Envoi de la commande à Ableton
        try:
            conn = get_conn()
            res = conn.send_command("add_automation", {
                "track_index": track_index,
                "clip_index": clip_index,
                "device_name": device_name,
                "param_name": param_name,
                "points": points
            })
            return f"✅ Automation '{shape}' générée avec succès : {res}"
        except Exception as e:
            logger.error(f"Erreur d'automation : {str(e)}")
            return f"Erreur : {str(e)}"