def parse_affected_object(obj):
    if not obj:
        return {}

    parsed = {}
    for p in obj.split(":"):
        if p.startswith("shelf"):
            parsed["shelf"] = p
        elif p.startswith("slot"):
            parsed["slot"] = p
        elif p.startswith("port"):
            parsed["port"] = p

    return parsed
