# Simulator Gaps & TODOs

Features discovered missing during PoC script validation.

## Modbus Protocol

### Device Identification (FC 43 / MEI 14) ⚠️
**Status:** PARTIALLY WORKING
**Issue:** Devices respond to Read Device Identification but all return the same identity

**What works:**
- Servers respond to FC 43 (Read Device Identification) requests
- Device identity data is loaded from `config/device_identity.yml`
- Identity information is returned (vendor, product code, revision, etc.)

**What doesn't work:**
- All devices return the same identity (last Modbus server created: "Wonderware")
- Cannot have different identities per server in same Python process

**Root cause - pymodbus 3.11.4 bug:**
- `ModbusDeviceIdentification` uses **class-level attributes** instead of instance attributes
- All instances share: `VendorName`, `ProductCode`, `MajorMinorRevision`, `stat_data`, etc.
- When FC 43 response is generated, pymodbus reads from class-level `stat_data`
- Last server to set values wins, overwriting all previous servers

**Attempted fixes (all failed):**
1. ✗ Instance attributes with `@property` decorators
2. ✗ `__dict__` manipulation to force instance-level storage
3. ✗ Sequential server creation (vs parallel)
4. ✗ Dynamic class creation with `type()` and empty dict
5. ✗ Dynamic class creation with explicit class attributes

**Current implementation:**
- Device identity config: `config/device_identity.yml` with realistic vendor/model/firmware
- Sequential Modbus startup (kept for consistency, doesn't fix the bug)
- Simple `ModbusDeviceIdentification()` with comment explaining the limitation
- All devices return "Wonderware System Platform 2017" (SCADA server identity)

**Security demonstration value:**
- Still demonstrates **information disclosure** vulnerability (FC 43 works without auth)
- Shows that device fingerprinting is possible via Modbus
- Attacker would see vendor/model/firmware information

**Acceptance:**
- This pymodbus bug is beyond reasonable workaround efforts
- The script works and demonstrates the security concept
- Moving on to test remaining 36 PoC scripts

**Script that discovered this:** `modbus_identity_probe.py`

**External bug:** pymodbus 3.11.4 `ModbusDeviceIdentification` design flaw: class attributes instead of instance attributes. Issue should be reported upstream.

## Temperature Units ✅
**Status:** FIXED
**Issue:** Was using Fahrenheit instead of Celsius
**Fixed by:** Converting TurbineState, TurbineParameters, and all related code


## Register Address Mapping ✅
**Status:** FIXED
**Issue:** DEFAULT_SETUP documented wrong addresses
**Fixed by:** Updated documentation to match actual implementation (0-9, 0-1)


---

## EtherNet/IP Protocol
**Status:** NOT IMPLEMENTED
**Issue:** No EtherNet/IP (CIP) server implementation

**What's missing:**
- EtherNet/IP server using cpppo or similar library
- Configured in devices.yml on port 44818 but no server code exists
- Protocol included in simulator_manager filter list but no creation logic

**Impact:**
- Cannot test Allen-Bradley/Rockwell Automation protocol attacks
- `enumerate-device.py` script fails with connection refused

**Implementation needed:**
- Create `components/network/servers/ethernetip_server.py`
- Implement CIP Identity Object (Class 0x01)
- Add server creation in `simulator_manager._expose_services()`

**Script blocked:** `enumerate-device.py`

---

## S7 Privileged Ports
**Status:** PARTIAL FAILURE
**Issue:** S7 servers cannot bind to ports 102/103 without root privileges

**Current situation:**
- S7 servers implemented and code works
- Default S7 port 102 (and 103 for safety PLC) are privileged (<1024)
- Running simulator as regular user fails with "Permission denied"
- Logs show: `TCP : Permission denied` for ports 102 and 103

**Workarounds:**
1. Run simulator with sudo (not recommended for development)
2. Use capability: `sudo setcap cap_net_bind_service=+ep python3`
3. Change S7 ports to >1024 in config (breaks protocol standards)
4. Use iptables/port forwarding: `iptables -t nat -A PREROUTING -p tcp --dport 102 -j REDIRECT --to-port 10502`

**Recommended:** Use capability or port forwarding for testing

**Script blocked:** `query-plc.py`

---

---

## Modbus Unit ID Validation
**Status:** ISSUE DISCOVERED
**Issue:** Modbus servers respond to ALL unit IDs, not just their configured one

**Current behavior:**
- Server configured with unit_id=1 responds to requests for unit_id=2, 3, 100, etc.
- All unit IDs return the same data from the same server
- No filtering/validation of requested unit ID vs configured unit ID

**Expected behavior:**
- Server should only respond to its configured unit_id
- Requests for other unit IDs should be ignored or return exception

**Impact:**
- Unrealistic - real Modbus devices validate unit ID
- Makes unit ID scanning less meaningful (everything responds)
- Allows unintended cross-device access

**Script that discovered this:** `scan_unit_ids.py`

---

## Next Gaps

Will be discovered as we test more scripts...
