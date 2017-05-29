import subprocess


def test_run(app_connection, composition):
    composition.run('run_test', 'true')


def test_run_timeout(app_connection, composition):
    try:
        composition.run('run_test', 'sleep', '5', timeout=1)
        assert False
    except subprocess.TimeoutExpired:
        pass  # Expected
