#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
This part of the code exposes functions to interface with the eink display
"""

import display.epd13in3E as eink
from PIL import Image
import logging


class DisplayHelper:

    def __init__(self, width, height):
        # Initialise the display
        self.logger = logging.getLogger('maginkcal')
        self.screenwidth = width
        self.screenheight = height
        self.epd = eink.EPD()
        self.epd.Init()

    def update(self, rgb_image):
        """
        Updates the display with a full-color image (PIL.Image).
        The image will be quantized to the 7-color palette.
        """

        # self.epd.clear()
        buf = self.epd.getbuffer(rgb_image)
        self.epd.display(buf)
        self.logger.info('E-Ink display update complete.')

    def calibrate(self, cycles=1):
        """
        Cycles through solid colors to prevent ghosting.
        """
        colors = [
            (255, 255, 255),  # White
            (0, 0, 0),        # Black
            (255, 255, 0),    # Yellow
            (255, 0, 0),      # Red
            (0, 0, 255),      # Blue
            (0, 255, 0),      # Green
        ]
        for _ in range(cycles):
            for color in colors:
                image = Image.new("RGB", (self.screenwidth, self.screenheight), color)
                buf = self.epd.getbuffer(image)
                self.epd.display(buf)
        self.logger.info('E-Ink display calibration complete.')

    def sleep(self):
        """
        Puts the display into deep sleep.
        """
        self.epd.sleep()
        self.logger.info('E-Ink display entered deep sleep.')

