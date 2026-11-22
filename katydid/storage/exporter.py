import re
from pathlib import Path

from katydid.model.collection import Collection
from katydid.model.entry import Entry

# make windows happy for file names
def _safe_name(text) -> str:
    text = re.sub(r'[<>:"/\\|?*]', "_", text)
    text = text.strip(" .")

    if text == "":
        return "Untitled"
    return text

# make sure duplicates are aptly labeled
def _unique_path(path: Path, has_suffix: bool = True) -> Path:
    n = 1
    orig_stem = path.stem
    orig_name = path.name
    while path.exists():
        n += 1
        if not has_suffix:
            path = path.with_name(f"{orig_name} ({n})")
        else:
            path = path.with_name(f"{orig_stem} ({n}){path.suffix}")
    return path

# create a markdown file with an entry's metadata
# format is "# [title]", blank line, italicized metadata line (with tags and modified date), blank line, entry body
def _entry_text(entry: Entry, collection: Collection) -> str:
    text = f"# {entry.title}\n\n*"
    all_tags = collection.available_tags()
    names = [all_tags[tag_id].name for tag_id in entry.tag_ids if tag_id in all_tags]
    parts = []
    if names:
        parts.append(", ".join(sorted(names)))
    parts.append(entry.modified.strftime("%Y-%m-%d"))
    meta_line = " - ".join(parts)
    text += f"{meta_line}*\n\n{entry.body}"
    return text

# export the collection
def export_collection(collection: Collection, destination) -> Path:
    destination = Path(destination)
    folder = _unique_path(destination / _safe_name(collection.title), has_suffix=False)
    folder.mkdir(parents=True)

    for entry in collection.entries.values():
        path = _unique_path(folder / f"{_safe_name(entry.title)}.md")
        path.write_text(_entry_text(entry, collection), encoding="utf-8")

    return folder
