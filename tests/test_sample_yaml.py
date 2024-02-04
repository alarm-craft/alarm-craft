from alarm_craft import config_loader


def test_sample_yaml():
    """Tests if sample yaml complies the config schema"""
    config_loader.load("config-min-sample.yaml")
    config_loader.load("config-sample.yaml")
