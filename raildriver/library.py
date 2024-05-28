"""
RailDriver
==========

The main interface for communicating with the RailDriver DLL on the Windows system
"""
import ctypes
import datetime
import collections
import pathlib
import typing
import winreg
import time
import pydantic

LocoInfo = collections.namedtuple("LocoInfo", ("provider", "product", "engine"))


class RailDriver:
    """The main API for communication with the RailDriver dynamic library file"""
    _restypes: dict[str, typing.Type] = {
        'GetControllerList': ctypes.c_char_p,
        'GetLocoName': ctypes.c_char_p,
        'GetControllerValue': ctypes.c_float,
    }

    @pydantic.validate_call
    def __init__(self, dll_location: pydantic.FilePath | None=None, x86: bool=False) -> None:
        """Initializes the raildriver.dll interface.

        Parameters
        ----------
        dll_location : str | None, optional
            Optionally pass the location of raildriver.dll if in some custom location.
            If not passed will try to guess the location by using the Windows Registry.
        x86 : bool, optional
            if dll to be found automatically use 32-bit version instead of 64-bit version 

        Raises
        ------
        EnvironmentError
            if the dll location cannot be deduced automatically
        """
        if not dll_location:
            steam_key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, 'Software\\Valve\\Steam')
            steam_path = winreg.QueryValueEx(steam_key, 'SteamPath')[0]
            railworks_path = pathlib.Path(steam_path).joinpath('steamapps', 'common', 'railworks', 'plugins')
            dll_location = railworks_path.joinpath(f"raildriver{'' if x86 else '64'}.dll")
            if not dll_location.is_file():
                raise EnvironmentError(f"Unable to automatically locate raildriver{'' if x86 else '64'}.dll")

        self._dll: ctypes.CDLL = ctypes.cdll.LoadLibrary(f"{dll_location}")
        for function_name, restype in self._restypes.items():
            getattr(self._dll, function_name).restype = restype

    def __repr__(self) -> str:
        return f"raildriver.RailDriver: {self._dll}"

    def get_controller_index(self, name):
        for idx, n in self.get_controller_list():
            if n == name:
                return idx
        raise ValueError('Controller index not found for {}'.format(name))

    def get_controller_list(self) -> typing.Iterable[tuple[int, str]]:
        """Returns an iterable of tuples containing (index, controller_name) pairs.

        Controller indexes start at 0.

        Example
        -------
        You may easily transform this to a {name: index} mapping by using:

        >>> controllers = {name: index for index, name in raildriver.get_controller_list()}

        Returns
        -------
        typing.Iterable[tuple[int, str]]
            enumeration of controls
        """

        ret_str: str = self._dll.GetControllerList().decode()
        if not ret_str:
            return []
        return enumerate(ret_str.split('::'))

    @pydantic.validate_call
    def get_controller_value(self, index_or_name: int | str, value_type: typing.Literal["current", "min", "max"]) -> float:
        """Returns current/min/max value of controller at given index or name.

        It is much more efficient to query using an integer index rather than string name.
        Name is fine for seldom updates but it's not advised to be used every second or so.
        See `get_controller_list` for an example how to cache a dictionary of {name: index} pairs.

        Parameters
        ----------
        index_or_name : int | str
            integer index or string name
        value_type : Literal['current', 'min', 'max']
            type of value to return

        Returns
        -------
        float

        """
        if not isinstance(index_or_name, int):
            index = self.get_controller_index(index_or_name)
        else:
            index = index_or_name
        value_type_int = ("current", "min", "max").index(value_type)
        return self._dll.GetControllerValue(index, value_type_int)

    def get_current_controller_value(self, index_or_name: int | str) -> float:
        """Syntactic sugar for get_controller_value(index_or_name, "current")

        Parameters
        ----------
        index_or_name : int | str
            either the index or name of the control

        Returns
        -------
        float
            the current value for this control
        """
        return self.get_controller_value(index_or_name, "current")
    
    @property
    def regulator(self) -> float:
        return self.get_current_controller_value("Regulator")
    
    @regulator.setter
    @pydantic.validate_call
    def regulator(self, value: typing.Annotated[float, pydantic.Field(ge=0, le=100)]) -> None:
        self.set_controller_value("Regulator", value / 100)

    @property
    def reverser(self) -> float:
        return self.get_current_controller_value("Reverser")
    
    @reverser.setter
    @pydantic.validate_call
    def reverser(self, value: typing.Annotated[float, pydantic.Field(ge=-100, le=100)]) -> None:
        self.set_controller_value("Reverser", value / 100)

    @property
    def train_brake(self) -> float:
        return self.get_current_controller_value("TrainBrakeControl")
    
    @train_brake.setter
    @pydantic.validate_call
    def train_brake(self, value: typing.Annotated[float, pydantic.Field(ge=0, le=100)]) -> None:
        self.set_controller_value("TrainBrakeControl", value / 100)

    @property
    def simple_throttle(self) -> float:
        return self.get_current_controller_value("SimpleThrottle")
    
    @simple_throttle.setter
    @pydantic.validate_call
    def simple_throttle(self, value: typing.Annotated[float, pydantic.Field(ge=0, le=100)]) -> None:
        self.set_controller_value("SimpleThrottle", value / 100)

    @property
    def virtual_brake(self) -> float:
        return self.get_current_controller_value("VirtualBrake")
    
    @virtual_brake.setter
    @pydantic.validate_call
    def virtual_brake(self, value: typing.Annotated[float, pydantic.Field(ge=0, le=100)]) -> None:
        self.set_controller_value("VirtualBrake", value / 100)

    @property
    def dynamic_brake(self) -> float:
        return self.get_current_controller_value("DynamicBrake")
    
    @dynamic_brake.setter
    @pydantic.validate_call
    def dynamic_brake(self, value: typing.Annotated[float, pydantic.Field(ge=0, le=100)]) -> None:
        self.set_controller_value("DynamicBrake", value / 100)

    def has_control(self, control: str) -> bool:
        """Check if the given control is available

        Parameters
        ----------
        control : str
            control label

        Returns
        -------
        bool
            if control exists
        """
        return control in dict(self.get_controller_list()).values()

    @property
    def speed(self) -> float:
        try:
            _value = self.get_current_controller_value("SpeedometerKPH")
        except ValueError:
            _value =  self.get_current_controller_value("SpeedometerMPH")
        
        return round(_value, 1)

    @property
    def coordinates(self) -> tuple[float, float]:
        """Get current geocoordinates (lat, lon) of train

        Returns
        -------
        tuple[float, float]
            latitude
            longitude
        """
        return self.get_current_controller_value(400), self.get_current_controller_value(401)

    @property
    def fuel_level(self) -> float:
        """Get current fuel level of train

        Returns
        -------
        float
            current fuel level
        """
        return self.get_current_controller_value(402)

    @property
    def gradient(self):
        """Get current gradient

        Returns
        -------
        float
            current gradient
        """
        return self.get_current_controller_value(404)

    @property
    def heading(self) -> float:
        """Get current heading
       

        Returns
        -------
        float
            current heading
        """
        return self.get_current_controller_value(405)

    @property
    def in_tunnel(self) -> bool:
        """Check if the train is currently (mostly) in tunnel     

        Returns
        -------
        float
            current tunnel status
        """
        return bool(self.get_current_controller_value(403))

    @property
    def current_time(self) -> datetime.time:
        """Get current time

        Returns
        -------
        datetime.time
            current time
        """
        hms = [int(self.get_current_controller_value(i)) for i in range(406, 409)]
        return datetime.time(*hms)

    @property
    def loco_name(self) -> LocoInfo | None:
        """
        Returns the Provider, Product and Engine name.

        Returns
        -------
        LocoInfo
            containing provider, product and engine
        """
        ret_str: str = self._dll.GetLocoName().decode()
        loco_info: list[str | None] = [None, None, None]

        if not ret_str:
            return
        for i, component in enumerate(ret_str.split(".:.")):
            loco_info[i] = component

        return LocoInfo(*loco_info)
    
    def horn(self, duration: float=1.0) -> None:
        self.set_controller_value("Horn", 1)
        time.sleep(duration)
        self.set_controller_value("Horn", 0)

    def bell(self, duration: float=1.0) -> None:
        self.set_controller_value("Bell", 1)
        time.sleep(duration)
        self.set_controller_value("Bell", 0)

    def wipers(self) -> bool:
        current_state = self.get_current_controller_value("Wipers")
        self.set_controller_value("Wipers", not current_state)
        return not current_state

    def aws_reset(self) -> None:
        self.set_controller_value("AWSReset", 1)
        time.sleep(0.1)
        self.set_controller_value("AWSReset", 0)

    def get_max_controller_value(self, index_or_name: int | str) -> float:
        """Syntactic sugar for get_controller_value(index_or_name, "max")

        Parameters
        ----------
        index_or_name : int | str
            either the index or name of the control

        Returns
        -------
        float
            the maximum value for this control
        """
        return self.get_controller_value(index_or_name, "max")

    def get_min_controller_value(self, index_or_name: str | int) -> float:
        """Syntactic sugar for get_controller_value(index_or_name, "min")

        Parameters
        ----------
        index_or_name : int | str
            either the index or name of the control

        Returns
        -------
        float
            the minimum value for this control
        """
        return self.get_controller_value(index_or_name, "min")

    @pydantic.validate_call
    def set_controller_value(self, index_or_name: pydantic.NonNegativeInt | str, value: float) -> None:
        """Sets value of controller control

        Parameters
        ----------
        index_or_name : int | str
            either the index or the name of the controller
        value : float
            the new value for this control
        """
        if not isinstance(index_or_name, int):
            index = self.get_controller_index(index_or_name)
        else:
            index = index_or_name
        self._dll.SetControllerValue(index, ctypes.c_float(value))

    def set_rail_driver_connected(self, connect: bool) -> None:
        """Needs to be called after instantiation in order to exchange data with Train Simulator

        Parameters
        ----------
        connect : bool
            whether to connect/disconnect
        """
        self._dll.SetRailDriverConnected(connect)
