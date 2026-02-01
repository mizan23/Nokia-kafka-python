def map_severity(sev, specific_problem):
    # alarm-change CLEAR payload
    if isinstance(sev, dict):
        if sev.get("new-value") == "cleared":
            return "CLEAR"

    if isinstance(specific_problem, str) and specific_problem.startswith("SEC_"):
        return "INFO"

    if isinstance(sev, dict):
        sev = sev.get("value") or sev.get("name") or sev.get("severity")

    if not isinstance(sev, str):
        return "UNKNOWN"

    sev = sev.strip().lower()

    return {
        "info": "INFO",
        "informational": "INFO",
        "indeterminate": "INFO",
        "condition": "INFO",
        "clear": "CLEAR",
        "warning": "WARNING",
        "minor": "MINOR",
        "major": "MAJOR",
        "critical": "CRITICAL",
    }.get(sev, "UNKNOWN")
