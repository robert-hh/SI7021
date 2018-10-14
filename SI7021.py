
from time import sleep_ms

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

class SI7021(object):
  def __init__(self, i2c=None):
    self.i2c = i2c
    self.addr = SI7021_I2C_DEFAULT_ADDR
    self.cbuffer = bytearray(2)
    self.temp = bytearray(3)
    self.rh = bytearray(3)
    self.resolution = 0
    self.resRH = (0xfff8, 0xff80, 0xffe0, 0xfff0)
    self.resTemp = (0xfffe, 0xfff8, 0xfffc, 0xfff0)

  def write_command(self, command_byte, command_ext=None):
    """
    Write a single or two-byte command
    """
    if command_ext is not None:
        self.cbuffer[0] = command_byte
        self.cbuffer[1] = command_ext
        self.i2c.writeto(self.addr, self.cbuffer)
    else:
        self.i2c.writeto(self.addr, command_byte)

  def reset(self):
    """
    Reset the device
    """
    self.write_command(CMD_RESET)
    sleep_ms(100)

  def setResolution(self, index):
    """
    Set the resolution, index according to the data sheet
    """
    self.resolution = index
    self.write_command(CMD_WRITE_RH_T_USER_REGISTER_1,
        (index & 2) << 6 | (index & 1))

  def readTemp(self, new=True):
    """
    Read the temperature
    """
    if new:
      self.write_command(CMD_MEASURE_TEMPERATURE)
    else:
      self.write_command(CMD_TEMPERATURE_FROM_PREV_RH_MEASUREMENT)
    for _ in  range (25):
      try:
        self.i2c.readfrom_into(self.addr, self.temp)
        break
      except OSError:
        sleep_ms(4)
    else:
        raise OSError('SI7021 timeout')
    temp2 = ((self.temp[0] << 8) | self.temp[1]) & self.resTemp[self.resolution]
    return (175.72 * temp2 / 65536.0) - 46.85

  def readRH(self):
    self.write_command(CMD_MEASURE_RELATIVE_HUMIDITY)
    for _ in  range (25):
      try:
        self.i2c.readfrom_into(self.addr, self.rh)
        break
      except OSError:
        sleep_ms(4)
    else:
        raise OSError('SI7021 timeout')
    rh2 = ((self.rh[0] << 8) | self.rh[1]) & self.resRH[self.resolution]
    rh2 = (125.0 * rh2 / 65536.0) - 6.0
    return max(0.0, min(100.0, rh2))

  def readSerial(self):
    self.write_command(CMD_READ_SERIAL_1, CMD_READ_SERIAL_2)
    sna = self.i2c.readfrom(self.addr, 8)
    self.write_command(CMD_READ_SERIAL_3, CMD_READ_SERIAL_4)
    snb = self.i2c.readfrom(self.addr, 6)
    serial = bytearray(8)
    for _ in range(4):
      serial[_] = sna[_ * 2]
    serial[4] = snb[0]
    serial[5] = snb[1]
    serial[6] = snb[3]
    serial[7] = snb[4]
    return serial

  def readRevision(self):
    self.write_command(CMD_READ_REVISION_1, CMD_READ_REVISION_2)
    return self.i2c.readfrom(self.addr, 1)

