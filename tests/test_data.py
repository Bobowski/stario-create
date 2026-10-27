from pathlib import Path

from stario_create import data_dir
from stario_create.data import skill_names

ROOT = Path(__file__).resolve().parents[1]


def test_data_dir_holds_the_bundled_files():
    d = data_dir()
    for name in ("AGENTS.md", "AGENTS-api.md", "llms.txt"):
        assert (d / name).is_file()
    for skill in skill_names():
        assert (d / "skills" / skill / "SKILL.md").is_file()


def test_guide_readme_and_llms_name_every_skill():
    guide = (ROOT / "AGENTS.md").read_text()
    readme = (ROOT / "README.md").read_text()
    llms = (ROOT / "llms.txt").read_text()
    assert "four skills" not in readme
    assert "four skills" not in llms
    for skill in skill_names():
        assert f"`{skill}`" in guide
        assert f"`{skill}`" in readme
        assert f"[{skill}]" in llms
