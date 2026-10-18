"""A small stand-in for the console (contract C8): plug-in page tests use it to call a handler without the full shell."""
import tempfile

from web_console.console_api import Console


class ConsoleStub:
    """Holds a real Console on a temp folder and exposes only what a page handler may use: cos, lock, run_story."""

    def __init__(self):
        self._dir = tempfile.TemporaryDirectory()
        self._console = Console(self._dir.name, seed_brain=False)  # page tests seed their own sample brain
        self.cos = self._console.cos
        self.lock = self._console.lock

    def run_story(self, run_id):
        return self._console.run_detail(run_id)

    def close(self):
        self._console.close()
        self._dir.cleanup()
