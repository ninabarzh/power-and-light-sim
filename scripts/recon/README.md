# Reconnaissance scripts

**Phase:** Initial footprinting and information gathering
**Risk Level:** Low (passive/non-invasive)
**Goal:** Discover what devices exist and basic capabilities

## Scripts

### turbine_recon.py
**Status:** WORKING
**Purpose:** Read turbine configuration and telemetry from PLCs
**Targets:** Modbus TCP devices on ports 10502-10520
**Output:** JSON report with operational parameters

**What it demonstrates:**
- Unauthorized reading of setpoints and safety thresholds
- Real-time telemetry access (speed, temperature, pressure)
- Baseline data collection for attack planning

### modbus_identity_probe.py
**Status:** NEEDS TESTING
**Purpose:** Identify device vendor, model, firmware via Modbus
**Expected:** Device identification data

### enumerate-device.py
**Status:** NEEDS TESTING
**Purpose:** Enumerate device capabilities and protocols

### query-plc.py
**Status:** NEEDS TESTING
**Purpose:** Query PLC for basic information

### query-substation-controller.py
**Status:** NEEDS TESTING
**Purpose:** Query substation RTU/controller

### connect-remote-substation.py
**Status:** NEEDS TESTING
**Purpose:** Establish connection to remote substation

### raw-tcp-probing.py
**Status:** NEEDS TESTING
**Purpose:** Raw TCP port scanning and protocol detection

## Next steps

Go through each  script and make it functional:
1. Update to pymodbus 3.x API
2. Use correct register addresses (0-9)
3. Test against running simulator
4. Document what it reveals about the target
