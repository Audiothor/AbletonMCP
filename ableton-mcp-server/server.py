# ableton-mcp-server/server.py
from mcp.server.fastmcp import FastMCP
import socket
import json
import logging
import time
import os
import importlib
import threading
import sys
from dataclasses import dataclass
from typing import Dict, Any, Optional

# --- INFORMATIONS DU PROGRAMME ---
APP_NAME = "AbletonMCP Server"
VERSION = "5.2.1"
APP_AUTHOR = "François SENELLART"
DEBUG_MODE = False

# Configuration logging
log_level = logging.DEBUG if DEBUG_MODE else logging.INFO
logging.basicConfig(
    level=log_level, 
    format='%(asctime)s - [%(levelname)s] - %(name)s : %(message)s',
    stream=sys.stderr
)
logger = logging.getLogger("AbletonUniversalServer")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

# --- VERROU GLOBAL RÉSEAU ---
# Empêche Claude d'envoyer deux ordres en même temps dans le même socket
_ableton_lock = threading.Lock()

@dataclass
class AbletonConnection:
    host: str
    port: int
    
    def check_connection(self) -> bool:
        """Vérifie si le Remote Script est actif."""
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(1.0)
            s.connect((self.host, self.port))
            s.close()
            return True
        except:
            return False

    def receive_full_response(self, sock, buffer_size=8192):
        """Lit la réponse JSON complète envoyée par Ableton."""
        chunks = []
        sock.settimeout(5.0)
        while True:
            try:
                chunk = sock.recv(buffer_size)
                if not chunk: break 
                chunks.append(chunk)
                try:
                    data = b''.join(chunks)
                    json.loads(data.decode('utf-8'))
                    return data
                except json.JSONDecodeError: 
                    continue
            except socket.timeout: 
                break
            except Exception: 
                break
            
        if chunks: 
            return b''.join(chunks)
        raise Exception("Aucune donnée reçue d'Ableton")

    def send_command(self, command_type: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
        """Envoie une commande unique et sécurisée au Remote Script."""
        with _ableton_lock:
            # SÉCURITÉ ANTI-NONE : On vérifie que la commande a un nom
            if not command_type:
                logger.error("Tentative d'envoi d'une commande vide (None)")
                raise ValueError("Le type de commande ne peut pas être vide")

            command = {"type": str(command_type), "params": params or {}}
            
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(10.0) # Temps suffisant pour les actions lourdes
            try:
                sock.connect((self.host, self.port))
                sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
                
                # Logging de la commande sortante
                if command_type != "get_session_info":
                    logger.info(f"📤 [ENVOI] {command_type} | Piste: {params.get('track_index', '?')}")
                
                sock.sendall(json.dumps(command).encode('utf-8'))
                
                # Récupération de la réponse
                response_data = self.receive_full_response(sock)
                response = json.loads(response_data.decode('utf-8'))
                
                if response.get("status") == "error":
                    raise Exception(response.get("message"))
                
                return response.get("result", response)
                
            except Exception as e:
                logger.error(f"💥 Erreur de communication Ableton : {str(e)}")
                raise e
            finally:
                sock.close()

# --- INITIALISATION MCP ---
mcp = FastMCP("AbletonMCP_Modular")
_connection = None

def get_conn():
    global _connection
    if _connection is None:
        _connection = AbletonConnection(host="localhost", port=9877)
    return _connection

# --- OUTILS CORE ---
@mcp.tool()
def access_lom(action: str, path: str, value_json_str: Optional[str] = None) -> str:
    """Accès universel au Live Object Model (LOM)."""
    try:
        actual_val = json.loads(value_json_str) if value_json_str else None
        res = get_conn().send_command("universal_accessor", {"action": action, "path": path, "value": actual_val})
        return json.dumps(res, indent=2)
    except Exception as e:
        return f"Erreur LOM: {e}"

@mcp.tool()
def get_session_info() -> str:
    """Résumé rapide de la session Ableton."""
    try:
        return json.dumps(get_conn().send_command("get_session_info"), indent=2)
    except Exception as e:
        return str(e)

# --- BOUCLE DE SURVEILLANCE ---
def connection_monitor():
    conn = get_conn()
    was_connected = False
    while True:
        is_connected = conn.check_connection()
        if is_connected and not was_connected:
            logger.info(f"✅ Remote Script AbletonMCP détecté sur le port {conn.port}")
            was_connected = True
        elif not is_connected and was_connected:
            logger.warning("⚠️ Connexion perdue avec Ableton")
            was_connected = False
        time.sleep(5)

# --- CHARGEMENT DYNAMIQUE DES MODULES ---
def load_modules():
    logger.info("📦 Chargement des modules de fonctionnalités...")
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
                    logger.info(f"  ↳ ✅ {module_name}")
                    loaded += 1
            except Exception as e:
                logger.error(f"  ↳ ❌ Erreur dans {module_name}: {str(e)}")
    logger.info(f"🏁 Serveur MCP prêt ({loaded} modules)")

def main():
    load_modules()
    monitor_thread = threading.Thread(target=connection_monitor, daemon=True)
    monitor_thread.start()
    
    try:
        mcp.run()
    except Exception as e:
        logger.error(f"💥 Erreur fatale : {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()