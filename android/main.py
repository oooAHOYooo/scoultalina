from kivy.app import App
from kivy.lang import Builder
from kivy.uix.boxlayout import BoxLayout
from kivy.properties import StringProperty, BooleanProperty
from kivy.clock import Clock
from kivy.uix.popup import Popup
from kivy.uix.label import Label
from kivy.utils import platform
from kivy.uix.textinput import TextInput
from kivy.uix.gridlayout import GridLayout
from kivy.uix.button import Button as KivyButton
import os
import json
from datetime import datetime
from urllib import request as urllib_request
try:
    from plyer import notification as plyer_notification
    from plyer import gps as plyer_gps
except Exception:
    plyer_notification = None
    plyer_gps = None
try:
    # Available only on Android
    from android.permissions import request_permissions, Permission, check_permission
except Exception:
    request_permissions = None
    Permission = None
    check_permission = None


KV = """
<RootLayout>:
    orientation: 'vertical'
    padding: dp(16)
    spacing: dp(12)

    Label:
        id: status_label
        text: app.status_text
        halign: 'center'
        valign: 'middle'
        text_size: self.size

    BoxLayout:
        size_hint_y: None
        height: dp(48)
        spacing: dp(12)
        Button:
            text: 'Start'
            on_release: app.start_collection()
        Button:
            text: 'Stop'
            on_release: app.stop_collection()

    Button:
        size_hint_y: None
        height: dp(48)
        text: 'About'
        on_release: app.show_about()

    BoxLayout:
        size_hint_y: None
        height: dp(48)
        spacing: dp(12)
        Button:
            text: 'Link Device'
            on_release: app.show_link_dialog()
"""


class RootLayout(BoxLayout):
    pass


class ScoutAlinaApp(App):
    status_text = StringProperty("Ready to collect")
    is_collecting = BooleanProperty(False)

    def build(self):
        Builder.load_string(KV)
        self.collected_points = []
        self._tick_ev = None
        self._gps_active = False
        root = RootLayout()
        # Attempt to upload any pending files on startup
        Clock.schedule_once(lambda *_: self._retry_pending_uploads(), 0)
        return root

    def start_collection(self):
        if self.is_collecting:
            return
        self.is_collecting = True
        self.status_text = "Collecting…"
        if self._start_gps():
            self.status_text = "Collecting… (GPS active)"
        else:
            # Fallback to simulated timestamps if GPS not available (e.g., desktop)
            self._tick_ev = Clock.schedule_interval(self._tick_simulated, 1.0)
            self.status_text = "Collecting… (simulated)"

    def stop_collection(self):
        if not self.is_collecting:
            return
        self.is_collecting = False
        if self._tick_ev is not None:
            self._tick_ev.cancel()
            self._tick_ev = None
        if self._gps_active and plyer_gps:
            try:
                plyer_gps.stop()
            except Exception:
                pass
            self._gps_active = False
        saved_path = self._save_collection()
        self.status_text = f"Saved {len(self.collected_points)} samples to {os.path.basename(saved_path)}"
        if plyer_notification:
            try:
                plyer_notification.notify(title="ScoutAlina", message="Collection saved")
            except Exception:
                pass
        # Attempt auto-upload in the background (best-effort)
        Clock.schedule_once(lambda *_: self._try_upload(saved_path), 0)
        # Reset buffer
        self.collected_points = []

    def _tick_simulated(self, *_):
        # Record a simple timestamped sample when GPS is unavailable
        self.collected_points.append({
            "timestamp": datetime.utcnow().isoformat() + "Z"
        })

    def _start_gps(self) -> bool:
        if not plyer_gps:
            return False
        # Request runtime location permissions on Android
        if platform == "android" and request_permissions and Permission and check_permission:
            wanted = [Permission.ACCESS_FINE_LOCATION, Permission.ACCESS_COARSE_LOCATION]
            try:
                missing = [p for p in wanted if not check_permission(p)]
            except Exception:
                missing = wanted
            if missing:
                try:
                    request_permissions(missing)
                except Exception:
                    pass
        try:
            plyer_gps.configure(on_location=self._on_gps_location, on_status=self._on_gps_status)
            # minTime in ms, minDistance in meters
            plyer_gps.start(minTime=1000, minDistance=0)
            self._gps_active = True
            return True
        except Exception:
            self._gps_active = False
            return False

    def _on_gps_location(self, **kwargs):
        # kwargs vary by provider; normalize common fields
        ts = datetime.utcnow().isoformat() + "Z"
        lat = kwargs.get("lat") or kwargs.get("latitude")
        lon = kwargs.get("lon") or kwargs.get("longitude")
        if lat is None or lon is None:
            # Ignore invalid fix
            return
        point = {
            "timestamp": ts,
            "lat": float(lat),
            "lon": float(lon),
        }
        if "speed" in kwargs and kwargs["speed"] is not None:
            try:
                point["speed"] = float(kwargs["speed"])  # m/s
            except Exception:
                pass
        if "accuracy" in kwargs and kwargs["accuracy"] is not None:
            try:
                point["accuracy"] = float(kwargs["accuracy"])  # meters
            except Exception:
                pass
        self.collected_points.append(point)

    def _on_gps_status(self, status_type, status):
        # Update label with brief GPS status
        self.status_text = f"Collecting… (GPS: {status})"

    def _routes_dir(self):
        d = os.path.join(self.user_data_dir, "routes")
        os.makedirs(d, exist_ok=True)
        return d

    def _save_collection(self):
        payload = {
            "recorded_date": datetime.utcnow().date().isoformat(),
            "points": list(self.collected_points),
        }
        fname = f"route_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"
        fpath = os.path.join(self._routes_dir(), fname)
        with open(fpath, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
        return fpath

    def show_about(self):
        content = Label(
            text="ScoutAlina\nProperty Discovery Companion\nVersion 0.1.0\n\n© 2025 ScoutAlina",
            halign="center",
            valign="middle",
        )
        content.text_size = (400, None)
        popup = Popup(title="About ScoutAlina", content=content, size_hint=(0.85, 0.6))
        popup.open()

    # --- Upload helpers ---
    def _config_path(self):
        return os.path.join(self.user_data_dir, "config.json")

    def _load_config(self):
        cfg_path = self._config_path()
        if not os.path.exists(cfg_path):
            return {}
        try:
            with open(cfg_path, "r", encoding="utf-8") as f:
                return json.load(f) or {}
        except Exception:
            return {}

    def _try_upload(self, route_path: str):
        cfg = self._load_config()
        base_url = (cfg.get("server_base_url") or "").rstrip("/")
        api_key = cfg.get("api_key")
        if not base_url or not api_key:
            return  # Not configured
        try:
            with open(route_path, "r", encoding="utf-8") as f:
                payload = json.load(f)
            data = json.dumps(payload).encode("utf-8")
            req = urllib_request.Request(
                url=f"{base_url}/api/upload_route",
                data=data,
                headers={
                    "Content-Type": "application/json",
                    "X-API-Key": api_key,
                },
                method="POST",
            )
            with urllib_request.urlopen(req) as resp:  # nosec B310 (demo-only)
                if 200 <= resp.status < 300:
                    self.status_text = "Upload complete"
        except Exception:
            # Best-effort; leave file on disk for later retry
            pass

    def _retry_pending_uploads(self):
        cfg = self._load_config()
        if not cfg.get("server_base_url") or not cfg.get("api_key"):
            return
        try:
            for name in sorted(os.listdir(self._routes_dir())):
                if not name.endswith('.json'):
                    continue
                path = os.path.join(self._routes_dir(), name)
                self._try_upload(path)
        except Exception:
            pass

    # --- Device link (code exchange) ---
    def show_link_dialog(self):
        layout = GridLayout(cols=2, padding=12, spacing=8)
        layout.add_widget(Label(text="Server URL"))
        url_input = TextInput(text=(self._load_config().get("server_base_url") or ""), multiline=False)
        layout.add_widget(url_input)

        layout.add_widget(Label(text="Link Code"))
        code_input = TextInput(text="", multiline=False)
        layout.add_widget(code_input)

        btns = BoxLayout(spacing=8, size_hint_y=None, height=48)
        ok_btn = KivyButton(text="Link")
        cancel_btn = KivyButton(text="Cancel")
        btns.add_widget(ok_btn)
        btns.add_widget(cancel_btn)

        container = BoxLayout(orientation="vertical", padding=8, spacing=8)
        container.add_widget(layout)
        container.add_widget(btns)

        popup = Popup(title="Link Device", content=container, size_hint=(0.9, 0.6))

        def _do_link(*_):
            base_url = (url_input.text or "").strip().rstrip("/")
            code = (code_input.text or "").strip().upper()
            if not base_url or not code:
                self.status_text = "Enter server URL and code"
                return
            try:
                payload = json.dumps({"code": code}).encode("utf-8")
                req = urllib_request.Request(
                    url=f"{base_url}/api/device_link/exchange",
                    data=payload,
                    headers={"Content-Type": "application/json"},
                    method="POST",
                )
                with urllib_request.urlopen(req) as resp:  # nosec B310
                    if 200 <= resp.status < 300:
                        resp_data = json.loads(resp.read().decode("utf-8"))
                        api_key = resp_data.get("api_key")
                        if api_key:
                            cfg = self._load_config()
                            cfg.update({"server_base_url": base_url, "api_key": api_key})
                            with open(self._config_path(), "w", encoding="utf-8") as f:
                                json.dump(cfg, f, ensure_ascii=False, indent=2)
                            self.status_text = "Device linked"
                            popup.dismiss()
                            return
                self.status_text = "Invalid code"
            except Exception:
                self.status_text = "Link failed"

        ok_btn.bind(on_release=_do_link)
        cancel_btn.bind(on_release=lambda *_: popup.dismiss())
        popup.open()


if __name__ == "__main__":
    ScoutAlinaApp().run()


