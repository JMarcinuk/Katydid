import json
import re
from pathlib import Path

# a path to the resources folder containing theme json and qss
RESOURCES = Path(__file__).parent.parent / "resources"
NON_COLOR_KEYS = {"id", "title"}

def load_themes() -> dict:
    return json.loads((RESOURCES / "themes.json").read_text(encoding="utf-8"))

def build_stylesheet(theme: dict) -> str:
    qss = (RESOURCES / "styles.qss").read_text(encoding="utf-8")

    for key, value in theme.items():
        if key in NON_COLOR_KEYS:
            continue
        qss = qss.replace("{" + key + "}", value)

    leftovers = re.findall(r"\{[a-z-]+\}", qss)
    if leftovers:
        missing = ", ".join(sorted(set(leftovers)))
        raise ValueError(f"Theme {theme.get('id')!r} is missing values for: {missing}")

    return qss

def apply_theme(app, theme_id) -> dict:
    themes = load_themes()
    if theme_id not in themes:
        raise KeyError

    app.setStyleSheet(build_stylesheet(themes[theme_id]))
    return themes[theme_id]