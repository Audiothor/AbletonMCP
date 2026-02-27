# AbletonMCP/__init__.py
from __future__ import absolute_import, print_function, unicode_literals
from _Framework.ControlSurface import ControlSurface
import socket, json, threading, traceback, re
import Live

try: import Queue as queue
except ImportError: import queue

DEFAULT_PORT, HOST = 9877, "localhost"

def create_instance(c_instance): return AbletonMCP(c_instance)

class AbletonMCP(ControlSurface):
    def __init__(self, c_instance):
        ControlSurface.__init__(self, c_instance)
        self.log_message("==============================================")
        self.log_message("   AbletonMCP V13 - SAMPLE LOADER ENABLED     ")
        self.log_message("==============================================")
        self.running = True
        self.start_server()

    def disconnect(self):
        self.running = False
        if hasattr(self, 'server') and self.server: 
            try: self.server.close()
            except: pass
        ControlSurface.disconnect(self)

    def start_server(self):
        try:
            self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server.bind((HOST, DEFAULT_PORT))
            self.server.listen(5)
            t = threading.Thread(target=self._server_thread)
            t.daemon = True
            t.start()
        except Exception as e: self.log_message("Server Error: " + str(e))

    def _server_thread(self):
        self.server.settimeout(1.0)
        while self.running:
            try:
                client, _ = self.server.accept()
                threading.Thread(target=self._handle_client, args=(client,)).start()
            except socket.timeout: continue

    def _handle_client(self, client):
        client.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        buffer = ''
        try:
            while self.running:
                data = client.recv(8192)
                if not data: break
                try: buffer += data.decode('utf-8')
                except: buffer += data
                try:
                    cmd = json.loads(buffer)
                    buffer = ''
                    resp = self._process_command(cmd)
                    res_json = json.dumps(resp)
                    try: client.sendall(res_json.encode('utf-8'))
                    except: client.sendall(res_json)
                except ValueError: continue
        except Exception as e:
            self.log_message("Client Error: " + str(e))
        finally: 
            client.close()

    def _process_command(self, command):
        cmd_type = command.get("type", "")
        params = command.get("params", {})
        
        self.log_message("--- EXECUTION: " + cmd_type + " ---")
        
        res_q = queue.Queue()
        def task():
            try:
                if cmd_type == "universal_accessor": res = self._navigate_and_execute(params)
                elif cmd_type == "load_device": res = self._load_device_by_name(params)
                elif cmd_type == "load_sample": res = self._load_sample(params)
                elif cmd_type == "delete_device": res = self._delete_device(params)
                elif cmd_type == "add_midi_notes": res = self._add_midi_notes(params)
                elif cmd_type == "read_midi_notes": res = self._read_midi_notes(params)
                elif cmd_type == "clear_midi_notes": res = self._clear_midi_notes(params)
                elif cmd_type == "set_device_param": res = self._set_device_param_by_name(params)
                elif cmd_type == "add_automation": res = self._add_automation_by_name(params)
                elif cmd_type == "get_session_info": res = {"tempo": self.song().tempo, "tracks": len(self.song().tracks)}
                else: raise Exception("Unknown command: " + cmd_type)
                res_q.put({"status": "success", "result": res})
            except Exception as e: 
                err_msg = str(e) + "\n" + traceback.format_exc()
                self.log_message("Command Error: " + err_msg)
                res_q.put({"status": "error", "message": str(e)})
        self.schedule_message(0, task)
        return res_q.get(timeout=15.0)

    # --- SOUS-FONCTIONS DU LOM ---
    def _navigate_and_execute(self, params):
        action = params.get("action")
        path_str = params.get("path", "")
        value = params.get("value")
        path_str = path_str.replace("live_set.", "song.").replace("live_set", "song")
        path_str = re.sub(r'([a-zA-Z_]+)\s+(\d+)', r'\1[\2]', path_str) 
        path_str = path_str.replace(" ", ".")
        if "app.browser" in path_str or "application.browser" in path_str:
            obj = self.application().browser
            path_str = path_str.split("browser")[-1].strip(".")
        elif path_str.startswith("application") or path_str.startswith("app"):
            obj = self.application()
            path_str = path_str.replace("application", "", 1).replace("app", "", 1).strip(".")
        elif path_str.startswith("browser"):
            obj = self.application().browser
            path_str = path_str.replace("browser", "", 1).strip(".")
        elif path_str.startswith("song"):
            obj = self.song()
            path_str = path_str.replace("song", "", 1).strip(".")
        else:
            obj = self.song()
            
        parts = [p for p in path_str.split(".") if p]
        if not parts: return str(obj)

        for part in parts[:-1]:
            if "[" in part:
                name, idx = part.split("[")[0], int(part.split("[")[1].replace("]", ""))
                obj = getattr(obj, name)[idx]
            else: obj = getattr(obj, part)
        attr = parts[-1]
        
        if "[" in attr:
            name, idx = attr.split("[")[0], int(attr.split("[")[1].replace("]", ""))
            obj = getattr(obj, name)
            if action == "get":
                val = obj[idx]
                return str(val.name) if hasattr(val, 'name') else str(val)
        else:
            if action == "get":
                val = getattr(obj, attr)
                try: 
                    if isinstance(val, (str, unicode)): return val
                except NameError:
                    if isinstance(val, str): return val
                if isinstance(val, (int, float, bool)): return val
                if val is None: return None
                return [str(i) for i in val] if hasattr(val, "__iter__") else str(val) if hasattr(val, 'name') else str(val)
            elif action == "set": 
                if hasattr(obj, "min") and hasattr(obj, "max") and isinstance(value, (int, float)):
                    value = max(obj.min, min(obj.max, float(value)))
                try:
                    setattr(obj, attr, value)
                except Exception as e:
                    if isinstance(value, int): 
                        try:
                            setattr(obj, attr, float(value))
                            return True
                        except: pass
                    raise Exception("Valeur invalide. Erreur : " + str(e))
                return True
            elif action == "call":
                m = getattr(obj, attr)
                args = value if isinstance(value, list) else ([value] if value is not None else [])
                res = m(*args)
                if res is None: return True
                if isinstance(res, (int, float, bool, str)): return res
                try:
                    if isinstance(res, unicode): return res
                except NameError: pass
                return str(res)

    def _add_midi_notes(self, params):
        t_idx, c_idx = params.get("track_index"), params.get("clip_index")
        notes_raw = params.get("notes", [])
        track = self.song().tracks[t_idx]
        if not track.clip_slots[c_idx].has_clip: return "Erreur : Aucun clip à cet emplacement."
        clip = track.clip_slots[c_idx].clip
        notes_to_add = []
        for n in notes_raw:
            start_val = n.get("start_time", n.get("start", n.get("time", 0.0)))
            dur_val = n.get("duration", n.get("dur", n.get("length", 0.25)))
            vel_val = n.get("velocity", n.get("vel", 100))
            safe_vel = max(1, min(127, int(vel_val)))
            note = Live.Clip.MidiNoteSpecification(
                start_time=float(start_val), duration=float(dur_val),
                pitch=int(n.get("pitch", 60)), velocity=safe_vel, mute=bool(n.get("mute", False))
            )
            notes_to_add.append(note)
        clip.add_new_notes(tuple(notes_to_add))
        return "Notes ajoutées avec succès"

    def _read_midi_notes(self, params):
        t_idx, c_idx = params.get("track_index"), params.get("clip_index")
        track = self.song().tracks[t_idx]
        if not track.clip_slots[c_idx].has_clip: return "Erreur : Aucun clip."
        clip = track.clip_slots[c_idx].clip
        result = []
        try:
            notes = clip.get_notes_extended(0, 128, 0.0, 99999.0)
            for n in notes:
                result.append({"pitch": n.pitch, "start": n.start_time, "dur": n.duration, "vel": n.velocity, "mute": n.mute})
        except AttributeError:
            notes = clip.get_notes(0.0, 0, 99999.0, 128)
            for n in notes:
                result.append({"pitch": int(n[0]), "start": float(n[1]), "dur": float(n[2]), "vel": int(n[3]), "mute": bool(n[4])})
        return result

    def _clear_midi_notes(self, params):
        t_idx, c_idx = params.get("track_index"), params.get("clip_index")
        track = self.song().tracks[t_idx]
        if not track.clip_slots[c_idx].has_clip: return "Erreur : Aucun clip."
        clip = track.clip_slots[c_idx].clip
        try: clip.remove_notes_extended(0, 128, 0.0, 99999.0)
        except AttributeError: clip.remove_notes(0.0, 0, 99999.0, 128)
        return "Clip vidé avec succès."

    def _delete_device(self, params):
        t_idx = params.get("track_index")
        device_name = params.get("device_name", "").lower()
        track = self.song().tracks[t_idx]
        deleted = False
        for i in range(len(track.devices) - 1, -1, -1):
            if device_name in track.devices[i].name.lower() or device_name == "all":
                track.delete_device(i)
                deleted = True
        if deleted: return "Plugins supprimés avec succès."
        return "Erreur : Plugin non trouvé sur cette piste."

    def _load_device_by_name(self, params):
        idx = params.get("track_index")
        raw_name = params.get("device_name", "").lower()
        for word in ["vsti", "vst3", "vst", "plugin", "audio unit", "au"]:
            raw_name = raw_name.replace(word, "")
        name = raw_name.strip()
        
        if name in ["drum rack", "drums", "drumrack"]:
            name = "909 core kit"
            
        browser = self.application().browser
        categories = [
            browser.instruments, browser.drums, browser.audio_effects, 
            browser.plugins, browser.max_for_live
        ]
        
        def find_item_exact(node):
            if hasattr(node, 'is_loadable') and node.is_loadable and node.name.lower() == name: return node
            if hasattr(node, 'children'):
                for child in node.children:
                    res = find_item_exact(child)
                    if res: return res
            return None
            
        def find_item_fuzzy(node):
            if hasattr(node, 'is_loadable') and node.is_loadable and name in node.name.lower(): return node
            if hasattr(node, 'children'):
                for child in node.children:
                    res = find_item_fuzzy(child)
                    if res: return res
            return None

        found = None
        for category in categories:
            found = find_item_exact(category)
            if found: break
            
        if not found:
            for category in categories:
                found = find_item_fuzzy(category)
                if found: break

        if found:
            self.application().view.selected_track = self.song().tracks[idx]
            browser.load_item(found)
            return "Loaded: " + str(found.name)
            
        return "Device '" + name + "' not found in Browser."

    # --- NOUVEAUTÉ V13 : CHARGER UN FICHIER AUDIO DEPUIS LA BIBLIOTHÈQUE ---
    def _load_sample(self, params):
        t_idx = params.get("track_index")
        c_idx = params.get("clip_index")
        sample_name = params.get("sample_name", "").lower()
        name = sample_name.strip()

        browser = self.application().browser
        
        # On fouille spécifiquement dans "Bibliothèque utilisateur" et "Places" (dossiers ajoutés)
        categories = [browser.user_library]
        if hasattr(browser, 'user_folders'):
            for folder in browser.user_folders:
                categories.append(folder)
        if hasattr(browser, 'packs'):
            categories.append(browser.packs)

        def find_item_exact(node):
            if hasattr(node, 'is_loadable') and node.is_loadable and node.name.lower() == name: return node
            if hasattr(node, 'children'):
                for child in node.children:
                    res = find_item_exact(child)
                    if res: return res
            return None

        def find_item_fuzzy(node):
            if hasattr(node, 'is_loadable') and node.is_loadable and name in node.name.lower(): return node
            if hasattr(node, 'children'):
                for child in node.children:
                    res = find_item_fuzzy(child)
                    if res: return res
            return None

        found = None
        for category in categories:
            found = find_item_exact(category)
            if found: break

        if not found:
            for category in categories:
                found = find_item_fuzzy(category)
                if found: break

        if found:
            # On cible la piste et on sélectionne la bonne case (scene) pour y déposer l'audio
            self.application().view.selected_track = self.song().tracks[t_idx]
            try:
                self.application().view.selected_scene = self.song().scenes[c_idx]
            except: pass
            
            browser.load_item(found)
            return "Sample chargé avec succès : " + str(found.name)

        return "Sample '" + name + "' introuvable dans la Bibliothèque utilisateur ou les dossiers."

    def _set_device_param_by_name(self, params):
        t_idx = params.get("track_index")
        d_name = params.get("device_name").lower()
        p_name = params.get("param_name").lower()
        val = float(params.get("value"))
        track = self.song().tracks[t_idx]
        for dev in track.devices:
            if d_name in dev.name.lower():
                for param in dev.parameters:
                    if p_name in param.name.lower():
                        clamped_val = max(param.min, min(param.max, val))
                        param.value = clamped_val
                        return "Succès: " + str(param.name) + " réglé sur " + str(clamped_val)
        return "Erreur: Plugin ou paramètre introuvable."

    def _add_automation_by_name(self, params):
        t_idx = params.get("track_index")
        c_idx = params.get("clip_index")
        d_name = params.get("device_name").lower()
        p_name = params.get("param_name").lower()
        points = params.get("points", [])
        track = self.song().tracks[t_idx]
        if not track.clip_slots[c_idx].has_clip: return "Erreur : Aucun clip."
        clip = track.clip_slots[c_idx].clip
        for dev in track.devices:
            if d_name in dev.name.lower():
                for param in dev.parameters:
                    if p_name in param.name.lower():
                        env = clip.automation_envelope(param)
                        if env is None: return "Erreur création enveloppe"
                        env.clear_all_events()
                        for pt in points:
                            time = float(pt.get("time", 0.0))
                            norm_val = float(pt.get("value", 0.5))
                            actual_val = param.min + (norm_val * (param.max - param.min))
                            actual_val = max(param.min, min(param.max, actual_val))
                            env.insert_step(time, actual_val)
                        return "Automation ajoutée sur " + param.name
        return "Erreur: Plugin/paramètre introuvable."