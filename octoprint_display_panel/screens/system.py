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
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.stats = {}
        self.last_stats = 0
        self.get_stats()

    def resource_usage(self, prefix, used_bytes, total_bytes):
        MB = 1048576
        GB = MB * 1024

        percent = (used_bytes / total_bytes) * 100.0
        unit = GB
        unit_str = 'GB'
        if total_bytes < GB:
                unit = MB
                unit_str = 'MB'
                if total_bytes < MB:
                        unit_str = 'kB'
                        unit = 1024
                        if total_bytes < 1024:
                                unit_str = 'bytes'
                                unit = 1
        total = total_bytes // unit
        used = used_bytes // unit
        return f'{prefix}: {used}/{total} {unit_str} {percent:.1f}%'

    def draw(self):
        self.get_stats()
        load = self.stats['load']
        mem = self.stats['memory']
        disk = self.stats['disk']
        data = self.stats['data']

        c = self.get_canvas()
        c.text_centered(0, self.stats['ip'])
        c.text((0, 9), f'CPU: {load[0]:.2f}, {load[1]:.2f}, {load[2]:.2f}')
        c.text((0, 18), self.resource_usage('Mem', mem.used, mem.total))
        c.text((0, 27), self.resource_usage('Dsk', disk.used, disk.total))
        c.text((0, 36), self.resource_usage('SD ', data.used, data.total))
        return c.image

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
        # TODO(adrcunha): Make this configurable.
        self.stats['data'] = shutil.disk_usage('/media/data')
