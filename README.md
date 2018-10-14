# SI7021: Python class for the SI7021 Temperature and Relative Humidity sensor

This is a very short and simple class. It uses the I2C bus for the interface.

## Constructor

### si7021 = SI7021(i2c)

i2c is an I2C object which has to be created by the caller.

## Methods

### temp = si7021.readTemp(new = True)

Reads the temperature and returns a °C value. If the parameter new is set to
new, a new reading is performed. When set to False, the Value taken during
the previous readRH() call is returned.  
The function raises OSError if after 100ms not value is returned from the device.


### rh = si7021.readRH()

Reads the relative humidity. The range is 0-100.  
The function raises OSError if after 100ms not value is returned from the device.

### si7021.setResolution(index)

Sets the resolution for both temperature and relative humidity. Index in the
range of 0-3 select the setting from the table below. The returned results of
readTemp() and readRH() are truncated according to the resolution set.
The conversion time also depends on the resolution.

|Index|RH|Temp|
|:-:|:-:|:-:|
|0|12 bit|14 bit|
|1|8 bit|12 bit|
|2|10 bit|13 bit|
|3|11 bit|11 bit|

### serial = si7021.readSerial()

Return the 8 byte serial number as a byte array. The fifth byte contains the
the identification of the device. For the SI7021 it's 0x15.

### serial = si7021.readRevision()

Return the firmware revision as a single byte object.

### si7021.reset()

Resets the device. The resolution is set back to maximum.


## Example

```
# Example for Pycom device.
# Connections:
# xxPy | ADS7818
# -----|-------
# P9   |  SDA
# P10  |  SCL
#
from machine import I2C
from SI7021 import SI7021

i2c = I2C(0, I2C.MASTER)
si7021 = SI7021(i2c)

temp = si7021.readTemp()
rh = si7021.readRH()
```
