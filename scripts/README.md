# ICS security testing scripts

Proof-of-concept scripts for security testing and validation of the ICS simulator.

## Directory Structure

### recon/
Reconnaissance and information gathering scripts. Non-invasive probing to discover devices, enumerate capabilities, and map the network.

**Purpose:** Footprinting phase - understand what exists before attacking.

### discovery/
Deep device discovery and protocol analysis. More intrusive than recon - actively probes memory maps, tests boundaries, and maps data structures.

**Purpose:** Detailed enumeration - understand how devices work internally.

### analysis/
Post-collection analysis and correlation scripts. Processes data gathered from recon/discovery to identify patterns, anomalies, and vulnerabilities.

**Purpose:** Make sense of collected data.

### exploitation/
Active attack demonstrations. Modifies device state, triggers unsafe conditions, or demonstrates security vulnerabilities.

**Purpose:** Demonstrate impact and validate security controls.

### assessment/
Security posture evaluation and reporting tools.

**Purpose:** Generate security assessments and recommendations.

## Usage workflow

1. **Recon** → Identify targets (devices, ports, protocols)
2. **Discovery** → Map device internals (registers, memory, capabilities)
3. **Analysis** → Identify vulnerabilities and attack vectors
4. **Exploitation** → Demonstrate attacks (READ-ONLY PoCs preferred)
5. **Assessment** → Document findings and recommendations

## Running scripts

All scripts should work against the running simulator:

```bash
# Start simulator (in one terminal)
python tools/simulator_manager.py

# Run PoC scripts (in another terminal)
python scripts/recon/turbine_recon.py
python scripts/discovery/scan_unit_ids.py
python scripts/exploitation/turbine_emergency_stop.py
```

## Script requirements

- Simulator must be running on localhost
- Default ports: Modbus TCP 10502-10520, S7 102-103, DNP3 20000-20002
- Python 3.10+ with pymodbus 3.11.4

## Development guidelines

- Scripts should be blackbox (no simulator internals knowledge)
- Include clear docstrings explaining the PoC
- Output should explain security impact
- Prefer read-only demonstrations
- Save results to JSON for evidence/reporting
