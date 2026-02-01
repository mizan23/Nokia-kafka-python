"""
alarm_filters.py

Central place for alarm filtering policy.
Return True  -> DROP alarm
Return False -> KEEP alarm
"""

from datetime import datetime, timedelta


# =================================================
# Helpers
# =================================================
def _parse_time(ts):
    return datetime.fromisoformat(ts.replace("Z", "+00:00"))


def _extract_ops_span(name):
    """
    Extract OPS shelf/slot span.
    Example:
      Benapole/OPS-3-7-A3,OCH,RCV  -> OPS-3-7
      Jessore/OPS-3-3-SIG2,OCH    -> OPS-3-3
    """
    if not name:
        return None

    for part in name.split("/"):
        if part.startswith("OPS-"):
            return "-".join(part.split("-")[:3])
    return None


# =================================================
# POWER correlation
# =================================================
POWER_CHILD_ALARMS = {
    "Power Adjustment Required",
    "Power Adjustment Failure",
}

POWER_TIME_WINDOW = timedelta(minutes=10)


# =================================================
# LOS-OCH correlation
# =================================================
LOS_ROOT_ALARMS = {
    "Loss of signal - OCH",
}

LOS_CHILD_ALARMS = {
    "Transport Failure",
    "OPS Protection Loss of Redundancy",
}

LOS_TIME_WINDOW = timedelta(seconds=30)


# =================================================
# MAIN FILTER FUNCTION
# =================================================
def should_drop_alarm(
    *,
    alarm_name,
    specific_problem,
    probable_cause,
    ne_name,
    ne_id,
    source,
    object_type,
    severity,
    affected_object_name=None,
    first_detected=None,
    active_power_issues=None,
    active_los_alarms=None,
):
    """
    Decide whether an alarm should be dropped.
    Return True  -> DROP
    Return False -> KEEP
    """

    # -------------------------------
    # MASTER: Always KEEP Power Issue
    # -------------------------------
    if alarm_name == "Power Issue" and object_type == "PHYSICALCONNECTION":
        return False

    # =================================================
    # 🔥 POWER CHILD SUPPRESSION
    # =================================================
    if (
        alarm_name in POWER_CHILD_ALARMS
        and object_type == "TP"
        and active_power_issues
        and affected_object_name
        and first_detected
    ):
        child_time = _parse_time(first_detected)
        child_span = _extract_ops_span(affected_object_name)

        for pi in active_power_issues:
            pi_time = pi.get("first_detected")
            pi_obj = pi.get("affected_object_name")

            if not pi_time or not pi_obj:
                continue

            if abs(child_time - _parse_time(pi_time)) > POWER_TIME_WINDOW:
                continue

            if child_span and child_span == _extract_ops_span(pi_obj):
                return True   # DROP power child

    # =================================================
    # 🔥 LOS-OCH CORRELATION (ROOT / CHILD)
    # =================================================
    if (
        alarm_name in LOS_CHILD_ALARMS
        and active_los_alarms
        and first_detected
    ):
        child_time = _parse_time(first_detected)
        child_span = _extract_ops_span(affected_object_name)

        for los in active_los_alarms:
            if (
                los.get("alarm_name") not in LOS_ROOT_ALARMS
                or los.get("severity") != "CRITICAL"
                or not los.get("first_detected")
            ):
                continue

            los_time = _parse_time(los["first_detected"])

            # ⏱ Time correlation
            if abs(child_time - los_time) > LOS_TIME_WINDOW:
                continue

            los_span = _extract_ops_span(los.get("affected_object_name"))

            # 🎯 Correlation priority:
            # 1. OPS span match (best)
            # 2. Same NE (fallback, mainly for TRAIL)
            if (
                (child_span and los_span and child_span == los_span)
                or ne_name == los.get("ne_name")
            ):
                return True   # DROP LOS child

    # =================================================
    # EXISTING FILTER LOGIC (UNCHANGED)
    # =================================================
    if (
        (
            isinstance(object_type, str)
            and object_type.startswith("NE")
            and "CLI" in object_type
            and object_type.endswith(("Login", "Logout"))
        )

        or (
            isinstance(probable_cause, str)
            and probable_cause.startswith("NE")
            and probable_cause.endswith(("Login", "Logout"))
        )

        or (
            isinstance(alarm_name, str)
            and object_type.startswith("Indicates")
            and "Threshold" in object_type
            and object_type.endswith("detection")
        )

        or (
            isinstance(alarm_name, str)
            and object_type.startswith("Power")
            and "management" in object_type
            and object_type.endswith("suspended")
        )

        or alarm_name == "SR_RESTORED"
        or alarm_name == "SR_MANUAL_SWITCH"
        or alarm_name == "BASELINE"

        or alarm_name == "Adjacency Not Found"

        or specific_problem == "SEC_NA"
        or probable_cause in ("OPR", "PWRSUSP")

        or (
            isinstance(probable_cause, str)
            and probable_cause.startswith("T-")
            and probable_cause.endswith(("15-MIN", "1-DAY"))
        )

        or (
            isinstance(alarm_name, str)
            and alarm_name.startswith("Quality Threshold Crossed")
            and alarm_name.endswith(("15m", "24h"))
        )

        or probable_cause == "MAINT2-ALLOWED-REMOTE"

        or severity in ("WARNING", "INFO")
    ):
        return True

    return False
