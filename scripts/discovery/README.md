# Discovery scripts

**Phase:** Detailed enumeration and protocol analysis
**Risk Level:** Medium (active probing, may trigger alarms)
**Goal:** Map device internals, memory structures, and capabilities

## Scripts

### Device discovery
- **scan_unit_ids.py** - Scan for active Modbus unit IDs
- **modbus_memory_census.py** - Map entire Modbus address space
- **verify_memory_access.py** - Test read/write permissions across memory

### Register analysis
- **check_input_registers.py** - Enumerate input register values
- **check_discrete_points.py** - Map discrete input/coil states
- **sparse_input_register_scan.py** - Find sparse register allocations
- **sparse_modbus_scan.py** - Identify non-contiguous memory regions

### Pattern detection
- **poll_register_0.py** - Monitor register 0 for patterns
- **monitor_discrete_pattern.py** - Track discrete input patterns over time
- **track_counter_groups.py** - Identify counter/timer registers
- **correlate_analogue_discrete.py** - Link analog values to discrete states

### Device comparison
- **compare_unit_id_memory.py** - Compare memory maps across unit IDs
- **compare_mirror_values.py** - Detect mirrored/redundant data
- **multi_id_snapshot.py** - Capture simultaneous state across multiple devices

### Protocol analysis
- **decode_register_0_type.py** - Identify data type in register 0
- **discover_pymodbus_api.py** - Test pymodbus API capabilities
- **minimal-modbus-request-frame.py** - Craft minimal Modbus requests
- **test_write_permissions.py** - Test which registers are writable

## Security impact

These scripts reveal:
- Device architecture and memory layout
- Operational patterns and timing
- Writable control points (attack surfaces)
- Redundancy and monitoring gaps
- Data correlation for attack planning

## Status

Most scripts need updating for:
1. Pymodbus 3.x API compatibility
2. Correct register addresses (0-9 instead of high addresses)
3. Better error handling
4. JSON output for reporting
