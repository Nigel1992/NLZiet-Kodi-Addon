import xbmc


def run():
    """Minimal service wrapper."""
    monitor = xbmc.Monitor()
    while not monitor.waitForAbort(1):
        pass


if __name__ == '__main__':
    run()
