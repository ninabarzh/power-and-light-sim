"""Protocol implementations - with optional dependency handling."""

__all__ = []

try:
    from .modbus_protocol import ModbusProtocol

    __all__.append("ModbusProtocol")
except ImportError:
    pass

try:
    from .iec104_protocol import IEC104Protocol

    __all__.append("IEC104Protocol")
except ImportError:
    pass

try:
    from .s7_protocol import S7Protocol

    __all__.append("S7Protocol")
except ImportError:
    pass

try:
    from .opcua_protocol import OPCUAProtocol

    __all__.append("OPCUAProtocol")
except ImportError:
    pass

try:
    from .dnp3_protocol import DNP3Protocol

    __all__.append("DNP3Protocol")
except ImportError:
    pass

try:
    from .iec61850_mms_protocol import IEC61850MMSProtocol

    __all__.append("IEC61850MMSProtocol")
except ImportError:
    pass

try:
    from .iec61850_goose_protocol import IEC61850GOOSEProtocol

    __all__.append("IEC61850GOOSEProtocol")
except ImportError:
    pass

try:
    from .modbus_rtu_protocol import ModbusRTUProtocol

    __all__.append("ModbusRTUProtocol")
except ImportError:
    pass
