# Contributing to UU Power & Light Simulator

*"The thing about keeping a city's lights on is that you can't simply wave your hands and hope for the best. There are 
rules, testing procedures, and an understanding that if something breaks, someone will notice. Immediately."*

Thank you for your interest in contributing to the UU Power & Light ICS simulator. This project simulates critical 
infrastructure: the sort that, if it fails in reality, leaves people quite literally in the dark. As such, we 
maintain certain standards.

## Contribution philosophy

This simulator exists to improve security. Contributions should serve that purpose, whether you're adding new attack 
surfaces, defensive capabilities, protocol implementations, or documentation that helps others understand industrial 
control systems better.

We welcome contributions from:
- Security researchers exploring ICS/SCADA vulnerabilities
- Industrial control professionals sharing domain knowledge
- Educators developing training scenarios
- Anyone who believes critical infrastructure security matters

What we expect: rigour, testing, and an understanding that poorly-written code in a security research tool can mislead 
others. Get it right, or don't submit it, or contact the community.

## Before beginning

### Understand the Licence

This project uses the Polyform Noncommercial Licence 1.0.0, with a security research exception.

What this means for contributors:
- The project remains under the copyright of Ty Myrddin (© 2026), for now
- Your contributions will be licenced under the same terms
- By submitting code, you grant the project maintainers perpetual rights to use your contribution under both noncommercial and commercial licences
- You retain copyright of your work, but acknowledge the dual-licensing model
- If you're uncomfortable with this, discuss it before contributing

Security Research Exception: Your work here can be used for legitimate research, vulnerability analysis, and 
defensive security (even if that involves attack tooling). See [SECURITY-RESEARCH-EXCEPTION.md](SECURITY-RESEARCH-EXCEPTION.md).

Commercial Licence: Organisations using this for paid services need a commercial licence. Your contributions may 
be used in that context. If this concerns you, [ask first](https://tymyrddin.dev/contact/).

## Code standards

### Architecture rules

This simulator follows strict architectural layering (see [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)). Violating 
these rules will result in rejection, no matter how clever the code.

Forbidden:
- Circular dependencies (the architecture is a directed acyclic graph for a reason)
- Direct device-to-device references (always use DataStore)
- Bypassing SimulationTime (all time queries go through the singleton)
- Protocol-specific logic in device implementations (devices expose memory maps; protocols translate)

Required:
- Async/await for all I/O operations
- ICSLogger integration for all components (see [components/devices/README.md](components/devices/README.md))
- Type hints (we use them extensively; you should too)
- Docstrings for public methods (Google/NumPy style)

If Ponder has to refactor your code to make it fit the architecture, you've done it wrong.

### Testing Requirements

This project has 1000+ passing tests. Your PR will not break them.

Requirements:
- All existing tests must pass (`pytest tests/`)
- New features require tests (unit tests at minimum, integration tests where appropriate)
- Bug fixes should include a test demonstrating the bug, then proving it's fixed
- Security features require tests showing they detect what they claim to detect

Running tests:
```bash
# All tests
pytest tests/

# Skip slow tests during development
pytest tests/unit -m "not slow"

# Specific subsystem
pytest tests/unit/protocols/
pytest tests/integration/
```

Coverage: We don't enforce a coverage percentage, but if your code is untested, explain why in the PR.

### Code style

- Linting: Code must pass `ruff check .` (we use ruff for linting and formatting)
- Formatting: Run `ruff format .` before committing
- Type checking: We don't require mypy, but type hints are mandatory

Pre-commit hooks (recommended):
```bash
pip install pre-commit
pre-commit install
```

This runs ruff automatically before commits. Saves everyone time.

## What to contribute

### Highly-valued contributions

New device types:
- IEDs (Intelligent Electronic Devices) with IEC 61850
- PMUs (Phasor Measurement Units)
- Protection relays (SEL, ABB, Siemens)
- Additional vendor-specific PLCs

Protocol implementations:
- Complete DNP3 implementation (currently partial)
- Full IEC 61850 GOOSE/MMS support
- Profibus/Profinet
- BACnet (building automation)

Physics models:
- Hydraulic systems (pumps, valves, pressure)
- Thermal dynamics (heat exchangers, cooling systems)
- Electrical load flow improvements

Security features:
- Detection rules for ICS-specific attacks
- SIEM correlation rules
- Anomaly detection algorithms
- Forensic analysis capabilities

Documentation:
- Attack scenario guides
- Protocol exploitation tutorials
- Device configuration examples
- Wiring diagrams for SCADA systems

### What not to contribute

- Malware or destructive payloads intended for production systems (this is a *simulator*)
- Exploits for 0-days without coordinated responsible disclosure
- Code that violates the architectural principles
- Features that exist solely to "look cool" but serve no security research purpose

If you're uncertain whether your idea fits, [ask first](https://tymyrddin.dev/contact/). Saves everyone's time.

## Contribution process

### Check for existing work

- Search [issues](https://github.com/tymyrddin/power-and-light-sim/issues) to avoid duplication
- Large features should have an issue discussing approach before implementation
- If you're fixing a bug, create an issue first describing the problem

### Fork and branch

```bash
# Fork the repository on GitHub, then:
git clone https://github.com/YOUR-USERNAME/power-and-light-sim.git
cd power-and-light-sim

# Create a feature branch
git checkout -b feature/your-feature-name
```

### Develop and Test

```bash
# Set up development environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -r requirements.txt

# Make your changes
# ...

# Run tests
pytest tests/

# Run linter
ruff check --fix
```

### Submit pull request

Before submitting:
- [ ] All tests pass locally
- [ ] Code passes `ruff check .`
- [ ] Documentation updated (if adding features)
- [ ] Architecture diagrams updated (if changing structure)
- [ ] Commit messages are clear and reference issues

PR descriptions include:
- What problem this solves or what feature it adds
- How to test it (commands to run, expected output)
- Any breaking changes or migration notes
- Related issue numbers (preferably)

### Code Review

Expect feedback. We may request changes for:
- Architectural compliance
- Improving test coverage
- Clear documentation
- Fixing subtle bugs you missed

This isn't personal. Industrial control systems are unforgiving; the code must be correct.

Review timeline:
- Simple fixes: Usually reviewed within a few days
- Large features: May take longer, especially if architectural discussion needed
- Security-sensitive changes: Require extra scrutiny

If you don't hear back within a week, politely ping the PR.

## Security research ethics

This simulator exists to improve security, not to cause harm.

Responsible use:
- Use this simulator for authorised testing and research only
- If you discover a vulnerability pattern applicable to real systems, follow coordinated responsible disclosure
- Don't use techniques developed here against systems you don't own or have permission to test
- If you're uncertain about the ethics of an approach, ask

Responsible disclosure:
- If you discover a security issue *in this simulator itself* (for example an unintended attack surface), report it privately first
- Use GitHub's [private security advisory feature](https://github.com/tymyrddin/power-and-light-sim/security/advisories) or contact us directly

The goal is to raise the level of security, not lower it.

## Development environment

### System requirements

- Python 3.12+ (type hints and modern async features required)
- Linux/macOS preferred (Windows works but networking features may behave differently)
- Git (obviously)

### Initial setup (without fork)

```bash
# Clone repository
git clone https://github.com/tymyrddin/power-and-light-sim.git
cd power-and-light-sim

# Create virtual environment
python3.12 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run tests to verify setup
pytest tests/unit -m "not slow"

# Start simulator to verify it works
python tools/simulator_manager.py
```

### Project structure

```
components/
├── devices/          # Device implementations (PLCs, RTUs, HMIs, historians)
├── protocols/        # Protocol implementations (Modbus, DNP3, OPC UA, etc.)
├── network/          # Network simulation and protocol servers
├── physics/          # Physics engines (turbine, reactor, HVAC, grid)
├── security/         # ICSLogger, authentication, anomaly detection
├── state/            # SystemState, DataStore (centralised state management)
└── time/             # SimulationTime (unified time management)

tests/
├── unit/             # Component-level tests
├── integration/      # Cross-component tests
└── scenario/         # End-to-end attack/defence scenarios
```

Read [docs/architecture.md](docs/ARCHITECTURE.md) to understand component dependencies before modifying anything significant.

### Running the simulator

```bash
# Start simulator (opens protocol servers on real ports)
python tools/simulator_manager.py

# In another terminal, test with external tools:
# Modbus read
mbtget -r -a 0 -n 10 localhost:[portnumber]

# OPC UA browse
python -c "from opcua import Client; c=Client('opc.tcp://localhost:4840'); c.connect(); print(c.get_root_node().get_children())"

# IEC 104 status
# (requires IEC 104 client tools)
```

### Debugging tips

- Logs: Check `logs/` directory for detailed component logs
- State inspection: DataStore methods allow querying device state
- Simulation time: Use `SimulationTime` to control time speed for faster testing
- Network issues: Check `config/network.yml` for zone policies

## Documentation

If you're adding features, update documentation:

- README.md - High-level changes (new protocols, major features)
- docs/architecture.md - Architectural changes (new components, dependencies)
- components/devices/README.md - New device types or patterns
- Docstrings - Public methods must have docstrings

Good documentation prevents Ponder having to answer the same questions repeatedly.

## Getting help

- Issues: Use [GitHub issues](https://github.com/tymyrddin/power-and-light-sim/issues) for bugs and feature requests
- Contact: For licensing, commercial use, or sensitive security topics: https://tymyrddin.dev/contact/

## Acknowledgements

By contributing, you help improve the security of critical infrastructure (even if only by providing a better training 
ground for those learning to defend it). That matters.

The Patrician appreciates competence. Ponder appreciates code that doesn't break at 3 at night. Both appreciate contributors 
who understand that infrastructure security is not a game, but apparently, a roleplay.

Thank you for your contribution.

---

Licence: By submitting a contribution, you agree to licence your work under the project's Polyform Noncommercial 
Licence, and grant the maintainers rights to use it under both noncommercial and commercial licences.

Code of Conduct: Be professional, be respectful, and remember that we're all trying to make things more secure. If 
you can't manage that, your contributions won't be welcome regardless of their technical merit.

Last Updated: February 2026