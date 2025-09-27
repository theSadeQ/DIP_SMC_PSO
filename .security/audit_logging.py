#==========================================================================================\\\
#=============================== security/audit_logging.py ===============================\\\
#==========================================================================================\\\
"""
Production-Grade Security Audit Logging System
Comprehensive logging for security events, access control, and system operations.

SECURITY FEATURES:
- Tamper-resistant logging
- Structured audit events
- Real-time alerting
- Log integrity verification
- Secure log storage
- Compliance reporting
"""

import json
import hashlib
import time
import threading
from typing import Dict, Any, List, Optional, Union
from dataclasses import dataclass, asdict, field
from datetime import datetime, timezone
from enum import Enum
import logging
from pathlib import Path
import hmac
import secrets
from logging.handlers import RotatingFileHandler, SysLogHandler
import gzip
import os

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class AuditEventType(Enum):
    """Types of audit events to track"""
    # Authentication events
    LOGIN_SUCCESS = "auth.login.success"
    LOGIN_FAILURE = "auth.login.failure"
    LOGOUT = "auth.logout"
    SESSION_EXPIRED = "auth.session.expired"
    PASSWORD_CHANGE = "auth.password.change"
    ACCOUNT_LOCKED = "auth.account.locked"

    # Authorization events
    ACCESS_GRANTED = "authz.access.granted"
    ACCESS_DENIED = "authz.access.denied"
    PERMISSION_ESCALATION = "authz.permission.escalation"
    ROLE_CHANGED = "authz.role.changed"

    # Control system events
    CONTROL_COMMAND = "control.command"
    EMERGENCY_STOP = "control.emergency.stop"
    CONFIGURATION_CHANGE = "control.config.change"
    SYSTEM_START = "control.system.start"
    SYSTEM_STOP = "control.system.stop"
    MODE_CHANGE = "control.mode.change"

    # Security events
    SECURITY_VIOLATION = "security.violation"
    INTRUSION_ATTEMPT = "security.intrusion.attempt"
    RATE_LIMIT_EXCEEDED = "security.rate.limit.exceeded"
    INVALID_INPUT = "security.input.invalid"
    ENCRYPTION_ERROR = "security.encryption.error"

    # System events
    SYSTEM_ERROR = "system.error"
    SYSTEM_WARNING = "system.warning"
    SYSTEM_INFO = "system.info"
    PERFORMANCE_ALERT = "system.performance.alert"
    RESOURCE_EXHAUSTION = "system.resource.exhaustion"

    # Administrative events
    USER_CREATED = "admin.user.created"
    USER_DELETED = "admin.user.deleted"
    CONFIG_UPDATED = "admin.config.updated"
    BACKUP_CREATED = "admin.backup.created"
    MAINTENANCE_START = "admin.maintenance.start"
    MAINTENANCE_END = "admin.maintenance.end"

class AuditSeverity(Enum):
    """Severity levels for audit events"""
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    INFO = "INFO"

@dataclass
class AuditEvent:
    """Structured audit event"""
    event_id: str
    timestamp: datetime
    event_type: AuditEventType
    severity: AuditSeverity
    user_id: Optional[str]
    client_ip: Optional[str]
    session_id: Optional[str]
    resource: Optional[str]
    action: str
    result: str  # SUCCESS, FAILURE, ERROR
    details: Dict[str, Any]
    source_component: str
    risk_score: int = 0  # 0-100 risk assessment
    tags: List[str] = field(default_factory=list)
    correlation_id: Optional[str] = None

    def __post_init__(self):
        """Post-initialization processing"""
        if not self.event_id:
            self.event_id = secrets.token_hex(16)
        if not self.correlation_id:
            self.correlation_id = secrets.token_hex(8)

class AuditLogger:
    """Tamper-resistant audit logging system"""

    def __init__(self, log_dir: str = "logs/audit", max_log_size: int = 10485760,  # 10MB
                 backup_count: int = 10, enable_syslog: bool = False):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)

        self.max_log_size = max_log_size
        self.backup_count = backup_count
        self.enable_syslog = enable_syslog

        # Secret key for log integrity
        self.integrity_key = secrets.token_bytes(32)

        # Event counters and statistics
        self.event_counters: Dict[str, int] = {}
        self.security_alerts: List[AuditEvent] = []
        self.lock = threading.RLock()

        # Setup loggers
        self._setup_loggers()

        # Start background tasks
        self._start_background_tasks()

    def _setup_loggers(self):
        """Setup rotating file and syslog handlers"""
        # Audit logger for structured events
        self.audit_logger = logging.getLogger('audit')
        self.audit_logger.setLevel(logging.INFO)
        self.audit_logger.propagate = False

        # Rotating file handler
        audit_file = self.log_dir / "audit.jsonl"
        file_handler = RotatingFileHandler(
            audit_file, maxBytes=self.max_log_size, backupCount=self.backup_count
        )

        # JSON formatter for structured logging
        formatter = logging.Formatter('%(message)s')
        file_handler.setFormatter(formatter)
        self.audit_logger.addHandler(file_handler)

        # Syslog handler for enterprise environments
        if self.enable_syslog:
            try:
                syslog_handler = SysLogHandler(address='/dev/log')
                syslog_formatter = logging.Formatter(
                    'DIP-CONTROL-AUDIT: %(message)s'
                )
                syslog_handler.setFormatter(syslog_formatter)
                self.audit_logger.addHandler(syslog_handler)
            except Exception as e:
                logger.warning(f"Failed to setup syslog: {e}")

        # Security alert logger
        self.security_logger = logging.getLogger('security_alerts')
        self.security_logger.setLevel(logging.WARNING)

        security_file = self.log_dir / "security_alerts.log"
        security_handler = RotatingFileHandler(
            security_file, maxBytes=self.max_log_size, backupCount=self.backup_count
        )
        security_handler.setFormatter(formatter)
        self.security_logger.addHandler(security_handler)

    def log_event(self, event: AuditEvent) -> bool:
        """Log audit event with integrity protection"""
        try:
            with self.lock:
                # Add integrity hash
                event_dict = asdict(event)
                event_dict['timestamp'] = event.timestamp.isoformat()
                event_dict['event_type'] = event.event_type.value
                event_dict['severity'] = event.severity.value

                # Calculate integrity hash
                event_json = json.dumps(event_dict, sort_keys=True)
                integrity_hash = hmac.new(
                    self.integrity_key,
                    event_json.encode('utf-8'),
                    hashlib.sha256
                ).hexdigest()

                event_dict['integrity_hash'] = integrity_hash

                # Log structured event
                self.audit_logger.info(json.dumps(event_dict))

                # Update counters
                event_key = event.event_type.value
                self.event_counters[event_key] = self.event_counters.get(event_key, 0) + 1

                # Handle security events
                if self._is_security_event(event):
                    self._handle_security_event(event)

                return True

        except Exception as e:
            logger.error(f"Failed to log audit event: {e}")
            return False

    def _is_security_event(self, event: AuditEvent) -> bool:
        """Check if event is security-related"""
        security_events = [
            AuditEventType.LOGIN_FAILURE,
            AuditEventType.ACCESS_DENIED,
            AuditEventType.SECURITY_VIOLATION,
            AuditEventType.INTRUSION_ATTEMPT,
            AuditEventType.RATE_LIMIT_EXCEEDED,
            AuditEventType.ACCOUNT_LOCKED,
            AuditEventType.INVALID_INPUT,
            AuditEventType.ENCRYPTION_ERROR
        ]

        return (event.event_type in security_events or
                event.severity in [AuditSeverity.CRITICAL, AuditSeverity.HIGH] or
                event.risk_score >= 70)

    def _handle_security_event(self, event: AuditEvent):
        """Handle security events with alerting"""
        try:
            # Add to security alerts
            self.security_alerts.append(event)

            # Log to security alert logger
            alert_msg = (
                f"SECURITY ALERT: {event.event_type.value} - "
                f"User: {event.user_id} - IP: {event.client_ip} - "
                f"Risk: {event.risk_score}/100 - Details: {event.details}"
            )
            self.security_logger.warning(alert_msg)

            # Real-time alerting for critical events
            if event.severity == AuditSeverity.CRITICAL or event.risk_score >= 90:
                self._send_critical_alert(event)

        except Exception as e:
            logger.error(f"Failed to handle security event: {e}")

    def _send_critical_alert(self, event: AuditEvent):
        """Send immediate alert for critical security events"""
        # In production, this would integrate with alerting systems
        # like PagerDuty, Slack, email, SMS, etc.
        logger.critical(
            f"CRITICAL SECURITY ALERT: {event.event_type.value} - "
            f"Immediate attention required! Event ID: {event.event_id}"
        )

    def _start_background_tasks(self):
        """Start background monitoring and cleanup tasks"""
        def background_worker():
            while True:
                try:
                    # Cleanup old security alerts (keep last 1000)
                    if len(self.security_alerts) > 1000:
                        self.security_alerts = self.security_alerts[-1000:]

                    # Compress old log files
                    self._compress_old_logs()

                    # Generate periodic security summary
                    self._generate_security_summary()

                    time.sleep(300)  # Run every 5 minutes

                except Exception as e:
                    logger.error(f"Background task error: {e}")
                    time.sleep(60)

        worker_thread = threading.Thread(target=background_worker, daemon=True)
        worker_thread.start()

    def _compress_old_logs(self):
        """Compress old log files to save space"""
        try:
            for log_file in self.log_dir.glob("*.log.*"):
                if not log_file.suffix == '.gz':
                    compressed_file = log_file.with_suffix(log_file.suffix + '.gz')
                    if not compressed_file.exists():
                        with open(log_file, 'rb') as f_in:
                            with gzip.open(compressed_file, 'wb') as f_out:
                                f_out.writelines(f_in)
                        os.remove(log_file)
        except Exception as e:
            logger.error(f"Log compression error: {e}")

    def _generate_security_summary(self):
        """Generate periodic security summary"""
        try:
            recent_alerts = [
                alert for alert in self.security_alerts
                if (datetime.now(timezone.utc) - alert.timestamp).total_seconds() < 3600
            ]

            if recent_alerts:
                summary = {
                    'time_period': '1 hour',
                    'total_security_events': len(recent_alerts),
                    'critical_events': len([a for a in recent_alerts if a.severity == AuditSeverity.CRITICAL]),
                    'high_risk_events': len([a for a in recent_alerts if a.risk_score >= 70]),
                    'event_types': {}
                }

                for alert in recent_alerts:
                    event_type = alert.event_type.value
                    summary['event_types'][event_type] = summary['event_types'].get(event_type, 0) + 1

                self.security_logger.info(f"Security Summary: {json.dumps(summary)}")

        except Exception as e:
            logger.error(f"Security summary error: {e}")

    def verify_log_integrity(self, log_file: Optional[str] = None) -> Dict[str, Any]:
        """Verify integrity of audit logs"""
        results = {
            'verified_entries': 0,
            'corrupted_entries': 0,
            'total_entries': 0,
            'integrity_status': 'UNKNOWN'
        }

        try:
            if not log_file:
                log_file = self.log_dir / "audit.jsonl"

            with open(log_file, 'r') as f:
                for line_no, line in enumerate(f, 1):
                    try:
                        results['total_entries'] += 1

                        # Parse log entry
                        entry = json.loads(line.strip())

                        # Extract integrity hash
                        stored_hash = entry.pop('integrity_hash', None)
                        if not stored_hash:
                            results['corrupted_entries'] += 1
                            continue

                        # Recalculate hash
                        entry_json = json.dumps(entry, sort_keys=True)
                        calculated_hash = hmac.new(
                            self.integrity_key,
                            entry_json.encode('utf-8'),
                            hashlib.sha256
                        ).hexdigest()

                        # Verify integrity
                        if hmac.compare_digest(stored_hash, calculated_hash):
                            results['verified_entries'] += 1
                        else:
                            results['corrupted_entries'] += 1
                            logger.warning(f"Corrupted log entry at line {line_no}")

                    except Exception as e:
                        results['corrupted_entries'] += 1
                        logger.error(f"Error verifying line {line_no}: {e}")

            # Determine overall status
            if results['corrupted_entries'] == 0:
                results['integrity_status'] = 'VERIFIED'
            elif results['corrupted_entries'] < results['total_entries'] * 0.01:  # < 1% corruption
                results['integrity_status'] = 'MOSTLY_VERIFIED'
            else:
                results['integrity_status'] = 'COMPROMISED'

        except Exception as e:
            logger.error(f"Log integrity verification failed: {e}")
            results['integrity_status'] = 'VERIFICATION_FAILED'

        return results

    def get_security_dashboard(self) -> Dict[str, Any]:
        """Get security dashboard data"""
        with self.lock:
            recent_events = [
                event for event in self.security_alerts
                if (datetime.now(timezone.utc) - event.timestamp).total_seconds() < 86400  # 24 hours
            ]

            return {
                'total_events_24h': len(recent_events),
                'critical_events_24h': len([e for e in recent_events if e.severity == AuditSeverity.CRITICAL]),
                'high_risk_events_24h': len([e for e in recent_events if e.risk_score >= 70]),
                'top_event_types': self._get_top_event_types(recent_events),
                'risk_distribution': self._get_risk_distribution(recent_events),
                'event_timeline': self._get_event_timeline(recent_events),
                'integrity_status': self.verify_log_integrity()['integrity_status']
            }

    def _get_top_event_types(self, events: List[AuditEvent]) -> Dict[str, int]:
        """Get top event types from recent events"""
        event_counts = {}
        for event in events:
            event_type = event.event_type.value
            event_counts[event_type] = event_counts.get(event_type, 0) + 1

        return dict(sorted(event_counts.items(), key=lambda x: x[1], reverse=True)[:10])

    def _get_risk_distribution(self, events: List[AuditEvent]) -> Dict[str, int]:
        """Get risk score distribution"""
        distribution = {'low': 0, 'medium': 0, 'high': 0, 'critical': 0}

        for event in events:
            if event.risk_score < 30:
                distribution['low'] += 1
            elif event.risk_score < 60:
                distribution['medium'] += 1
            elif event.risk_score < 90:
                distribution['high'] += 1
            else:
                distribution['critical'] += 1

        return distribution

    def _get_event_timeline(self, events: List[AuditEvent]) -> List[Dict[str, Any]]:
        """Get hourly event timeline"""
        timeline = {}

        for event in events:
            hour_key = event.timestamp.replace(minute=0, second=0, microsecond=0)
            if hour_key not in timeline:
                timeline[hour_key] = {'total': 0, 'critical': 0, 'high_risk': 0}

            timeline[hour_key]['total'] += 1
            if event.severity == AuditSeverity.CRITICAL:
                timeline[hour_key]['critical'] += 1
            if event.risk_score >= 70:
                timeline[hour_key]['high_risk'] += 1

        return [
            {'hour': hour.isoformat(), **stats}
            for hour, stats in sorted(timeline.items())
        ]

# Global audit logger instance
audit_logger = AuditLogger()

# Convenience functions for common audit events
def log_login_success(user_id: str, client_ip: str, session_id: str):
    """Log successful login"""
    event = AuditEvent(
        event_id="",
        timestamp=datetime.now(timezone.utc),
        event_type=AuditEventType.LOGIN_SUCCESS,
        severity=AuditSeverity.INFO,
        user_id=user_id,
        client_ip=client_ip,
        session_id=session_id,
        resource="authentication",
        action="login",
        result="SUCCESS",
        details={'login_method': 'password'},
        source_component="authentication_service",
        risk_score=10
    )
    audit_logger.log_event(event)

def log_control_command(user_id: str, client_ip: str, control_force: float, session_id: str):
    """Log control command"""
    # Calculate risk score based on control force magnitude
    risk_score = min(100, int(abs(control_force) * 0.67))  # Scale 0-150N to 0-100 risk

    event = AuditEvent(
        event_id="",
        timestamp=datetime.now(timezone.utc),
        event_type=AuditEventType.CONTROL_COMMAND,
        severity=AuditSeverity.HIGH if abs(control_force) > 100 else AuditSeverity.MEDIUM,
        user_id=user_id,
        client_ip=client_ip,
        session_id=session_id,
        resource="dip_control_system",
        action="control_command",
        result="SUCCESS",
        details={'control_force_N': control_force, 'safety_bounds': [-150, 150]},
        source_component="control_interface",
        risk_score=risk_score,
        tags=['physical_control', 'safety_critical']
    )
    audit_logger.log_event(event)

def log_security_violation(user_id: Optional[str], client_ip: str, violation_type: str, details: Dict[str, Any]):
    """Log security violation"""
    event = AuditEvent(
        event_id="",
        timestamp=datetime.now(timezone.utc),
        event_type=AuditEventType.SECURITY_VIOLATION,
        severity=AuditSeverity.CRITICAL,
        user_id=user_id,
        client_ip=client_ip,
        session_id=None,
        resource="security_system",
        action="security_violation",
        result="BLOCKED",
        details={'violation_type': violation_type, **details},
        source_component="security_monitor",
        risk_score=95,
        tags=['security_incident', 'potential_attack']
    )
    audit_logger.log_event(event)