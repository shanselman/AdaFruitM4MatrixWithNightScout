# The MIT License (MIT)
#
# Copyright (c) 2019 Limor Fried for Adafruit Industries
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.
"""
`line`
================================================================================

Various common shapes for use with displayio - Line shape!


* Author(s): Melissa LeBlanc-Williams

Implementation Notes
--------------------

**Software and Dependencies:**

* Adafruit CircuitPython firmware for the supported boards:
  https://github.com/adafruit/circuitpython/releases

"""

from adafruit_display_shapes.polygon import Polygon

__version__ = "2.0.1"
__repo__ = "https://github.com/adafruit/Adafruit_CircuitPython_Display_Shapes.git"


class Line(Polygon):
    # pylint: disable=too-many-arguments,invalid-name, too-few-public-methods
    """A line.

    :param x0: The x-position of the first vertex.
    :param y0: The y-position of the first vertex.
    :param x1: The x-position of the second vertex.
    :param y1: The y-position of the second vertex.
    :param color: The color of the line.
    """

    def __init__(self, x0, y0, x1, y1, color):
        super().__init__([(x0, y0), (x1, y1)], outline=color)
