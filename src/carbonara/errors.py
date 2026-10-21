"""The kinds of failure a run itself can raise, and the signal that stops one. Imports
nothing."""


class ReadinessError(Exception):
    """Something the run needed was missing, found before the first write."""


class RuntimeFailure(Exception):
    """The run stopped partway, after the first write had already happened."""


class Stopped(Exception):
    """A signal asked the run to stop, and carries that signal's number."""

    def __init__(self, signum):
        """Keep the signal number, so the exit code can follow the shell's rule."""
        super().__init__(signum)
        self.signum = signum
