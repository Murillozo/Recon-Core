from runner.scheduler import module_scripts


def test_module_scripts_follow_profile(tmp_path):
    root = tmp_path
    modules_dir = root / "modules"
    profiles_dir = root / "config" / "profiles"
    modules_dir.mkdir(parents=True)
    profiles_dir.mkdir(parents=True)

    for name in ["01_dns.sh", "02_subdomains.sh", "99_report.sh"]:
        (modules_dir / name).write_text("#!/usr/bin/env bash\n", encoding="utf-8")

    profile_file = profiles_dir / "balanced.yml"
    profile_file.write_text(
        """
name: balanced
modules:
  - 01_dns.sh
  - 02_subdomains.sh
""",
        encoding="utf-8",
    )

    scripts = module_scripts(root, profile_file)
    names = [s.name for s in scripts]
    assert names == ["01_dns.sh", "02_subdomains.sh", "99_report.sh"]
