# modules/arrangement.py
# Exemple :
#         - L'architecte : "Prépare-moi une structure de morceau pop classique."
#         Claude appellera build_song_skeleton(["Intro", "Couplet 1", "Pré-Refrain", "Refrain", "Break", "Refrain Final"]). Ta vue Session sera instantanément renommée et organisée.
#         - L'arrangeur soustractif (Le secret de la musique électronique) : "Le Refrain à la ligne 3 est parfait. Duplique-le pour faire le Couplet 2, mais retire la grosse caisse (piste 0) et le synthé lead (piste 3)."
#        Claude appellera create_variation_from_scene(source_scene_index=3, new_scene_name="Couplet 2", tracks_to_clear=[0, 3]). Ableton va dupliquer la ligne complète et vider les cases 0 et 3.
#         - Le chef d'orchestre : "Lance la lecture du Break (scène 4) pour qu'on écoute ce que ça donne."

import logging

logger = logging.getLogger("AbletonUniversal.Arrangement")

def register_tools(mcp, get_conn):
    
    @mcp.tool()
    def build_song_skeleton(sections: list) -> str:
        """Construit la structure du morceau en nommant les scènes de la vue Session."""
        logger.info(f"🏗️ Création du squelette du morceau : {sections}")
        conn = get_conn()
        try:
            logger.debug("-> Étape 1 : Récupération du nombre de scènes actuelles via LOM")
            scenes_raw = conn.send_command("universal_accessor", {"action": "get", "path": "song.scenes"})
            current_scene_count = len(scenes_raw) if isinstance(scenes_raw, list) else 1
            
            logger.debug(f"-> Étape 2 : Création des scènes manquantes (Actuel: {current_scene_count}, Cible: {len(sections)})")
            while current_scene_count < len(sections):
                conn.send_command("universal_accessor", {"action": "call", "path": "song.create_scene", "value": -1})
                current_scene_count += 1
            
            logger.debug("-> Étape 3 : Renommage de chaque scène")
            for i, name in enumerate(sections):
                conn.send_command("universal_accessor", {"action": "set", "path": f"song.scenes[{i}].name", "value": str(name)})
                
            return f"✅ Structure créée avec {len(sections)} sections : {', '.join(sections)}."
        except Exception as e:
            logger.error(f"Erreur Skeleton: {str(e)}")
            return f"Erreur : {str(e)}"

    @mcp.tool()
    def create_variation_from_scene(source_scene_index: int, new_scene_name: str, tracks_to_clear: list) -> str:
        """Duplique une scène pleine pour créer une variation."""
        logger.info(f"✂️ Duplication de la scène {source_scene_index} -> '{new_scene_name}'")
        logger.debug(f"-> Pistes à nettoyer (Mute) : {tracks_to_clear}")
        
        conn = get_conn()
        try:
            logger.debug("-> Action LOM : Duplication de la scène source")
            conn.send_command("universal_accessor", {"action": "call", "path": "song.duplicate_scene", "value": source_scene_index})
            
            new_scene_index = source_scene_index + 1
            
            logger.debug(f"-> Action LOM : Renommage de la nouvelle scène (index {new_scene_index}) en '{new_scene_name}'")
            conn.send_command("universal_accessor", {"action": "set", "path": f"song.scenes[{new_scene_index}].name", "value": new_scene_name})
            
            cleared_count = 0
            for t_idx in tracks_to_clear:
                logger.debug(f"-> Action LOM : Vérification de présence de clip sur la piste {t_idx}")
                has_clip = conn.send_command("universal_accessor", {
                    "action": "get", 
                    "path": f"song.tracks[{t_idx}].clip_slots[{new_scene_index}].has_clip"
                })
                
                if str(has_clip).lower() == "true":
                    logger.debug(f"   ↳ Clip trouvé sur piste {t_idx} ! Action LOM : Suppression du clip.")
                    conn.send_command("universal_accessor", {
                        "action": "call", 
                        "path": f"song.tracks[{t_idx}].clip_slots[{new_scene_index}].delete_clip"
                    })
                    cleared_count += 1
                else:
                    logger.debug(f"   ↳ Aucun clip sur piste {t_idx}, on ignore.")
            
            return f"✅ Variation '{new_scene_name}' créée. {cleared_count} instruments supprimés."
        except Exception as e:
            logger.error(f"Erreur Variation: {str(e)}")
            return f"Erreur : {str(e)}"