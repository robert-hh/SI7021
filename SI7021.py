# The MIT License (MIT)
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
#
# The calculation of dew_point and humid_ambient is taken from the Pycom
# SI7006-A20 library. Thanks to the Author. For these methods,
# their license applies. See:
# https://github.com/pycom/pycom-libraries/tree/master/license
# If that is inappropriate, just remove these two methods. They are not
# essential.
#
from time import sleep_ms
import math

# Default Address
SI7021_I2C_DEFAULT_ADDR = const(0x40)

# Commands
CMD_MEASURE_RELATIVE_HUMIDITY_HOLD_MASTER_MODE = const(0xE5)
CMD_MEASURE_RELATIVE_HUMIDITY = const(0xF5)
CMD_MEASURE_TEMPERATURE_HOLD_MASTER_MODE = const(0xE3)
CMD_MEASURE_TEMPERATURE = const(0xF3)
CMD_TEMPERATURE_FROM_PREV_RH_MEASUREMENT = const(0xE0)
CMD_RESET = const(0xFE)
CMD_WRITE_RH_T_USER_REGISTER_1 = const(0xE6)
CMD_READ_RH_T_USER_REGISTER_1 = const(0xE7)
CMD_WRITE_HEATER_CONTROL_REGISTER = const(0x51)
CMD_READ_HEATER_CONTROL_REGISTER = const(0x11)
CMD_READ_SERIAL_1 = const(0xfa)
CMD_READ_SERIAL_2 = const(0x0f)
CMD_READ_SERIAL_3 = const(0xfc)
CMD_READ_SERIAL_4 = const(0xc9)
CMD_READ_REVISION_1 = const(0x84)
CMD_READ_REVISION_2 = const(0xb8)
I2C_POLLING_TIME = const(5)


class SI7021(object):
    def __init__(self, i2c=None):
        self.i2c = i2c
        self.addr = SI7021_I2C_DEFAULT_ADDR
        self.cbuffer = bytearray(2)
        self.temp = bytearray(3)
        self.rh = bytearray(3)
        self._resolution = 0
        self.resRH = (0xfff8, 0xff80, 0xffe0, 0xfff0)
        self.resTemp = (0xfffe, 0xfff8, 0xfffc, 0xfff0)
        self.crctab1 = (b"\x00\x31\x62\x53\xc4\xf5\xa6\x97"
                        b"\xb9\x88\xdb\xea\x7d\x4c\x1f\x2e")
        self.crctab2 = (b"\x00\x43\x86\xc5\x3d\x7e\xbb\xf8"
                        b"\x7a\x39\xfc\xbf\x47\x04\xc1\x82")

    def _write_command(self, command_byte, command_ext=None):
        """
        Write a single or two-byte command
        """
        if command_ext is not None:
            self.cbuffer[0] = command_byte
            self.cbuffer[1] = command_ext
            self.i2c.writeto(self.addr, self.cbuffer)
        else:
            self.i2c.writeto(self.addr, bytes([command_byte]))

    def _crc8(self, data, crc=0):
        """
        Calculate the CRC8, x^8 + x^5 + x^4 + 1
        """
        for byte in data:
            crc ^= byte
            crc = (self.crctab1[crc & 0x0f] ^
                   self.crctab2[(crc >> 4) & 0x0f])
        return crc

    def reset(self):
        """
        Reset the device
        """
        self._write_command(CMD_RESET)
        sleep_ms(100)

    def set_resolution(self, index):
        """
        Set the resolution, index according to the data sheet
        """
        self._resolution = index
        self._write_command(CMD_WRITE_RH_T_USER_REGISTER_1,
                            (index & 2) << 6 | (index & 1))

    def temperature(self, new=True):
        """
        Read the temperature
        """
        if new:
            self._write_command(CMD_MEASURE_TEMPERATURE)
            sleep_ms(I2C_POLLING_TIME)
            for _ in range(20):
                try:
                    self.i2c.readfrom_into(self.addr, self.temp)
                    if self._crc8(self.temp) != 0:
                        raise OSError('SI7021 CRC error')
                    break
                except OSError:
                    sleep_ms(I2C_POLLING_TIME)
            else:
                raise OSError('SI7021 timeout')
        else:
            self._write_command(CMD_TEMPERATURE_FROM_PREV_RH_MEASUREMENT)
            self.i2c.readfrom_into(self.addr, self.temp)
        temp2 = (((self.temp[0] << 8) | self.temp[1]) &
                 self.resTemp[self._resolution])
        return (175.72 * temp2 / 65536.0) - 46.85

    def humidity(self):
        self._write_command(CMD_MEASURE_RELATIVE_HUMIDITY)
        for _ in range(20):
            sleep_ms(I2C_POLLING_TIME)
            try:
                self.i2c.readfrom_into(self.addr, self.rh)
                break
            except OSError:
                pass
        else:
            raise OSError('SI7021 timeout')
        if self._crc8(self.rh) == 0:
            rh2 = (((self.rh[0] << 8) | self.rh[1]) &
                   self.resRH[self._resolution])
            rh2 = (125.0 * rh2 / 65536.0) - 6.0
            return max(0.0, min(100.0, rh2))
        else:
            raise OSError('SI7021 CRC error')

    def dew_point(self):
        """
        Compute the dew point temperature for the current Temperature
        and Humidity measured pair
        """
        temp = self.temperature()
        humid = self.humidity()
        h = ((math.log(humid, 10) - 2) / 0.4343 +
             (17.62 * temp) / (243.12 + temp))
        dew_p = 243.12 * h / (17.62 - h)
        return dew_p

    def humid_ambient(self, t_ambient, dew_p=None):
        """
        Returns the relative humidity compensated for the current
        ambient temperature
        """
        if dew_p is None:
            dew_p = self.dew_point()
        h = 17.62 * dew_p / (243.12 + dew_p)
        h_ambient = math.pow(10, (h - (17.62 * t_ambient) /
                             (243.12 + t_ambient)) * 0.4343 + 2)
        return max(0.0, min(100.0, h_ambient))

    @property
    def serialnumber(self):
        self._write_command(CMD_READ_SERIAL_1, CMD_READ_SERIAL_2)
        sna = self.i2c.readfrom(self.addr, 8)
        self._write_command(CMD_READ_SERIAL_3, CMD_READ_SERIAL_4)
        snb = self.i2c.readfrom(self.addr, 6)
        serial = bytearray(8)
        for _ in range(4):
            serial[_] = sna[_ * 2]
        serial[4] = snb[0]
        serial[5] = snb[1]
        serial[6] = snb[3]
        serial[7] = snb[4]
        return serial

    @property
    def revision(self):
        self._write_command(CMD_READ_REVISION_1, CMD_READ_REVISION_2)
        return self.i2c.readfrom(self.addr, 1)
