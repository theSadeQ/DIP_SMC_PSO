#==========================================================================================\\\
#======================== src/interfaces/monitoring/alerting.py ========================\\\
#==========================================================================================\\\
"""
Intelligent alerting system for interface monitoring.
This module provides comprehensive alerting capabilities including
rule-based alerts, adaptive thresholds, notification channels,
alert correlation, and escalation management for proactive
monitoring of all interface components.
"""

import asyncio
import json
import logging
import smtplib
import time
from abc import ABC, abstractmethod
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Callable, Union
import threading


class AlertLevel(Enum):
    """Alert severity levels."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class AlertStatus(Enum):
    """Alert lifecycle status."""
    ACTIVE = "active"
    ACKNOWLEDGED = "acknowledged"
    RESOLVED = "resolved"
    SUPPRESSED = "suppressed"


class NotificationChannel(Enum):
    """Available notification channels."""
    EMAIL = "email"
    WEBHOOK = "webhook"
    SMS = "sms"
    SLACK = "slack"
    DISCORD = "discord"
    LOG = "log"


@dataclass
class Alert:
    """Alert message with metadata."""
    id: str
    title: str
    description: str
    level: AlertLevel
    source: str
    timestamp: datetime = field(default_factory=datetime.now)
    status: AlertStatus = AlertStatus.ACTIVE
    tags: Set[str] = field(default_factory=set)
    metadata: Dict[str, Any] = field(default_factory=dict)
    acknowledged_by: Optional[str] = None
    acknowledged_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None
    escalated: bool = False
    escalation_count: int = 0
    notification_count: int = 0
    last_notification: Optional[datetime] = None


@dataclass
class AlertRule:
    """Rule for triggering alerts."""
    id: str
    name: str
    condition: str
    level: AlertLevel
    enabled: bool = True
    tags: Set[str] = field(default_factory=set)
    cooldown: int = 300  # seconds
    escalation_time: int = 1800  # seconds
    max_escalations: int = 3
    notification_channels: List[NotificationChannel] = field(default_factory=list)
    custom_message: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class NotificationConfig:
    """Configuration for notification channels."""
    channel: NotificationChannel
    enabled: bool = True
    config: Dict[str, Any] = field(default_factory=dict)
    rate_limit: int = 60  # seconds between notifications
    max_retries: int = 3
    retry_delay: int = 30  # seconds


class AlertCondition(ABC):
    """Base class for alert conditions."""

    @abstractmethod
    def evaluate(self, metrics: Dict[str, Any]) -> bool:
        """Evaluate condition against metrics."""
        pass


class ThresholdCondition(AlertCondition):
    """Simple threshold-based condition."""

    def __init__(self, metric_name: str, threshold: float, operator: str = ">"):
        self.metric_name = metric_name
        self.threshold = threshold
        self.operator = operator

    def evaluate(self, metrics: Dict[str, Any]) -> bool:
        value = metrics.get(self.metric_name)
        if value is None:
            return False

        if self.operator == ">":
            return value > self.threshold
        elif self.operator == ">=":
            return value >= self.threshold
        elif self.operator == "<":
            return value < self.threshold
        elif self.operator == "<=":
            return value <= self.threshold
        elif self.operator == "==":
            return value == self.threshold
        elif self.operator == "!=":
            return value != self.threshold
        else:
            return False


class CompositeCondition(AlertCondition):
    """Composite condition combining multiple conditions."""

    def __init__(self, conditions: List[AlertCondition], operator: str = "AND"):
        self.conditions = conditions
        self.operator = operator.upper()

    def evaluate(self, metrics: Dict[str, Any]) -> bool:
        if not self.conditions:
            return False

        if self.operator == "AND":
            return all(condition.evaluate(metrics) for condition in self.conditions)
        elif self.operator == "OR":
            return any(condition.evaluate(metrics) for condition in self.conditions)
        else:
            return False


class TrendCondition(AlertCondition):
    """Trend-based condition for detecting patterns."""

    def __init__(self, metric_name: str, window_size: int = 5, trend_threshold: float = 0.1):
        self.metric_name = metric_name
        self.window_size = window_size
        self.trend_threshold = trend_threshold
        self.history = deque(maxlen=window_size)

    def evaluate(self, metrics: Dict[str, Any]) -> bool:
        value = metrics.get(self.metric_name)
        if value is None:
            return False

        self.history.append(value)

        if len(self.history) < self.window_size:
            return False

        # Calculate trend (linear regression slope)
        n = len(self.history)
        x_mean = (n - 1) / 2
        y_mean = sum(self.history) / n

        numerator = sum((i - x_mean) * (y - y_mean) for i, y in enumerate(self.history))
        denominator = sum((i - x_mean) ** 2 for i in range(n))

        if denominator == 0:
            return False

        slope = numerator / denominator
        return abs(slope) > self.trend_threshold


class NotificationHandler(ABC):
    """Base class for notification handlers."""

    def __init__(self, config: NotificationConfig):
        self.config = config
        self.last_notification = {}
        self.logger = logging.getLogger(__name__)

    def can_send(self, alert: Alert) -> bool:
        """Check if notification can be sent (rate limiting)."""
        if not self.config.enabled:
            return False

        key = f"{alert.source}:{alert.title}"
        last_sent = self.last_notification.get(key)

        if last_sent:
            elapsed = (datetime.now() - last_sent).total_seconds()
            if elapsed < self.config.rate_limit:
                return False

        return True

    @abstractmethod
    async def send_notification(self, alert: Alert) -> bool:
        """Send notification for alert."""
        pass

    def record_notification(self, alert: Alert):
        """Record that notification was sent."""
        key = f"{alert.source}:{alert.title}"
        self.last_notification[key] = datetime.now()


class EmailNotificationHandler(NotificationHandler):
    """Email notification handler."""

    async def send_notification(self, alert: Alert) -> bool:
        try:
            smtp_server = self.config.config.get("smtp_server", "localhost")
            smtp_port = self.config.config.get("smtp_port", 587)
            username = self.config.config.get("username", "")
            password = self.config.config.get("password", "")
            from_addr = self.config.config.get("from_address", "alerts@system.local")
            to_addrs = self.config.config.get("to_addresses", [])

            if not to_addrs:
                self.logger.warning("No email recipients configured")
                return False

            msg = MIMEMultipart()
            msg['From'] = from_addr
            msg['To'] = ", ".join(to_addrs)
            msg['Subject'] = f"[{alert.level.value.upper()}] {alert.title}"

            body = f"""
            Alert: {alert.title}
            Level: {alert.level.value.upper()}
            Source: {alert.source}
            Time: {alert.timestamp}

            Description:
            {alert.description}

            Tags: {', '.join(alert.tags)}

            Metadata:
            {json.dumps(alert.metadata, indent=2)}
            """

            msg.attach(MIMEText(body, 'plain'))

            server = smtplib.SMTP(smtp_server, smtp_port)
            if username and password:
                server.starttls()
                server.login(username, password)

            server.send_message(msg)
            server.quit()

            self.record_notification(alert)
            return True

        except Exception as e:
            self.logger.error(f"Failed to send email notification: {e}")
            return False


class WebhookNotificationHandler(NotificationHandler):
    """Webhook notification handler."""

    async def send_notification(self, alert: Alert) -> bool:
        try:
            import aiohttp

            url = self.config.config.get("url")
            if not url:
                self.logger.warning("No webhook URL configured")
                return False

            headers = self.config.config.get("headers", {})
            timeout = self.config.config.get("timeout", 30)

            payload = {
                "alert": {
                    "id": alert.id,
                    "title": alert.title,
                    "description": alert.description,
                    "level": alert.level.value,
                    "source": alert.source,
                    "timestamp": alert.timestamp.isoformat(),
                    "status": alert.status.value,
                    "tags": list(alert.tags),
                    "metadata": alert.metadata
                }
            }

            async with aiohttp.ClientSession() as session:
                async with session.post(
                    url,
                    json=payload,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=timeout)
                ) as response:
                    if response.status == 200:
                        self.record_notification(alert)
                        return True
                    else:
                        self.logger.warning(
                            f"Webhook returned status {response.status}: {await response.text()}"
                        )
                        return False

        except Exception as e:
            self.logger.error(f"Failed to send webhook notification: {e}")
            return False


class LogNotificationHandler(NotificationHandler):
    """Log-based notification handler."""

    async def send_notification(self, alert: Alert) -> bool:
        try:
            log_level = self.config.config.get("log_level", "INFO")
            logger_name = self.config.config.get("logger_name", "alerts")

            logger = logging.getLogger(logger_name)
            log_message = f"ALERT [{alert.level.value.upper()}] {alert.title}: {alert.description}"

            if log_level.upper() == "CRITICAL":
                logger.critical(log_message)
            elif log_level.upper() == "ERROR":
                logger.error(log_message)
            elif log_level.upper() == "WARNING":
                logger.warning(log_message)
            else:
                logger.info(log_message)

            self.record_notification(alert)
            return True

        except Exception as e:
            self.logger.error(f"Failed to log notification: {e}")
            return False


class AlertManager:
    """Main alert management system."""

    def __init__(self):
        self.alerts: Dict[str, Alert] = {}
        self.rules: Dict[str, AlertRule] = {}
        self.conditions: Dict[str, AlertCondition] = {}
        self.notification_handlers: Dict[NotificationChannel, NotificationHandler] = {}
        self.alert_history: deque = deque(maxlen=10000)
        self.metrics_buffer: Dict[str, deque] = defaultdict(lambda: deque(maxlen=100))
        self.is_running = False
        self.evaluation_interval = 30  # seconds
        self.logger = logging.getLogger(__name__)
        self._lock = threading.Lock()

    def register_notification_handler(
        self,
        channel: NotificationChannel,
        handler: NotificationHandler
    ):
        """Register a notification handler."""
        self.notification_handlers[channel] = handler
        self.logger.info(f"Registered notification handler for {channel.value}")

    def add_rule(self, rule: AlertRule, condition: AlertCondition):
        """Add an alert rule with condition."""
        with self._lock:
            self.rules[rule.id] = rule
            self.conditions[rule.id] = condition
        self.logger.info(f"Added alert rule: {rule.name}")

    def remove_rule(self, rule_id: str):
        """Remove an alert rule."""
        with self._lock:
            self.rules.pop(rule_id, None)
            self.conditions.pop(rule_id, None)
        self.logger.info(f"Removed alert rule: {rule_id}")

    def update_metrics(self, metrics: Dict[str, Any]):
        """Update metrics for alert evaluation."""
        timestamp = datetime.now()
        for key, value in metrics.items():
            self.metrics_buffer[key].append((timestamp, value))

    def get_current_metrics(self) -> Dict[str, Any]:
        """Get current metrics values."""
        current_metrics = {}
        for key, values in self.metrics_buffer.items():
            if values:
                current_metrics[key] = values[-1][1]  # Latest value
        return current_metrics

    async def evaluate_rules(self) -> List[Alert]:
        """Evaluate all alert rules against current metrics."""
        current_metrics = self.get_current_metrics()
        new_alerts = []

        for rule_id, rule in self.rules.items():
            if not rule.enabled:
                continue

            condition = self.conditions.get(rule_id)
            if not condition:
                continue

            try:
                if condition.evaluate(current_metrics):
                    alert = await self._create_alert(rule, current_metrics)
                    if alert:
                        new_alerts.append(alert)

            except Exception as e:
                self.logger.error(f"Error evaluating rule {rule.name}: {e}")

        return new_alerts

    async def _create_alert(self, rule: AlertRule, metrics: Dict[str, Any]) -> Optional[Alert]:
        """Create alert from rule and metrics."""
        # Check cooldown
        similar_alerts = [
            a for a in self.alerts.values()
            if a.source == rule.name and a.status == AlertStatus.ACTIVE
        ]

        if similar_alerts:
            latest_alert = max(similar_alerts, key=lambda x: x.timestamp)
            cooldown_elapsed = (datetime.now() - latest_alert.timestamp).total_seconds()
            if cooldown_elapsed < rule.cooldown:
                return None

        alert_id = f"{rule.name}_{int(time.time())}"
        description = rule.custom_message or f"Rule '{rule.name}' triggered"

        alert = Alert(
            id=alert_id,
            title=rule.name,
            description=description,
            level=rule.level,
            source=rule.name,
            tags=rule.tags,
            metadata={
                "rule_id": rule.id,
                "triggering_metrics": metrics,
                **rule.metadata
            }
        )

        with self._lock:
            self.alerts[alert_id] = alert
            self.alert_history.append(alert)

        self.logger.info(f"Created alert: {alert.title} [{alert.level.value}]")

        # Send notifications
        await self._send_notifications(alert, rule)

        return alert

    async def _send_notifications(self, alert: Alert, rule: AlertRule):
        """Send notifications for alert."""
        for channel in rule.notification_channels:
            handler = self.notification_handlers.get(channel)
            if handler and handler.can_send(alert):
                try:
                    success = await handler.send_notification(alert)
                    if success:
                        alert.notification_count += 1
                        alert.last_notification = datetime.now()
                        self.logger.info(
                            f"Sent {channel.value} notification for alert {alert.id}"
                        )
                    else:
                        self.logger.warning(
                            f"Failed to send {channel.value} notification for alert {alert.id}"
                        )
                except Exception as e:
                    self.logger.error(
                        f"Error sending {channel.value} notification for alert {alert.id}: {e}"
                    )

    def acknowledge_alert(self, alert_id: str, acknowledged_by: str) -> bool:
        """Acknowledge an alert."""
        with self._lock:
            alert = self.alerts.get(alert_id)
            if alert and alert.status == AlertStatus.ACTIVE:
                alert.status = AlertStatus.ACKNOWLEDGED
                alert.acknowledged_by = acknowledged_by
                alert.acknowledged_at = datetime.now()
                self.logger.info(f"Alert {alert_id} acknowledged by {acknowledged_by}")
                return True
        return False

    def resolve_alert(self, alert_id: str) -> bool:
        """Resolve an alert."""
        with self._lock:
            alert = self.alerts.get(alert_id)
            if alert and alert.status in [AlertStatus.ACTIVE, AlertStatus.ACKNOWLEDGED]:
                alert.status = AlertStatus.RESOLVED
                alert.resolved_at = datetime.now()
                self.logger.info(f"Alert {alert_id} resolved")
                return True
        return False

    def suppress_alert(self, alert_id: str, duration: int = 3600) -> bool:
        """Suppress an alert for a duration."""
        with self._lock:
            alert = self.alerts.get(alert_id)
            if alert:
                alert.status = AlertStatus.SUPPRESSED
                alert.metadata["suppressed_until"] = (
                    datetime.now() + timedelta(seconds=duration)
                ).isoformat()
                self.logger.info(f"Alert {alert_id} suppressed for {duration} seconds")
                return True
        return False

    def get_active_alerts(self) -> List[Alert]:
        """Get all active alerts."""
        return [a for a in self.alerts.values() if a.status == AlertStatus.ACTIVE]

    def get_alerts_by_level(self, level: AlertLevel) -> List[Alert]:
        """Get alerts by severity level."""
        return [a for a in self.alerts.values() if a.level == level]

    def get_alerts_by_source(self, source: str) -> List[Alert]:
        """Get alerts by source."""
        return [a for a in self.alerts.values() if a.source == source]

    def get_alert_statistics(self) -> Dict[str, Any]:
        """Get alert statistics."""
        total_alerts = len(self.alerts)
        active_alerts = len(self.get_active_alerts())

        level_counts = defaultdict(int)
        status_counts = defaultdict(int)

        for alert in self.alerts.values():
            level_counts[alert.level.value] += 1
            status_counts[alert.status.value] += 1

        return {
            "total_alerts": total_alerts,
            "active_alerts": active_alerts,
            "level_distribution": dict(level_counts),
            "status_distribution": dict(status_counts),
            "total_rules": len(self.rules),
            "enabled_rules": len([r for r in self.rules.values() if r.enabled])
        }

    async def check_escalations(self):
        """Check for alerts that need escalation."""
        now = datetime.now()

        for alert in self.get_active_alerts():
            rule = self.rules.get(alert.metadata.get("rule_id"))
            if not rule or alert.escalated:
                continue

            escalation_time = timedelta(seconds=rule.escalation_time)
            if now - alert.timestamp >= escalation_time and alert.escalation_count < rule.max_escalations:
                alert.escalated = True
                alert.escalation_count += 1

                self.logger.warning(f"Escalating alert {alert.id} (escalation #{alert.escalation_count})")

                # Send escalation notifications
                await self._send_notifications(alert, rule)

    async def cleanup_resolved_alerts(self, retention_hours: int = 24):
        """Clean up old resolved alerts."""
        cutoff = datetime.now() - timedelta(hours=retention_hours)

        with self._lock:
            alerts_to_remove = [
                alert_id for alert_id, alert in self.alerts.items()
                if alert.status == AlertStatus.RESOLVED and alert.resolved_at
                and alert.resolved_at < cutoff
            ]

            for alert_id in alerts_to_remove:
                del self.alerts[alert_id]

        if alerts_to_remove:
            self.logger.info(f"Cleaned up {len(alerts_to_remove)} resolved alerts")

    async def start_monitoring(self):
        """Start continuous alert monitoring."""
        self.is_running = True
        self.logger.info("Starting alert monitoring")

        while self.is_running:
            try:
                # Evaluate rules
                new_alerts = await self.evaluate_rules()

                # Check escalations
                await self.check_escalations()

                # Cleanup old alerts
                await self.cleanup_resolved_alerts()

                await asyncio.sleep(self.evaluation_interval)

            except Exception as e:
                self.logger.error(f"Error in alert monitoring loop: {e}")
                await asyncio.sleep(self.evaluation_interval)

    def stop_monitoring(self):
        """Stop alert monitoring."""
        self.is_running = False
        self.logger.info("Stopped alert monitoring")

    def export_alerts(self, file_path: Path, format: str = "json"):
        """Export alerts to file."""
        try:
            if format.lower() == "json":
                alerts_data = []
                for alert in self.alerts.values():
                    alerts_data.append({
                        "id": alert.id,
                        "title": alert.title,
                        "description": alert.description,
                        "level": alert.level.value,
                        "source": alert.source,
                        "timestamp": alert.timestamp.isoformat(),
                        "status": alert.status.value,
                        "tags": list(alert.tags),
                        "metadata": alert.metadata,
                        "acknowledged_by": alert.acknowledged_by,
                        "acknowledged_at": alert.acknowledged_at.isoformat() if alert.acknowledged_at else None,
                        "resolved_at": alert.resolved_at.isoformat() if alert.resolved_at else None,
                        "escalation_count": alert.escalation_count,
                        "notification_count": alert.notification_count
                    })

                with open(file_path, 'w') as f:
                    json.dump(alerts_data, f, indent=2)

            self.logger.info(f"Exported {len(self.alerts)} alerts to {file_path}")

        except Exception as e:
            self.logger.error(f"Error exporting alerts: {e}")


# Global alert manager instance
alert_manager = AlertManager()


def create_threshold_rule(
    name: str,
    metric_name: str,
    threshold: float,
    level: AlertLevel = AlertLevel.WARNING,
    operator: str = ">",
    channels: List[NotificationChannel] = None
) -> Tuple[AlertRule, AlertCondition]:
    """Create a simple threshold-based alert rule."""
    if channels is None:
        channels = [NotificationChannel.LOG]

    rule = AlertRule(
        id=f"threshold_{name.lower().replace(' ', '_')}",
        name=name,
        condition=f"{metric_name} {operator} {threshold}",
        level=level,
        notification_channels=channels
    )

    condition = ThresholdCondition(metric_name, threshold, operator)

    return rule, condition


def create_composite_rule(
    name: str,
    conditions: List[Tuple[str, float, str]],  # (metric, threshold, operator)
    level: AlertLevel = AlertLevel.WARNING,
    logic: str = "AND",
    channels: List[NotificationChannel] = None
) -> Tuple[AlertRule, AlertCondition]:
    """Create a composite alert rule with multiple conditions."""
    if channels is None:
        channels = [NotificationChannel.LOG]

    rule = AlertRule(
        id=f"composite_{name.lower().replace(' ', '_')}",
        name=name,
        condition=f"Composite rule with {len(conditions)} conditions",
        level=level,
        notification_channels=channels
    )

    threshold_conditions = [
        ThresholdCondition(metric, threshold, operator)
        for metric, threshold, operator in conditions
    ]

    condition = CompositeCondition(threshold_conditions, logic)

    return rule, condition


async def setup_default_alerts():
    """Set up default system alerts."""
    # High CPU usage alert
    cpu_rule, cpu_condition = create_threshold_rule(
        "High CPU Usage",
        "cpu_usage",
        80.0,
        AlertLevel.WARNING,
        ">",
        [NotificationChannel.LOG, NotificationChannel.EMAIL]
    )
    alert_manager.add_rule(cpu_rule, cpu_condition)

    # High memory usage alert
    memory_rule, memory_condition = create_threshold_rule(
        "High Memory Usage",
        "memory_usage",
        85.0,
        AlertLevel.WARNING,
        ">",
        [NotificationChannel.LOG, NotificationChannel.EMAIL]
    )
    alert_manager.add_rule(memory_rule, memory_condition)

    # Critical system resource alert (composite)
    critical_rule, critical_condition = create_composite_rule(
        "Critical System Resources",
        [("cpu_usage", 95.0, ">"), ("memory_usage", 95.0, ">")],
        AlertLevel.CRITICAL,
        "OR",
        [NotificationChannel.LOG, NotificationChannel.EMAIL, NotificationChannel.WEBHOOK]
    )
    alert_manager.add_rule(critical_rule, critical_condition)


def configure_email_notifications(
    smtp_server: str,
    smtp_port: int = 587,
    username: str = "",
    password: str = "",
    from_address: str = "alerts@system.local",
    to_addresses: List[str] = None
):
    """Configure email notification handler."""
    if to_addresses is None:
        to_addresses = []

    config = NotificationConfig(
        channel=NotificationChannel.EMAIL,
        config={
            "smtp_server": smtp_server,
            "smtp_port": smtp_port,
            "username": username,
            "password": password,
            "from_address": from_address,
            "to_addresses": to_addresses
        }
    )

    handler = EmailNotificationHandler(config)
    alert_manager.register_notification_handler(NotificationChannel.EMAIL, handler)


def configure_webhook_notifications(url: str, headers: Dict[str, str] = None):
    """Configure webhook notification handler."""
    if headers is None:
        headers = {}

    config = NotificationConfig(
        channel=NotificationChannel.WEBHOOK,
        config={
            "url": url,
            "headers": headers
        }
    )

    handler = WebhookNotificationHandler(config)
    alert_manager.register_notification_handler(NotificationChannel.WEBHOOK, handler)


def configure_log_notifications(log_level: str = "INFO", logger_name: str = "alerts"):
    """Configure log notification handler."""
    config = NotificationConfig(
        channel=NotificationChannel.LOG,
        config={
            "log_level": log_level,
            "logger_name": logger_name
        }
    )

    handler = LogNotificationHandler(config)
    alert_manager.register_notification_handler(NotificationChannel.LOG, handler)