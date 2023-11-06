"""
Started from MoonPhase sample by Phil 'PaintYourDragon' Burgess for Adafruit Industries.
MIT license, all text above must be included in any redistribution.
BDF fonts from the X.Org project
"""

# pylint: disable=import-error
import gc
#from lib2to3.pgen2.token import GREATEREQUAL
import time
import math
import json
import board
import busio
import displayio
from rtc import RTC
from adafruit_matrixportal.network import Network
from adafruit_matrixportal.matrix import Matrix
from adafruit_bitmap_font import bitmap_font
import adafruit_display_text.label
import adafruit_lis3dh

try:
    from secrets import secrets
except ImportError:
    print('WiFi secrets are kept in secrets.py, please add them there!')
    raise

# CONFIGURABLE SETTINGS ----------------------------------------------------
  
TWELVE_HOUR = True # If set, use 12-hour time vs 24-hour (e.g. 3:00 vs 15:00)
BITPLANES = 2      # Ideally 6, but can set lower if RAM is tight

RED = 0xFF0000
GREEN = 0x00FF00
YELLOW = 0xFFFF00

UPARROW = '\u2191'
DOWNARROW = '\u2193'
RIGHTARROW = '\u2192'
UPRIGHTARROW = '\u2197'
DOWNRIGHTARROW = '\u2198'
DOUBLEUPARROW = '\u21D1'
DOUBLEDOWNARROW = '\u21D3'

# SOME UTILITY FUNCTIONS AND CLASSES ---------------------------------------

def parse_time(timestring, is_dst=-1):
    """ Given a string of the format YYYY-MM-DDTHH:MM:SS.SS-HH:MM (and
        optionally a DST flag), convert to and return an equivalent
        time.struct_time (strptime() isn't available here). Calling function
        can use time.mktime() on result if epoch seconds is needed instead.
        Time string is assumed local time; UTC offset is ignored. If seconds
        value includes a decimal fraction it's ignored.
    """
    date_time = timestring.split('T')        # Separate into date and time
    year_month_day = date_time[0].split('-') # Separate time into Y/M/D
    hour_minute_second = date_time[1].split('+')[0].split('-')[0].split(':')
    return time.struct_time(int(year_month_day[0]),
                            int(year_month_day[1]),
                            int(year_month_day[2]),
                            int(hour_minute_second[0]),
                            int(hour_minute_second[1]),
                            int(hour_minute_second[2].split('.')[0]),
                            -1, -1, is_dst)


def update_time(timezone=None):
    """ Update system date/time from WorldTimeAPI public server;
        no account required. Pass in time zone string
        (http://worldtimeapi.org/api/timezone for list)
        or None to use IP geolocation. Returns current local time as a
        time.struct_time and UTC offset as string. This may throw an
        exception on fetch_data() - it is NOT CAUGHT HERE, should be
        handled in the calling code because different behaviors may be
        needed in different situations (e.g. reschedule for later).
    """
    if timezone: # Use timezone api
        time_url = 'http://worldtimeapi.org/api/timezone/' + timezone
    else: # Use IP geolocation
        time_url = 'http://worldtimeapi.org/api/ip'

    time_data = NETWORK.fetch_data(time_url,
                                   json_path=[['datetime'], ['dst'],
                                              ['utc_offset']])
    time_struct = parse_time(time_data[0], time_data[1])
    RTC().datetime = time_struct
    return time_struct, time_data[2]


def hh_mm(time_struct):
    """ Given a time.struct_time, return a string as H:MM or HH:MM, either
        12- or 24-hour style depending on global TWELVE_HOUR setting.
        This is ONLY for 'clock time,' NOT for countdown time, which is
        handled separately in the one spot where it's needed.
    """
    if TWELVE_HOUR:
        if time_struct.tm_hour > 12:
            hour_string = str(time_struct.tm_hour - 12) # 13-23 -> 1-11 (pm)
        elif time_struct.tm_hour > 0:
            hour_string = str(time_struct.tm_hour) # 1-12
        else:
            hour_string = '12' # 0 -> 12 (am)
    else:
        hour_string = '{0:0>2}'.format(time_struct.tm_hour)
    return hour_string + ':' + '{0:0>2}'.format(time_struct.tm_min)

# pylint: disable=too-few-public-methods
class SugarData():
    def __init__(self):
        url = (str(NIGHTSCOUT) + '/api/v1/entries.json?count=5&token=' + str(TOKEN))
        print('Fetching sugar data via', url)

        # pylint: disable=bare-except
        for _ in range(1): # Retries
            try:
                full_data = json.loads(NETWORK.fetch_data(url))
                self.sugarList = []
                for entry in full_data:
                    sugarDetails = {'sgv': entry['sgv'], 'date': entry['date'], 'direction': entry['direction']}
                    sugarDetails['sgv']   = entry['sgv']
                    sugarDetails['date']  = entry['date']
                    sugarDetails['direction'] = entry['direction']
                    sugarDetails['type']  = entry['type']
                    self.sugarList.append(sugarDetails)

                print("DUMP: " + self.sugarList)
                return # Success!
            except:
                # server error (maybe), try again after 15 seconds.
                time.sleep(15)

# ONE-TIME INITIALIZATION --------------------------------------------------

MATRIX = Matrix(bit_depth=BITPLANES)
DISPLAY = MATRIX.display
ACCEL = adafruit_lis3dh.LIS3DH_I2C(busio.I2C(board.SCL, board.SDA),
                                   address=0x19)
_ = ACCEL.acceleration # Dummy reading to blow out any startup residue
time.sleep(0.1)
# Rotate display depending on board orientation
DISPLAY.rotation = (int(((math.atan2(-ACCEL.acceleration.y,
                                     -ACCEL.acceleration.x) + math.pi) /
                         (math.pi * 2) + 0.875) * 4) % 4) * 90

LARGE_FONT = bitmap_font.load_font('/fonts/helvB12.bdf')
SMALL_FONT = bitmap_font.load_font('/fonts/helvR10.bdf')
SYMBOL_FONT = bitmap_font.load_font('/fonts/6x10.bdf')
LARGE_FONT.load_glyphs('0123456789:')
SMALL_FONT.load_glyphs('0123456789:/.%')
# include blood sugar specific glyphs
SYMBOL_FONT.load_glyphs('0123456789.\u2191\u2193\u2192\u2197\u2198\u21D1\u21D3')

# Display group is set up once, then we just shuffle items around later.
# Order of creation here determines their stacking order.
GROUP = displayio.Group(max_size=10)
# Element 0 is a stand-in item, later replaced with the moon phase bitmap
# pylint: disable=bare-except
#try:
    #FILENAME = 'moon/splash-' + str(DISPLAY.rotation) + '.bmp'
    #BITMAP = displayio.OnDiskBitmap(open(FILENAME, 'rb'))
    #TILE_GRID = displayio.TileGrid(BITMAP,
                                   #pixel_shader=displayio.ColorConverter(),)
    # GROUP.append(TILE_GRID)
#except:
GROUP.append(adafruit_display_text.label.Label(SYMBOL_FONT, color=GREEN,
                                                text='Loading...'))
GROUP[0].x = (DISPLAY.width - GROUP[0].bounding_box[2] + 1) // 2
GROUP[0].y = DISPLAY.height // 2 - 1

# Elements 1-4 are an outline around the moon percentage -- text labels
# offset by 1 pixel up/down/left/right. Initial position is off the matrix,
# updated on first refresh. Initial text value must be long enough for
# longest anticipated string later.
# for i in range(4):
#     GROUP.append(adafruit_display_text.label.Label(SMALL_FONT, color=0,
#                                                    text='99.9%', y=-99))
# # Element 5 is the moon percentage (on top of the outline labels)
# GROUP.append(adafruit_display_text.label.Label(SMALL_FONT, color=0xFFFF00,
#                                                text='99.9%', y=-99))
# # Element 6 is the current time
# GROUP.append(adafruit_display_text.label.Label(LARGE_FONT, color=0x808080,
#                                                text='12:00', y=-99))
# # Element 7 is the current date
# GROUP.append(adafruit_display_text.label.Label(SMALL_FONT, color=0x808080,
#                                                text='12/31', y=-99))
# # Element 8 is a symbol indicating next rise or set
# GROUP.append(adafruit_display_text.label.Label(SYMBOL_FONT, color=0x00FF00,
#                                                text='x', y=-99))
# # Element 9 is the time of (or time to) next rise/set event
# GROUP.append(adafruit_display_text.label.Label(SMALL_FONT, color=0x00FF00,
#                                                text='12:00', y=-99))
DISPLAY.show(GROUP)

NETWORK = Network(status_neopixel=board.NEOPIXEL, debug=True)
NETWORK.connect()

try:
    TIMEZONE = secrets['timezone'] # e.g. 'America/New_York'
except:
    TIMEZONE = None

try:
    TOKEN = secrets['token'] 
except:
    TOKEN = None 

try:
    NIGHTSCOUT = secrets['nightscout'] 
except:
    NIGHTSCOUT = None 

# pylint: disable=bare-except
try:
    DATETIME, UTC_OFFSET = update_time(TIMEZONE)
except:
    DATETIME, UTC_OFFSET = time.localtime(), '+00:00'
LAST_SYNC = time.mktime(DATETIME)

# MAIN LOOP ----------------------------------------------------------------
while True:
    gc.collect()
    NOW = time.time() # Current epoch time in seconds

    # Sync with time server every ~5 min
    if NOW - LAST_SYNC > 5 * 60:
        try:
            DATETIME, UTC_OFFSET = update_time(TIMEZONE)
            LAST_SYNC = time.mktime(DATETIME)
            continue # Time may have changed; refresh NOW value
        except:
            # try again in a minute
            LAST_SYNC += 1 * 60 

    SUGAR = SugarData()


    # if DISPLAY.rotation in (0, 180): # Horizontal 'landscape' orientation
    #     CENTER_X = 48      # Text along right
    #     MOON_Y = 0         # Moon at left
    #     TIME_Y = 6         # Time at top right
    #     EVENT_Y = 26       # Rise/set at bottom right
    # else:                  # Vertical 'portrait' orientation
    #     CENTER_X = 16      # Text down center
    #     if RISEN:
    #         MOON_Y = 0     # Moon at top
    #         EVENT_Y = 38   # Rise/set in middle
    #         TIME_Y = 49    # Time/date at bottom
    #     else:
    #         TIME_Y = 6     # Time/date at top
    #         EVENT_Y = 26   # Rise/set in middle
    #         MOON_Y = 32    # Moon at bottom

    # Update moon image (GROUP[0])
    #FILENAME = 'moon/moon' + '{0:0>2}'.format(FRAME) + '.bmp'
    #BITMAP = displayio.OnDiskBitmap(open(FILENAME, 'rb'))
    #TILE_GRID = displayio.TileGrid(BITMAP,
                                   #pixel_shader=displayio.ColorConverter(),)
    #TILE_GRID.x = 0
    #TILE_GRID.y = MOON_Y
    #GROUP[0] = TILE_GRID

    # Update percent value (5 labels: GROUP[1-4] for outline, [5] for text)
    # if PERCENT >= 99.95:
    #     STRING = '100%'
    # else:
    #     STRING = '{:.1f}'.format(PERCENT + 0.05) + '%'
    #print(NOW, "test", 'full')
    # Set element 5 first, use its size and position for setting others
    #GROUP[0].text = SUGAR[0].sugar_text
    #GROUP[0].color_index = GREEN



    TEXTCOLOR = GREEN

    CURRENTSUGAR = SUGAR.sugarList[0]["sgv"]

    if CURRENTSUGAR > 200:
        TEXTCOLOR = RED
    elif CURRENTSUGAR > 150:
        TEXTCOLOR = YELLOW
    elif CURRENTSUGAR < 60:
        TEXTCOLOR = RED

    CURRENTDIRECTION = SUGAR.sugarList[0]["direction"]

    if CURRENTDIRECTION == "Flat":
        TEXTDIRECTION = RIGHTARROW
    elif CURRENTDIRECTION == "FortyFiveUp":
        TEXTDIRECTION = UPRIGHTARROW
    elif CURRENTDIRECTION == "FortyFiveDown":
        TEXTDIRECTION = DOWNRIGHTARROW
    elif CURRENTDIRECTION == "SingleUp":
        TEXTDIRECTION = UPARROW
    elif CURRENTDIRECTION == "SingleDown":
        TEXTDIRECTION = DOWNARROW
    elif CURRENTDIRECTION == "DoubleUp":
        TEXTDIRECTION = DOUBLEUPARROW
    elif CURRENTDIRECTION == "DoubleDown":
        TEXTDIRECTION = DOUBLEDOWNARROW

    GROUP[0].color_index = TEXTCOLOR
    GROUP[0].text = str(SUGAR.sugarList[0]["sgv"]) + " " + TEXTDIRECTION
    GROUP[0].x = (DISPLAY.width - GROUP[0].bounding_box[2] + 1) // 2
    GROUP[0].y = DISPLAY.height // 2 - 1
    
    #GROUP[0].text = SUGAR[0].sugar_text
    #print(SUGAR[0].sgv)

    # GROUP[5].text = STRING
    # GROUP[5].x = 16 - GROUP[5].bounding_box[2] // 2
    # GROUP[5].y = MOON_Y + 16
    # for _ in range(1, 5):
    #     GROUP[_].text = GROUP[5].text
    # GROUP[1].x, GROUP[1].y = GROUP[5].x, GROUP[5].y - 1 # Up 1 pixel
    # GROUP[2].x, GROUP[2].y = GROUP[5].x - 1, GROUP[5].y # Left
    # GROUP[3].x, GROUP[3].y = GROUP[5].x + 1, GROUP[5].y # Right
    # GROUP[4].x, GROUP[4].y = GROUP[5].x, GROUP[5].y + 1 # Down

    DISPLAY.refresh() # Force full repaint (splash screen sometimes sticks)
    time.sleep(5)
