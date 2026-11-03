from app.lines import motor

LINES = {"motor": motor}


def get_line(name):
    """Return the line module for the given name."""
    if name not in LINES:
        raise ValueError(f"Unknown line: {name}")
    return LINES[name]