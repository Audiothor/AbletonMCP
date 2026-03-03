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
        self.log_message("   AbletonMCP V26 - FINAL C++ & LOM FIX       ")
        self.log_message("==============================================")
        self._task_queue = queue.Queue()
        self._is_processing = False
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
            t = threading.Thread(target=self._listen)
            t.daemon = True
            t.start()
        except: self.log_message("Server Error: " + traceback.format_exc())

    def _listen(self):
        while self.running:
            try:
                conn, addr = self.server.accept()
                data = conn.recv(65536)
                if data:
                    try:
                        req = json.loads(data.decode('utf-8'))
                        self._process_request(conn, req)
                    except: conn.close()
                else: conn.close()
            except: pass

    def _process_request(self, conn, req):
        cmd_type = req.get("type") or req.get("command")
        params = req.get("params", {})
        try:
            conn.sendall(json.dumps({"status": "queued"}).encode('utf-8'))
            conn.close()
        except: pass
        if cmd_type:
            params["_retry_count"] = 0
            self._task_queue.put((cmd_type, params))
            if not self._is_processing:
                self._is_processing = True
                self.schedule_message(1, self._process_queue)

    def _process_queue(self):
        if self._task_queue.empty():
            self._is_processing = False
            return
        cmd_type, params = self._task_queue.get()
        try:
            # FIX FOCUS : Toujours convertir l'index en objet Track pour éviter l'erreur C++
            t_idx = params.get("track_index")
            if t_idx is not None:
                all_tracks = list(self.song().tracks) + list(self.song().return_tracks) + [self.song().master_track]
                if t_idx < len(all_tracks):
                    target = all_tracks[t_idx]
                    if self.song().view.selected_track != target:
                        self.song().view.selected_track = target
                        self._task_queue.put((cmd_type, params))
                        self.schedule_message(2, self._process_queue)
                        return

            if cmd_type == "load_device": self._load_device_by_name(params)
            elif cmd_type == "load_sample": self._load_sample(params)
            elif cmd_type == "universal_accessor": self._universal_accessor(params)
            elif cmd_type == "add_midi_notes": self._add_midi_notes(params)
            elif cmd_type == "set_device_param": self._set_device_param_by_name(params)
            self.log_message("(AbletonMCP) Done: " + str(cmd_type))
        except Exception as e: self.log_message("(AbletonMCP) Error: " + str(e))
        self.schedule_message(5, self._process_queue)

    def _universal_accessor(self, params):
        action, path_str, value = params.get("action"), params.get("path", ""), params.get("value")
        
        # SÉCURITÉ C++ SIGNATURE : Correction immédiate du chemin si c'est un focus de piste
        if "selected_track" in path_str and action == "set":
            try:
                idx = int(value)
                self.song().view.selected_track = self.song().tracks[idx]
                return
            except: pass

        obj_data = self._navigate_and_execute(path_str)
        if obj_data:
            obj, attr = obj_data
            if action == "set":
                val = float(value) if hasattr(obj, "min") else value
                setattr(obj, attr, val)
            elif action == "call":
                getattr(obj, attr)(value) if value is not None else getattr(obj, attr)()

    def _navigate_and_execute(self, path_str):
        path_str = path_str.replace("live_set", "song").replace(" ", ".")
        path_str = re.sub(r'([a-zA-Z_]+)\.([\d]+)', r'\1[\2]', path_str)
        obj = self.song() if path_str.startswith("song") else self
        path_str = path_str.replace("song.", "").replace("song", "").strip(".")
        parts = [p for p in path_str.split(".") if p]
        curr = obj
        for part in parts[:-1]:
            try:
                if "[" in part:
                    name, key = part.split("[")[0], part.split("[")[1].replace("]", "").strip('"')
                    coll = getattr(curr, name)
                    curr = coll[int(key)] if key.isdigit() else next((x for x in coll if key.lower() in x.name.lower()), coll[0])
                else: curr = getattr(curr, part)
            except: return None
        return (curr, parts[-1])

    def _load_device_by_name(self, params):
        name = str(params.get("device_name", "")).lower().strip()
        browser = Live.Application.get_application().browser
        
        # PRIORITÉ : Effets audio si on est sur une piste audio ou si le nom n'indique pas un instrument
        is_kit = "kit" in name or "drum" in name
        cats = [browser.audio_effects, browser.instruments, browser.drums, browser.packs]
        if is_kit: cats = [browser.drums, browser.packs, browser.instruments]

        def find_r(node, target):
            if hasattr(node, 'is_loadable') and node.is_loadable:
                n_name = node.name.lower()
                if n_name.endswith(('.wav', '.aif', '.mp3')): return None
                if target == n_name: return node # Match exact
                if target in n_name: return node # Match partiel
            if hasattr(node, 'children'):
                for child in node.children:
                    res = find_r(child, target)
                    if res: return res
            return None

        found = None
        for cat in cats:
            found = find_r(cat, name)
            if found: break
        if found: 
            browser.load_item(found)
            self.log_message("(AbletonMCP) Loaded Device: " + str(found.name))

    def _load_sample(self, params):
        name = str(params.get("sample_name", "")).lower().strip()
        browser = Live.Application.get_application().browser
        roots = [browser.samples, browser.user_library] + (list(browser.user_folders) if hasattr(browser, 'user_folders') else [])
        def find_s(node, target):
            if hasattr(node, 'is_loadable') and node.is_loadable:
                if target in node.name.lower(): return node
            if hasattr(node, 'children'):
                for child in node.children:
                    res = find_s(child, target)
                    if res: return res
            return None
        found = None
        for r in roots:
            found = find_s(r, name)
            if found: break
        if found:
            self.log_message("(AbletonMCP) FOUND SAMPLE: " + str(found.name))
            browser.load_item(found)

    def _add_midi_notes(self, params):
        clip = self.song().tracks[params.get("track_index")].clip_slots[params.get("clip_index")].clip
        notes = [Live.Clip.MidiNoteSpecification(pitch=int(n['pitch']), start_time=float(n['start']), duration=float(n['dur']), velocity=int(n['vel'])) for n in params.get("notes", [])]
        clip.add_new_notes(tuple(notes))

    def _set_device_param_by_name(self, params):
        d_name, p_name, val = params.get("device_name").lower(), params.get("param_name").lower(), float(params.get("value"))
        for dev in self.song().view.selected_track.devices:
            if d_name in dev.name.lower():
                for p in dev.parameters:
                    if p_name in p.name.lower():
                        p.value = max(p.min, min(p.max, val))
                        return True