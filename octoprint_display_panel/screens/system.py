"""System-centric Micro Panel screen.
"""
import time
import psutil
import shutil
import socket

from . import base


class SystemInfoScreen(base.MicroPanelScreenBase):
    """The common system information screen - IP, memory, etc.
    """
    def __init__(self, width, height, shutdown_command):
        super().__init__(width, height)
        self.shutdown_command = shutdown_command
        self.stats = {}
        self.last_stats = 0
        self.get_stats()
        
    def draw(self):
        self.get_stats()
        load = self.stats['load']
        mem = self.stats['memory']
        disk = self.stats['disk']
        disk_percent = (disk.used / disk.total) * 100.0
        MB = 1048576
        GB = MB * 1024
        
        c = self.get_canvas()
        c.text_centered(0, self.stats['ip'])
        c.text((0, 9), f'L: {load[0]:.2f}, {load[1]:.2f}, {load[2]:.2f}')
        c.text((0, 18), (f'M: {mem.used//MB}/{mem.total//MB} MB'
                         f' {mem.percent}%'))
        c.text((0, 27), (f'D: {disk.used//GB}/{disk.total//GB} GB'
                         f' {disk_percent:.1f}%'))
        return c.image

    def handle_button(self, label):
        if label == 'cancel_long':
            self.set_subscreen(
                ShutdownScreen(self.width, self.height, self.shutdown_command))
            return {'DRAW'}
        return {}

    def get_stats(self):
        # Only get stats every 5 seconds
        if (time.time() - self.last_stats) < 5:
            return
        self.last_stats = time.time()
        
        try:
            # This technique gives a reliable reading on the system's
            # externally visible IP address, but requires that
            # external connectivity is online.
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            self.stats['ip'] = s.getsockname()[0]
            s.close()
        except OSError:
            self.stats['ip'] = 'IP unavailable'
        
        try:
            self.stats['load'] = psutil.getloadavg()
        except OSError:
            self.stats['load'] = (-1, 0, 0)
        self.stats['memory'] = psutil.virtual_memory()
        self.stats['disk'] = shutil.disk_usage('/')
        
    
class ShutdownScreen(base.MicroPanelScreenBase):
    """The shutdown screen.

    This screen is shown by the MicroPanelScreenTop when the cancel
    button is pressed for 5+ seconds when showing the system info.
    """
    def __init__(self, width, height, shutdown_command):
        super().__init__(width, height)
        self.shutdown_message = "Shutting down"
        self.message_y = 11 # ((64-9)/2 - 16 --> 11
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

    def handle_button(self, label):
        return {'IGNORE'}
