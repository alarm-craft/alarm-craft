from pathlib import Path

from alarm_craft import config_loader


def test_sample_yaml():
    """Tests if sample yaml complies the config schema"""
    curr_dir = Path(__file__).parent

    config_loader.load(str(curr_dir.parent / "config-min-sample.yaml"))
    config_loader.load(str(curr_dir.parent / "config-sample.yaml"))
