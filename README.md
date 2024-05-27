# py-raildriver

Python interface to Train Simulator Classic, this now expands on the original code by Piotr Kilczuk. The aim of this project is to ease communication with either `raildriver64.dll` or `raildriver.dll` provided with Train Simulator. The code in this version (v2+) requires Python 3.10+. The code is provided under the MIT license.

## Installation

The current release of `py-raildriver` is available on PyPi:

```sh
pip install py-raildriver
```

For development releases by [artemis-beta](https://github.com/artemis-beta/py-raildriver) you can install from this repository:

```sh
pip install git+https://github.com/artemis-beta/py-raildriver.git
```


## Documentation

Numpy style docstrings have been provided for all classes and methods.


## Example

Start your `Railworks.exe`/`Railworks64.exe`, get running, pause and try this in your Python console:

```sh
>>> import raildriver
>>> rd = raildriver.RailDriver()
>>> rd.set_rail_driver_connected(True)  # start data exchange
>>> assert 'SpeedometerMPH' in dict(rd.get_controller_list()).values(), 'SpeedometerMPH is not available on this loco'
>>> rd.get_current_controller_value('SpeedometerMPH')
50.004728991072624922
```

## Bugs & Contributing

Please use Github to report bugs and feature requests:
http://github.com/artemis-beta/py-raildriver

Code contributions are of course more than welcome. Please remember about unit tests or your code might not be accepted.
You can run the test suite with:::

    python setup.py test

Copyright 2025, Piotr Kilczuk
