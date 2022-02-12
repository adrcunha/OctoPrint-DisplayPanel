
from board import SCL, SDA
import busio
import time
import adafruit_ssd1306
import RPi.GPIO as GPIO

import logging
logger = logging.getLogger("octoprint.plugins.display_panel.panels")

def bcm2board(bcm_pin):
    pinmap = [-1, -1, -1,  7, 29, 31, -1, -1, -1, -1, -1, 32,
              33, -1, -1, 36, 11, 12, 35, 38, 40, 15, 16, 18,
              22, 37, 13]
    if bcm_pin != -1:
        return pinmap[bcm_pin - 1]
    return -1


class MicroPanel:
    """Interface to the standard I2C and GPIO-driven Micro Panel.
    """
    width = 128
    height = 64
    
    def __init__(self, button_callback):
        self.button_event_callback = button_callback
        self.gpio_pinset = set()
        self.last_press = None
        
    def setup(self, settings):
        """Apply settings from OctoPrint's SettingsPlugin mixin to
        configure the panel.
        """
        self.i2c_address = int(settings.get(['i2c_address'], merged=True), 0)
        self.input_pinset = {
            settings.get_int([f'pin_{p}'], merged=True): p
            for p in ['cancel', 'mode', 'pause', 'play']
        }
        self.debounce_time = settings.get_int(['debounce'], merged=True)
    
        # set up display
        self.i2c = busio.I2C(SCL, SDA)
        self.disp = adafruit_ssd1306.SSD1306_I2C(
            self.width, self.height, self.i2c, addr=self.i2c_address)

        # set up GPIO mode
        current_mode = GPIO.getmode()
        if current_mode is None:
            # set GPIO to BCM numbering
            GPIO.setmode(GPIO.BCM)

        elif current_mode != GPIO.BCM:
            # remap to BOARD numbering
            GPIO.setmode(current_mode)
            self.input_pinset = {bcm2board(p): l
                                 for p, l in self.input_pinset.items()}
        GPIO.setwarnings(False)

        # set up pins
        for gpio_pin in self.input_pinset:
            if gpio_pin == -1:
                continue

            GPIO.setup(gpio_pin, GPIO.IN, GPIO.PUD_UP)
            GPIO.remove_event_detect(gpio_pin)
            GPIO.add_event_detect(gpio_pin, GPIO.FALLING,
                                  callback=self.handle_gpio_event,
                                  bouncetime=self.debounce_time)
            self.gpio_pinset.add(gpio_pin)

        # clean up any pins that may not be selected any more
        cleaned_pins = set()
        for gpio_pin in self.gpio_pinset.difference(self.input_pinset.keys()):
            try:
                GPIO.remove_event_detect(gpio_pin)
                GPIO.cleanup(gpio_pin)
            except:
                logger.exception(f'failed to clean up GPIO pin {gpio_pin}')
            else:
                cleaned_pins.add(gpio_pin)
        self.gpio_pinset.difference_update(cleaned_pins)

    def shutdown(self):
        """Called during plugin shutdown.
        """
        for gpio_pin in self.input_pinset:
            if gpio_pin == -1:
                continue
            GPIO.remove_event_detect(gpio_pin)
            GPIO.cleanup(gpio_pin)
            
    def fill(self, v):
        """Fill the screen with the specified color.
        """
        self.disp.fill(v)

    def image(self, img):
        """Set an image to be shown on screen.
        """
        self.disp.image(img)

    def show(self):
        """Show the currently set image on the screen.
        """
        self.disp.show()

    def poweroff(self):
        """Turn the display off.
        """
        self.disp.poweroff()

    def poweron(self):
        """Turn the display on.
        """
        self.disp.poweron()

    def handle_gpio_event(self, channel):
        """Called on a GPIO event, translate an input channel to a button label
        and invokes the button callback function with that label.
        """
        if channel not in self.input_pinset:
            return

        event_name = self.input_pinset[channel]
        press_time = time.time()
        unpress_time = press_time + 1

        # Debounce: ignore presses less than 0.5s apart
        if self.last_press:
            last_press = press_time - self.last_press
            if last_press < 0.5:
                # logger.info(f'button {event_name} pressed too soon ({last_press}s)')
                return

        # Wait until button is released
        while True:
            # "Released" means: during debounce_time, button wasn't pressed for 51%+ of the time.
            release_count = 0.0
            debounce_time = 100
            for _ in range(0, debounce_time):
              time.sleep(0.001)
              if GPIO.input(channel):
                release_count += 1.0
            debounce = release_count * 100 / debounce_time
            # logger.info(f'button {event_name}: {debounce:0.2f}% certain')
            if debounce > 51:
              unpress_time = time.time()
              break

        self.last_press = unpress_time
        pressed_time = unpress_time - press_time
        logger.info(f'button {event_name} pressed for {pressed_time}ss ({debounce:0.2f}% sure)')
        if pressed_time < 0.2:
            logger.info(f'ignoring noise for button {event_name}')
            return
        if pressed_time >= 5:
            event_name += '_long'

        self.button_event_callback(event_name)
