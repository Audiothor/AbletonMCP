# server.py
from mcp.server.fastmcp import FastMCP, Context
import socket
import json
import logging
import time
import os
import importlib
import threading
import sys
from dataclasses import dataclass
from typing import Dict, Any, List, Optional

# --- INFORMATIONS DU PROGRAMME ---
APP_NAME = "AbletonMCP Server"
VERSION = "5.1.0"
APP_AUTHOR = "François SENELLART"
DEBUG_MODE = False

# Configuration logging stricte sur stderr pour ne jamais faire planter Claude
log_level = logging.DEBUG if DEBUG_MODE else logging.INFO
logging.basicConfig(
    level=log_level, 
    format='%(asctime)s - [%(levelname)s] - %(name)s : %(message)s',
    stream=sys.stderr
)
logger = logging.getLogger("AbletonUniversalServer")

# --- FIX DU DOSSIER DE TRAVAIL ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

@dataclass
class AbletonConnection:
    host: str
    port: int
    sock: Optional[socket.socket] = None
    
    def check_connection(self) -> bool:
        """Vérifie si la connexion est réellement vivante côté Ableton."""
        if not self.sock:
            return False
        try:
            # PING FANTÔME : On envoie un simple saut à la ligne.
            # Si Ableton a été fermé, cela déclenchera immédiatement une erreur.
            # S'il est ouvert, le script d'Ableton ignorera ce caractère vide.
            self.sock.sendall(b'\n')
            return True
        except (socket.error, BrokenPipeError, ConnectionResetError):
            self.sock = None
            return False

    def connect(self) -> bool:
        if self.check_connection(): 
            return True
            
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.connect((self.host, self.port))
            self.sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
            return True
        except Exception:
            self.sock = None
            return False

    def receive_full_response(self, sock, buffer_size=8192):
        chunks = []
        sock.settimeout(15.0)
        try:
            while True:
                try:
                    chunk = sock.recv(buffer_size)
                    if not chunk: raise Exception("Connection closed")
                    chunks.append(chunk)
                    try:
                        data = b''.join(chunks)
                        json.loads(data.decode('utf-8'))
                        return data
                    except json.JSONDecodeError: continue
                except socket.timeout:
                    break
                except Exception as e:
                    raise e
        except Exception as e:
            raise e
            
        if chunks:
            data = b''.join(chunks)
            return data
        else: raise Exception("No data")

    def send_command(self, command_type: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
        if not self.sock and not self.connect():
            raise ConnectionError("Non connecté à Ableton")
        
        command = {"type": command_type, "params": params or {}}
        start_time = time.time()
        
        is_modifying = command_type in ["add_midi_notes", "load_device", "universal_accessor", "set_device_param", "add_automation"]
        
        try:
            if command_type == "universal_accessor":
                logger.debug(f"🔍 [LOM EXEC] {params.get('action', '').upper()} -> {params.get('path', '')}")
            elif command_type != "get_session_info":
                logger.debug(f"📤 [CMD] {command_type} | Params: {json.dumps(params)}")
                
            self.sock.sendall(json.dumps(command).encode('utf-8'))
            if is_modifying: time.sleep(0.1)
            
            self.sock.settimeout(35.0 if command_type == "load_device" else 15.0)
            
            response_data = self.receive_full_response(self.sock)
            response = json.loads(response_data.decode('utf-8'))
            execution_time = (time.time() - start_time) * 1000
            
            if response.get("status") == "error":
                logger.error(f"🔴 ERREUR ABLETON : {response.get('message')}")
                raise Exception(response.get("message"))
            
            if command_type != "get_session_info":
                logger.debug(f"📥 [REPONSE] ({execution_time:.1f}ms) | Taille: {len(response_data)} bytes")
            
            if is_modifying: time.sleep(0.1)
            return response.get("result", {})
            
        except Exception as e:
            logger.error(f"💥 Erreur de communication : {str(e)}")
            self.sock = None
            raise e

# --- INITIALISATION MCP ---
mcp = FastMCP("AbletonMCP_Modular")
_connection = None

def get_conn():
    global _connection
    if _connection is None:
        _connection = AbletonConnection(host="localhost", port=9877)
    return _connection

# --- OUTILS CORE (Système global) ---
@mcp.tool()
def access_lom(action: str, path: str, value_json_str: Optional[str] = None) -> str:
    """Accès universel au Live Object Model (LOM)."""
    try:
        actual_val = json.loads(value_json_str) if value_json_str else None
        res = get_conn().send_command("universal_accessor", {"action": action, "path": path, "value": actual_val})
        return json.dumps(res, indent=2)
    except Exception as e:
        if value_json_str:
            res = get_conn().send_command("universal_accessor", {"action": action, "path": path, "value": value_json_str})
            return json.dumps(res, indent=2)
        return f"Erreur LOM: {e}"

@mcp.tool()
def get_session_info() -> str:
    """Résumé rapide de la session."""
    try:
        return json.dumps(get_conn().send_command("get_session_info"), indent=2)
    except Exception as e:
        return str(e)


# --- BOUCLE DE SURVEILLANCE DE LA CONNEXION ---
def connection_monitor():
    """Vérifie l'état de la connexion et logue intelligemment."""
    conn = get_conn()
    was_connected = False
    
    while True:
        is_connected = conn.check_connection()
        
        if not is_connected:
            is_connected = conn.connect()
        
        if is_connected:
            if not was_connected:
                # N'affiche le message de succès qu'une seule fois quand la connexion est établie
                logger.info(f"✅ Succès : Le remote script AbletonMCP est joignable (Port {conn.port})")
                was_connected = True
        else:
            if was_connected:
                # Si on était connecté et qu'on perd la connexion
                logger.error(f"❌ ALERTE : Perte de connexion avec AbletonMCP sur le port {conn.port} ! Le logiciel a-t-il été fermé ?")
                was_connected = False
            
            # Boucle toutes les 5s UNIQUEMENT quand ce n'est pas joignable
            logger.warning(f"⏳ En attente du remote script AbletonMCP sur le port {conn.port}...")
            
        time.sleep(5)

# --- CHARGEMENT DYNAMIQUE DES MODULES ---
def load_modules():
    logger.info("📦 Recherche et chargement des modules...")
    modules_dir = os.path.join(BASE_DIR, "modules")
    
    if not os.path.exists(modules_dir):
        os.makedirs(modules_dir)
        with open(os.path.join(modules_dir, "__init__.py"), "w") as f: pass

    loaded = 0
    for filename in os.listdir(modules_dir):
        if filename.endswith(".py") and not filename.startswith("__"):
            module_name = filename[:-3]
            try:
                module = importlib.import_module(f"modules.{module_name}")
                if hasattr(module, "register_tools"):
                    module.register_tools(mcp, get_conn)
                    logger.info(f"  ↳ ✅ Module chargé : {module_name}")
                    loaded += 1
                else:
                    logger.warning(f"  ↳ ⚠️ Ignoré : {module_name} (Il manque 'register_tools')")
            except Exception as e:
                logger.error(f"  ↳ ❌ Erreur de chargement pour {module_name}: {str(e)}")
                
    logger.info(f"🏁 Serveur prêt ! ({loaded} modules externes chargés)")


def main():
    # 1. Bannière de démarrage
    logger.info("="*55)
    logger.info(f"🎵  {APP_NAME} - v{VERSION}")
    logger.info(f"    Licence MIT")
    logger.info(f"    Copyright (c) 2026 {APP_AUTHOR}")
    if DEBUG_MODE:
        logger.info("    [!] MODE DEBUG ACTIF")
    logger.info("="*55)
    
    logger.info("🚀 Démarrage de AbletonMCP server...")
    
    # 2. Chargement des modules
    load_modules()
    
    # 3. Lancement du thread de surveillance réseau
    monitor_thread = threading.Thread(target=connection_monitor, daemon=True)
    monitor_thread.start()
    
    # 4. Lancement du serveur MCP
    try:
        mcp.run()
    except Exception as e:
        logger.error(f"💥 Erreur fatale MCP : {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()