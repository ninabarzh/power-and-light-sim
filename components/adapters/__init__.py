"""Adapter implementations - with optional dependency handling."""

__all__ = []

try:
    from .pymodbus_3114 import PyModbus3114Adapter

    __all__.append("PyModbus3114Adapter")
except ImportError:
    pass

try:
    from .c104_221 import IEC104C104Adapter

    __all__.append("IEC104C104Adapter")
except ImportError:
    pass

try:
    from .snap7_202 import Snap7Adapter202

    __all__.append("Snap7Adapter202")
except ImportError:
    pass

try:
    from .opcua_asyncua_118 import OPCUAAsyncua118Adapter

    __all__.append("OPCUAAsyncua118Adapter")
except ImportError:
    pass

try:
    from .dnp3_adapter import DNP3Adapter

    __all__.append("DNP3Adapter")
except ImportError:
    pass

try:
    from .iec61850_mms_adapter import IEC61850MMSAdapter

    __all__.append("IEC61850MMSAdapter")
except ImportError:
    pass

try:
    from .iec61850_goose_adapter import IEC61850GOOSEAdapter

    __all__.append("IEC61850GOOSEAdapter")
except ImportError:
    pass

try:
    from .modbus_rtu_adapter import ModbusRTUAdapter

    __all__.append("ModbusRTUAdapter")
except ImportError:
    pass
