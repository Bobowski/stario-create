from stario_create import data_dir
from stario_create.data import skill_names


def test_data_dir_holds_the_bundled_files():
    d = data_dir()
    for name in ("AGENTS.md", "AGENTS-api.md", "llms.txt"):
        assert (d / name).is_file()
    for skill in skill_names():
        assert (d / "skills" / skill / "SKILL.md").is_file()
