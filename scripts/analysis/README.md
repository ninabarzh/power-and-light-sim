# Analysis scripts

**Phase:** Post-collection data analysis
**Risk Level:** None (offline analysis)
**Goal:** Process collected data to identify vulnerabilities and patterns

## Scripts

### Network analysis
- **id-rogues-by-mac-address.py** - Identify unauthorized devices by MAC address

### Safety analysis
- **safety_plc_analysis.py** - Analyze safety PLC behavior and vulnerabilities

## Analysis types

### Device fingerprinting
Analyse responses to identify:
- Vendor and model
- Firmware versions
- Configuration weaknesses

### Behavioural analysis
- Normal operating patterns
- Anomaly detection baseline
- Attack indicators

### Vulnerability correlation
- Known CVEs applicable to discovered devices
- Configuration vulnerabilities
- Architectural weaknesses

## Outputs

Analysis scripts should produce:
- Risk rankings
- Vulnerability reports
- Attack surface maps
- Remediation recommendations

## Status

Needs expansion:
- More analysis scripts for discovery data
- Automated vulnerability mapping
- Report generation
