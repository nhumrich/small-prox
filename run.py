import os
from smallprox import core

if __name__ == '__main__':
    if os.getenv('DEV_MODE', 'false') == 'true':
        import pydevd_pycharm
        pydevd_pycharm.settrace('host.docker.internal', port=9999, stdoutToServer=True,
                                stderrToServer=True)
    core.main()
