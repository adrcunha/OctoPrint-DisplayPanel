"""System shutdown Micro Panel screen.
"""

from . import base


class SystemShutdownScreen(base.MicroPanelScreenBase):
    """The shutdown screen.

    This screen is shown by the MicroPanelScreenTop when the cancel
    button is pressed for 5+ seconds when showing the system info.
    """
    def __init__(self, width, height, shutdown_command):
        super().__init__(width, height)
        self.shutdown_message = "Shutting down"
        self.message_y = int((height - 9) / 2)
        try:
            import sarge
            p = sarge.run(shutdown_command, async_=True)
        except Exception as e:
            self.shutdown_message = "** Error **\n{error}".format(error=e)
            self.message_y = 0

    def draw(self):
        c = self.get_canvas()
        c.text_centered(self.message_y, self.shutdown_message)
        return c.image
