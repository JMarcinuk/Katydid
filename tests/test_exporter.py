import pytest

from katydid.model.collection import Collection
from katydid.storage.exporter import export_collection

class TestExporter:

    def test_files_appear(self, collection, tmp_path):
        # test that entries exported appear as separate .md files
        folder = export_collection(collection, tmp_path)
        entry_files = list(folder.glob("*.md"))

        assert len(entry_files) == len(collection.entries)

    def test_bad_titles_cleaned(self, tmp_path, default_tags, make_entry):
        # test that a title with a windows-forbidden character is cleaned before exporting
        collection = Collection(title="Test", description="test", default_tags=default_tags)
        collection.add_entry(make_entry(title="Test?"))

        folder = export_collection(collection, tmp_path)
        test_path = folder / "Test_.md"
        assert test_path.is_file()

    def test_no_overwrite(self, collection, tmp_path):
        # test that a duplicate export does not overwrite an old one, but rather makes a duplicate with a different name
        export_collection(collection, tmp_path)
        export_collection(collection, tmp_path)

        names = {folder.name for folder in tmp_path.iterdir() if folder.is_dir()}
        assert names == {collection.title, f"{collection.title} (2)"}