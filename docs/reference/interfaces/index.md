# Interfaces

This section maps to `src/interfaces/` and documents system interfaces used for data exchange, hardware devices, networks, monitoring, and HIL integration.

- Key modules:
  - {py:mod}`src.interfaces.core` (protocols, data types)
  - {py:mod}`src.interfaces.data_exchange` (schemas, serializers, streaming)
  - {py:mod}`src.interfaces.hardware` (sensors, actuators, device drivers)
  - {py:mod}`src.interfaces.network` (UDP/TCP/HTTP/WebSocket)
  - {py:mod}`src.interfaces.monitoring` (metrics collectors, diagnostics)
  - {py:mod}`src.interfaces.hil` (controller client, plant server, real-time sync)

See also: HIL section for a focused view on hardware-in-the-loop workflows.

