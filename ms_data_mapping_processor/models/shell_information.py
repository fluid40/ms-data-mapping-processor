"""Module defining the ShellInformation class."""


class ShellInformation:
    """Class representing shell information for a model."""

    def __init__(self, id: str, id_short: str, display_name: str):
        """Initialize ShellInformation with given parameters.

        :param id: The unique identifier of the shell.
        :param id_short: The short identifier of the shell.
        :param display_name: The display name of the shell.
        """
        self.id = id
        self.id_short = id_short
        self.display_name = display_name
