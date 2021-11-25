from dataclasses import dataclass


@dataclass
class Sensor:
    name: str


@dataclass
class ThermalCamera(Sensor):
    name: str = "thermal_camera"


@dataclass
class OpticalCamera(Sensor):
    name: str = "optical_camera"


@dataclass
class Microphone(Sensor):
    name: str = "microphone"


@dataclass
class LIDAR(Sensor):
    name: str = "lidar"
