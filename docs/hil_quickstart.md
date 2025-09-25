# Hardware-in-the-Loop (HIL) Quickstart Guide

## Overview

Hardware-in-the-Loop (HIL) allows you to connect real hardware components to the DIP_SMC_PSO simulation system. The repository provides UDP-based networking to enable real-time data exchange between the simulation and external hardware.

## Architecture

The HIL system uses a client-server architecture with UDP communication:

```
┌─────────────────┐    UDP     ┌─────────────────┐
│   Plant Server  │ ◄─────────► │ Controller Client│
│   (Simulation)  │             │   (Hardware)    │
│   Port: 9000    │             │   Port: 9001    │
└─────────────────┘             └─────────────────┘
```

**Two Operating Modes:**

1. **Plant Server Mode** (Default): Simulation runs the plant dynamics, external hardware runs the controller
2. **Controller Client Mode**: Simulation runs the controller, external hardware provides plant feedback

## Quick Setup

### 1. Configuration

Edit `config.yaml` to configure HIL parameters:

```yaml
hil:
  plant_ip: 127.0.0.1          # IP address of plant server
  plant_port: 9000             # Plant server UDP port
  controller_ip: 127.0.0.1     # IP address of controller client
  controller_port: 9001        # Controller client UDP port
  extra_latency_ms: 0.0        # Additional latency simulation (ms)
  sensor_noise_std: 0.0        # Sensor noise standard deviation
```

### 2. Running HIL Simulation

```bash
# Basic HIL simulation
python simulate.py --run-hil --plot

# HIL with specific controller
python simulate.py --run-hil --ctrl sta_smc --plot

# HIL with custom configuration
python simulate.py --config custom_config.yaml --run-hil
```

## Network Protocol

### Data Packet Format

The HIL system uses robust UDP packet formats with sequence numbers and CRC-32 checksums for reliable communication:

**State Data (Plant → Controller):**
```
[sequence_num] [x] [theta1] [theta2] [x_dot] [theta1_dot] [theta2_dot] [crc32]
```

**Control Data (Controller → Plant):**
```
[sequence_num] [control_force] [crc32]
```

**Format Details:**
- `sequence_num`: 32-bit unsigned integer (network byte order)
- State values: 6 × 64-bit floats (network byte order)
- Control force: 64-bit float (network byte order)
- `crc32`: 32-bit CRC-32 checksum (network byte order)

### Packet Integrity Features

**Sequence Numbers:**
- Detect out-of-order, duplicate, or lost packets
- Plant server echoes last received sequence number
- Stale packets (sequence < last_received) are discarded

**CRC-32 Checksums:**
- Computed over sequence number + data payload
- Provides UDP integrity checking beyond basic checksum
- Corrupted packets automatically rejected

**Example CRC Computation (Python):**
```python
import struct
import zlib

# For control packet: sequence + command
payload = struct.pack("!I d", sequence_num, control_force)
crc = zlib.crc32(payload) & 0xFFFFFFFF
packet = payload + struct.pack("!I", crc)

# For state packet: sequence + 6 measurements
payload = struct.pack("!I 6d", sequence_num, x, theta1, theta2, x_dot, theta1_dot, theta2_dot)
crc = zlib.crc32(payload) & 0xFFFFFFFF
packet = payload + struct.pack("!I", crc)
```

### Sample Rate

- Default simulation timestep: 0.001s (1000 Hz)
- Network update rate: Matches simulation timestep
- Latency compensation: Configurable via `extra_latency_ms`

## Safety Guidelines

⚠️ **Important Safety Considerations**

1. **Start with Low Gains**: Use conservative controller parameters initially
2. **Implement Software Limits**:
   ```yaml
   controllers:
     classical_smc:
       max_force: 10.0    # Reduced from default 150.0
   ```
3. **Emergency Stop**: Keep physical emergency stop accessible
4. **Validate Units**: Ensure force units match hardware expectations (Newtons)
5. **Test Communication**: Verify network connectivity before enabling actuators

## Troubleshooting

### Common Issues

**Connection Refused:**
```bash
# Check if ports are available
netstat -an | grep 9000
netstat -an | grep 9001

# Test with telnet
telnet 127.0.0.1 9000
```

**High Latency:**
- Reduce `extra_latency_ms` to 0.0
- Use wired Ethernet instead of WiFi
- Check network utilization

**Control Instability:**
- Verify timestamp synchronization between systems
- Check for packet loss or reordering
- Reduce controller gains for initial testing

**Packet Integrity Issues:**
- Monitor CRC checksum failures in debug logs
- Check for sequence number gaps indicating lost packets
- Verify network byte order on different architectures

### Debug Mode

Enable detailed logging:

```python
import logging
logging.basicConfig(level=logging.DEBUG)

# Run HIL with debug output
python simulate.py --run-hil --plot --verbose
```

## Advanced Configuration

### Custom Network Settings

For distributed HIL setups across multiple machines:

```yaml
hil:
  plant_ip: 192.168.1.100      # Remote plant server
  plant_port: 9000
  controller_ip: 192.168.1.101  # Remote controller
  controller_port: 9001
  extra_latency_ms: 2.0        # Account for network delay
```

### Sensor Noise Simulation

Add realistic sensor noise for robustness testing:

```yaml
hil:
  sensor_noise_std: 0.001      # Standard deviation for position noise
```

### Integration with External Controllers

To connect your own controller hardware:

1. Implement UDP client that listens on `controller_port`
2. Parse incoming state packets (7 float values)
3. Compute control output
4. Send control packet back to plant server

Example in Python:
```python
import socket
import struct

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind(('127.0.0.1', 9001))

while True:
    data, addr = sock.recvfrom(1024)
    # Unpack state: timestamp, x, θ1, θ2, ẋ, θ̇1, θ̇2
    state = struct.unpack('!7f', data)

    # Your controller logic here
    control_force = your_controller(state[1:])  # Exclude timestamp

    # Send control response
    response = struct.pack('!2f', state[0], control_force)
    sock.sendto(response, addr)
```

## Performance Considerations

- **Real-time Requirements**: HIL simulation requires consistent timing
- **Network Buffer Size**: Default UDP buffers may need tuning for high-frequency data
- **CPU Priority**: Consider running simulation with higher process priority
- **Jitter Minimization**: Disable power management and background processes

## Integration with Main Simulation

HIL simulation integrates seamlessly with the main DIP_SMC_PSO workflow:

- All controllers (`classical_smc`, `sta_smc`, `adaptive_smc`, etc.) are HIL-compatible
- PSO optimization can run over HIL for real-world parameter tuning
- Plotting and analysis tools work with HIL data
- Configuration system provides unified HIL/simulation interface

## Fault Detection Integration

The HIL system integrates with the project's Fault Detection and Isolation (FDI) module for enhanced safety:

### Network Fault Detection

Built-in HIL fault detection includes:

```yaml
hil:
  max_packet_loss_rate: 0.05     # Maximum acceptable packet loss (5%)
  max_latency_ms: 10.0           # Maximum acceptable round-trip latency
  crc_failure_threshold: 3       # Consecutive CRC failures before fault
  sequence_gap_threshold: 10     # Missing sequence numbers before fault
```

### FDI Integration Example

```python
from src.fault_detection.fdi import FaultDetector
from src.interfaces.hil.plant_server import PlantServer

# Create FDI system with HIL-specific fault types
fdi = FaultDetector(
    fault_types=['sensor_failure', 'actuator_saturation', 'network_timeout']
)

# Initialize HIL with FDI monitoring
plant_server = PlantServer(config, fault_detector=fdi)

# FDI automatically monitors:
# - Sensor value bounds and rate limits
# - Network packet integrity and timing
# - Control signal saturation and discontinuities
```

### Automated Safety Responses

When faults are detected, the HIL system can:

1. **Graceful Degradation**: Switch to backup controller
2. **Safe Mode**: Apply minimal control to maintain stability
3. **Emergency Stop**: Disconnect from hardware and log incident

```yaml
fdi:
  safety_actions:
    network_timeout:
      action: "safe_mode"
      backup_controller: "classical_smc"
      reduced_gains: true
    sensor_failure:
      action: "emergency_stop"
      notify_hardware: true
```

## Related Documentation

- [Main README](README.md) - Overall project overview
- [Architecture Guide](architecture.md) - System architecture details
- [Testing Guide](TESTING.md) - How to test HIL functionality
- [Configuration Reference](api/index.md) - Complete configuration options