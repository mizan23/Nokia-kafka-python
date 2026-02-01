import threading

class AlarmCache:
    def __init__(self):
        self._lock = threading.Lock()

        # Root alarms only
        self.active_power_issues = {}   # alarm_id -> alarm dict
        self.active_los_alarms = {}     # alarm_id -> alarm dict

    # ---------------------------
    # Loaders (startup only)
    # ---------------------------
    def load_power_issues(self, alarms):
        with self._lock:
            self.active_power_issues = {
                a["alarm_id"]: a for a in alarms
            }

    def load_los_alarms(self, alarms):
        with self._lock:
            self.active_los_alarms = {
                a["alarm_id"]: a for a in alarms
            }

    # ---------------------------
    # Readers (hot path)
    # ---------------------------
    def get_power_issues(self):
        with self._lock:
            return list(self.active_power_issues.values())

    def get_los_alarms(self):
        with self._lock:
            return list(self.active_los_alarms.values())

    # ---------------------------
    # Writers (lifecycle events)
    # ---------------------------
    def add_or_update(self, alarm):
        alarm_id = alarm["alarm_id"]
        name = alarm.get("alarm_name")
        severity = alarm.get("severity")

        with self._lock:
            if name == "Power Issue" and alarm.get("object_type") == "PHYSICALCONNECTION":
                self.active_power_issues[alarm_id] = alarm

            if name == "Loss of signal - OCH" and severity in ("CRITICAL", "MAJOR"):
                self.active_los_alarms[alarm_id] = alarm

    def remove(self, alarm_id):
        with self._lock:
            self.active_power_issues.pop(alarm_id, None)
            self.active_los_alarms.pop(alarm_id, None)
