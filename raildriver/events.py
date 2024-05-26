"""
Listener Class
==============

Main class for the monitoring of RailWorks/TSClassic activity via the Windows DLL
"""

import collections
import copy
import threading
import time
import typing

if typing.TYPE_CHECKING:
    from .library import RailDriver


class Listener:

    special_fields: dict[str, str] = {
        '!Coordinates': 'coordinates',
        '!FuelLevel': 'fuel_level',
        '!Gradient': 'gradient',
        '!Heading': 'heading',
        '!IsInTunnel': 'in_tunnel',
        '!LocoName': 'loco_name',
        '!Time': 'current_time',
    }

    def __init__(self, raildriver: "RailDriver", interval: float=0.5) -> None:
        """Initialize control listener. Requires raildriver.RailDriver instance.

        Parameters
        ----------
        raildriver : RailDriver
            RailDriver instance
        interval : float, optional
            how often to check the state of controls, by default 0.5
        """
        
        self._interval: float = interval
        self._raildriver: "RailDriver" = raildriver

        self._bindings: dict[str, list[typing.Callable]] = collections.defaultdict(list)
        self._current_data = collections.defaultdict(lambda: None)
        self._previous_data = collections.defaultdict(lambda: None)
        self._subscribed_fields: list[str] = []

        self._exc: Exception | None  = None
        self._running: bool = False
        self._thread: threading.Thread | None = None

        self._current_data: dict[str, typing.Any] = {}
        self._previous_data: dict[str, typing.Any] = {}
        self._iteration: int = 0

    def __getattr__(self, item):
        return self._bindings[item].append

    def _execute_bindings(self, type, *args, **kwargs):
        if (type_bindings := self._bindings.get(type)) is None:
            raise RuntimeError(f"Expected bindings for type '{type}' but none found")
        for binding in type_bindings:
            binding(*args, **kwargs)

    def _main_iteration(self) -> None:
        self._iteration += 1
        self._previous_data = copy.copy(self._current_data)

        for field_name in self._subscribed_fields:
            try:
                current_value = self._raildriver.get_current_controller_value(field_name)
            except ValueError:
                del self._current_data[field_name]
            else:
                self._current_data[field_name] = current_value
                if current_value != self._previous_data.get(field_name) and self._iteration > 1:
                    binding_name = f"on_{field_name.lower()}_change"
                    self._execute_bindings(binding_name, current_value, self._previous_data[field_name])

        for field_name, method_name in self.special_fields.items():
            current_value = getattr(self._raildriver, method_name)()
            self._current_data[field_name] = current_value
            if current_value != self._previous_data.get(field_name) and self._iteration > 1:
                binding_name = f"on_{field_name[1:].lower()}_change"
                self._execute_bindings(binding_name, current_value, self._previous_data[field_name])

    def _main_loop(self) -> None:
        try:
            while self.running:
                self._main_iteration()
                time.sleep(self._interval)
        except Exception as exc:
            self._exc = exc

    def start(self) -> None:
        """
        Start listening to changes
        """
        self._running = True
        self.thread = threading.Thread(target=self._main_loop)
        self.thread.start()

    def stop(self) -> None:
        """
        Stop listening to changes. This has to be explicitly called before you terminate your program
        or the listening thread will never die.
        """
        self.running = False

    def subscribe(self, field_names: list[str]) -> None:
        """Subscribe to given fields.

        Special fields cannot be subscribed to and will be checked on every iteration. These include:

        * loco name
        * coordinates
        * fuel level
        * gradient
        * current heading
        * is in tunnel
        * time

        You can of course still receive notifications when those change.

        It is important to understand that when the loco changes the set of possible controllers will likely change
        too. Any missing field changes will stop triggering notifications.
        Parameters
        ----------
        field_names : list[str]
            fieldsto to subscribe to

        Raises
        ------
        ValueError
            if field is not present on current loco
        """
        available_controls = dict(self._raildriver.get_controller_list()).values()
        for field in field_names:
            if field not in available_controls:
                raise ValueError(f"Cannot subscribe to a missing controller {field}")
        self.subscribed_fields = field_names
