#==========================================================================================\\\
#======================= src/interfaces/monitoring/dashboard.py ========================\\\
#==========================================================================================\\\
"""
Real-time monitoring dashboard for interface systems.
This module provides comprehensive dashboard capabilities including
real-time metrics visualization, interactive charts, system status
displays, alert management interface, and customizable monitoring
views for all interface components.
"""

import asyncio
import json
import logging
import time
import webbrowser
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple, Callable
import threading


@dataclass
class MetricSeries:
    """Time series data for a metric."""
    name: str
    values: deque = field(default_factory=lambda: deque(maxlen=1000))
    unit: str = ""
    description: str = ""
    color: str = "#007acc"
    visible: bool = True


@dataclass
class ChartConfig:
    """Configuration for dashboard charts."""
    title: str
    chart_type: str = "line"  # line, bar, gauge, pie
    metrics: List[str] = field(default_factory=list)
    height: int = 300
    width: int = 600
    refresh_interval: int = 5  # seconds
    auto_scale: bool = True
    y_min: Optional[float] = None
    y_max: Optional[float] = None
    show_legend: bool = True
    show_grid: bool = True


@dataclass
class DashboardLayout:
    """Dashboard layout configuration."""
    title: str
    charts: List[ChartConfig] = field(default_factory=list)
    columns: int = 2
    refresh_interval: int = 5
    auto_refresh: bool = True
    theme: str = "dark"  # dark, light


class DashboardServer:
    """Web-based dashboard server."""

    def __init__(self, host: str = "localhost", port: int = 8080):
        self.host = host
        self.port = port
        self.metrics: Dict[str, MetricSeries] = {}
        self.layouts: Dict[str, DashboardLayout] = {}
        self.current_layout = "default"
        self.is_running = False
        self.logger = logging.getLogger(__name__)
        self._lock = threading.Lock()

        # Create default layout
        self._create_default_layout()

    def _create_default_layout(self):
        """Create default dashboard layout."""
        default_layout = DashboardLayout(
            title="System Monitoring Dashboard",
            charts=[
                ChartConfig(
                    title="CPU Usage",
                    chart_type="line",
                    metrics=["cpu_usage"],
                    height=250
                ),
                ChartConfig(
                    title="Memory Usage",
                    chart_type="line",
                    metrics=["memory_usage"],
                    height=250
                ),
                ChartConfig(
                    title="Network I/O",
                    chart_type="line",
                    metrics=["network_bytes_sent", "network_bytes_recv"],
                    height=250
                ),
                ChartConfig(
                    title="System Load",
                    chart_type="gauge",
                    metrics=["system_load"],
                    height=250,
                    y_max=100.0
                ),
                ChartConfig(
                    title="Response Time",
                    chart_type="line",
                    metrics=["response_time"],
                    height=250
                ),
                ChartConfig(
                    title="Error Rate",
                    chart_type="bar",
                    metrics=["error_rate"],
                    height=250
                )
            ],
            columns=2
        )
        self.layouts["default"] = default_layout

    def register_metric(self, name: str, unit: str = "", description: str = "", color: str = "#007acc"):
        """Register a new metric for monitoring."""
        with self._lock:
            self.metrics[name] = MetricSeries(
                name=name,
                unit=unit,
                description=description,
                color=color
            )
        self.logger.info(f"Registered metric: {name}")

    def update_metric(self, name: str, value: float, timestamp: Optional[datetime] = None):
        """Update metric value."""
        if timestamp is None:
            timestamp = datetime.now()

        with self._lock:
            if name not in self.metrics:
                self.register_metric(name)

            self.metrics[name].values.append((timestamp, value))

    def update_metrics(self, metrics: Dict[str, float], timestamp: Optional[datetime] = None):
        """Update multiple metrics at once."""
        if timestamp is None:
            timestamp = datetime.now()

        with self._lock:
            for name, value in metrics.items():
                if name not in self.metrics:
                    self.register_metric(name)
                self.metrics[name].values.append((timestamp, value))

    def get_metric_data(self, name: str, duration_minutes: int = 60) -> List[Tuple[datetime, float]]:
        """Get metric data for the last N minutes."""
        if name not in self.metrics:
            return []

        cutoff = datetime.now() - timedelta(minutes=duration_minutes)
        return [
            (timestamp, value)
            for timestamp, value in self.metrics[name].values
            if timestamp >= cutoff
        ]

    def get_latest_metrics(self) -> Dict[str, float]:
        """Get latest values for all metrics."""
        latest = {}
        with self._lock:
            for name, series in self.metrics.items():
                if series.values:
                    latest[name] = series.values[-1][1]
        return latest

    def create_layout(self, name: str, layout: DashboardLayout):
        """Create a new dashboard layout."""
        self.layouts[name] = layout
        self.logger.info(f"Created dashboard layout: {name}")

    def set_current_layout(self, name: str):
        """Set the current active layout."""
        if name in self.layouts:
            self.current_layout = name
            self.logger.info(f"Switched to layout: {name}")
        else:
            self.logger.warning(f"Layout not found: {name}")

    def generate_html_dashboard(self) -> str:
        """Generate HTML dashboard."""
        layout = self.layouts[self.current_layout]

        html_template = f"""
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>{layout.title}</title>
            <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
            <style>
                body {{
                    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                    margin: 0;
                    padding: 20px;
                    background-color: {'#1e1e1e' if layout.theme == 'dark' else '#ffffff'};
                    color: {'#ffffff' if layout.theme == 'dark' else '#000000'};
                }}
                .header {{
                    text-align: center;
                    margin-bottom: 30px;
                    border-bottom: 2px solid {'#333' if layout.theme == 'dark' else '#ddd'};
                    padding-bottom: 20px;
                }}
                .dashboard-grid {{
                    display: grid;
                    grid-template-columns: repeat({layout.columns}, 1fr);
                    gap: 20px;
                    max-width: 1400px;
                    margin: 0 auto;
                }}
                .chart-container {{
                    background-color: {'#2d2d2d' if layout.theme == 'dark' else '#f9f9f9'};
                    border-radius: 8px;
                    padding: 15px;
                    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                }}
                .chart-title {{
                    text-align: center;
                    font-weight: bold;
                    margin-bottom: 10px;
                    font-size: 16px;
                }}
                .status-bar {{
                    position: fixed;
                    bottom: 0;
                    left: 0;
                    right: 0;
                    background-color: {'#333' if layout.theme == 'dark' else '#f0f0f0'};
                    padding: 10px;
                    text-align: center;
                    border-top: 1px solid {'#555' if layout.theme == 'dark' else '#ddd'};
                    font-size: 14px;
                }}
                .metric-summary {{
                    display: inline-block;
                    margin: 0 20px;
                }}
                .controls {{
                    text-align: center;
                    margin-bottom: 20px;
                }}
                .control-button {{
                    background-color: #007acc;
                    color: white;
                    border: none;
                    padding: 10px 20px;
                    margin: 0 5px;
                    border-radius: 4px;
                    cursor: pointer;
                    font-size: 14px;
                }}
                .control-button:hover {{
                    background-color: #005a9e;
                }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>{layout.title}</h1>
                <div class="controls">
                    <button class="control-button" onclick="toggleAutoRefresh()">
                        <span id="auto-refresh-text">Auto Refresh: ON</span>
                    </button>
                    <button class="control-button" onclick="refreshDashboard()">Refresh Now</button>
                    <button class="control-button" onclick="exportData()">Export Data</button>
                </div>
            </div>

            <div class="dashboard-grid">
                {self._generate_chart_html(layout)}
            </div>

            <div class="status-bar">
                <div class="metric-summary">
                    Last Updated: <span id="last-updated">{datetime.now().strftime('%H:%M:%S')}</span>
                </div>
                <div class="metric-summary">
                    Metrics: <span id="metric-count">{len(self.metrics)}</span>
                </div>
                <div class="metric-summary">
                    Status: <span id="system-status">Online</span>
                </div>
            </div>

            <script>
                let autoRefresh = true;
                let refreshInterval;

                {self._generate_chart_javascript(layout)}

                function startAutoRefresh() {{
                    if (autoRefresh) {{
                        refreshInterval = setInterval(refreshDashboard, {layout.refresh_interval * 1000});
                    }}
                }}

                function toggleAutoRefresh() {{
                    autoRefresh = !autoRefresh;
                    document.getElementById('auto-refresh-text').textContent =
                        'Auto Refresh: ' + (autoRefresh ? 'ON' : 'OFF');

                    if (autoRefresh) {{
                        startAutoRefresh();
                    }} else {{
                        clearInterval(refreshInterval);
                    }}
                }}

                function refreshDashboard() {{
                    fetch('/api/metrics')
                        .then(response => response.json())
                        .then(data => {{
                            updateCharts(data);
                            document.getElementById('last-updated').textContent =
                                new Date().toLocaleTimeString();
                        }})
                        .catch(error => {{
                            console.error('Error fetching data:', error);
                            document.getElementById('system-status').textContent = 'Error';
                        }});
                }}

                function exportData() {{
                    fetch('/api/export')
                        .then(response => response.blob())
                        .then(blob => {{
                            const url = window.URL.createObjectURL(blob);
                            const a = document.createElement('a');
                            a.href = url;
                            a.download = 'dashboard-data.json';
                            a.click();
                        }});
                }}

                // Start auto-refresh on page load
                startAutoRefresh();

                // Initial data load
                refreshDashboard();
            </script>
        </body>
        </html>
        """

        return html_template

    def _generate_chart_html(self, layout: DashboardLayout) -> str:
        """Generate HTML for charts."""
        chart_html = ""
        for i, chart in enumerate(layout.charts):
            chart_html += f"""
            <div class="chart-container">
                <div class="chart-title">{chart.title}</div>
                <div id="chart-{i}" style="height: {chart.height}px;"></div>
            </div>
            """
        return chart_html

    def _generate_chart_javascript(self, layout: DashboardLayout) -> str:
        """Generate JavaScript for charts."""
        js_code = ""

        for i, chart in enumerate(layout.charts):
            if chart.chart_type == "line":
                js_code += self._generate_line_chart_js(i, chart)
            elif chart.chart_type == "gauge":
                js_code += self._generate_gauge_chart_js(i, chart)
            elif chart.chart_type == "bar":
                js_code += self._generate_bar_chart_js(i, chart)

        js_code += """
        function updateCharts(data) {
            // Update each chart with new data
        """

        for i, chart in enumerate(layout.charts):
            js_code += f"""
            updateChart{i}(data);
            """

        js_code += "}"

        return js_code

    def _generate_line_chart_js(self, chart_id: int, chart: ChartConfig) -> str:
        """Generate JavaScript for line charts."""
        return f"""
        function initChart{chart_id}() {{
            const layout = {{
                title: '',
                xaxis: {{ title: 'Time' }},
                yaxis: {{ title: 'Value' }},
                showlegend: {str(chart.show_legend).lower()},
                plot_bgcolor: 'rgba(0,0,0,0)',
                paper_bgcolor: 'rgba(0,0,0,0)',
                font: {{ color: 'inherit' }}
            }};

            const config = {{
                responsive: true,
                displayModeBar: false
            }};

            Plotly.newPlot('chart-{chart_id}', [], layout, config);
        }}

        function updateChart{chart_id}(data) {{
            const traces = [];
            {json.dumps(chart.metrics)}.forEach((metric, index) => {{
                if (data[metric]) {{
                    traces.push({{
                        x: data[metric].timestamps,
                        y: data[metric].values,
                        type: 'scatter',
                        mode: 'lines+markers',
                        name: metric,
                        line: {{ width: 2 }}
                    }});
                }}
            }});

            Plotly.react('chart-{chart_id}', traces);
        }}

        initChart{chart_id}();
        """

    def _generate_gauge_chart_js(self, chart_id: int, chart: ChartConfig) -> str:
        """Generate JavaScript for gauge charts."""
        return f"""
        function initChart{chart_id}() {{
            const data = [{{
                type: "indicator",
                mode: "gauge+number+delta",
                value: 0,
                domain: {{ x: [0, 1], y: [0, 1] }},
                title: {{ text: "{chart.title}" }},
                gauge: {{
                    axis: {{ range: [null, {chart.y_max or 100}] }},
                    bar: {{ color: "darkblue" }},
                    steps: [
                        {{ range: [0, 50], color: "lightgray" }},
                        {{ range: [50, 85], color: "yellow" }},
                        {{ range: [85, 100], color: "red" }}
                    ],
                    threshold: {{
                        line: {{ color: "red", width: 4 }},
                        thickness: 0.75,
                        value: 90
                    }}
                }}
            }}];

            const layout = {{
                width: {chart.width},
                height: {chart.height},
                margin: {{ t: 25, r: 25, l: 25, b: 25 }},
                paper_bgcolor: 'rgba(0,0,0,0)',
                font: {{ color: 'inherit' }}
            }};

            Plotly.newPlot('chart-{chart_id}', data, layout);
        }}

        function updateChart{chart_id}(data) {{
            const metric = {json.dumps(chart.metrics[0] if chart.metrics else "")};
            if (data[metric] && data[metric].values.length > 0) {{
                const value = data[metric].values[data[metric].values.length - 1];
                Plotly.restyle('chart-{chart_id}', 'value', [value]);
            }}
        }}

        initChart{chart_id}();
        """

    def _generate_bar_chart_js(self, chart_id: int, chart: ChartConfig) -> str:
        """Generate JavaScript for bar charts."""
        return f"""
        function initChart{chart_id}() {{
            const layout = {{
                title: '',
                xaxis: {{ title: 'Metric' }},
                yaxis: {{ title: 'Value' }},
                showlegend: {str(chart.show_legend).lower()},
                plot_bgcolor: 'rgba(0,0,0,0)',
                paper_bgcolor: 'rgba(0,0,0,0)',
                font: {{ color: 'inherit' }}
            }};

            const config = {{
                responsive: true,
                displayModeBar: false
            }};

            Plotly.newPlot('chart-{chart_id}', [], layout, config);
        }}

        function updateChart{chart_id}(data) {{
            const x = [];
            const y = [];

            {json.dumps(chart.metrics)}.forEach(metric => {{
                if (data[metric] && data[metric].values.length > 0) {{
                    x.push(metric);
                    y.push(data[metric].values[data[metric].values.length - 1]);
                }}
            }});

            const trace = {{
                x: x,
                y: y,
                type: 'bar',
                marker: {{ color: '#007acc' }}
            }};

            Plotly.react('chart-{chart_id}', [trace]);
        }}

        initChart{chart_id}();
        """

    async def start_server(self):
        """Start the dashboard web server."""
        try:
            from aiohttp import web, web_runner
            import aiohttp_cors

            app = web.Application()

            # Add CORS support
            cors = aiohttp_cors.setup(app, defaults={
                "*": aiohttp_cors.ResourceOptions(
                    allow_credentials=True,
                    expose_headers="*",
                    allow_headers="*",
                    allow_methods="*"
                )
            })

            # Routes
            app.router.add_get('/', self._handle_dashboard)
            app.router.add_get('/api/metrics', self._handle_metrics_api)
            app.router.add_get('/api/export', self._handle_export_api)
            app.router.add_get('/api/layouts', self._handle_layouts_api)
            app.router.add_post('/api/layouts', self._handle_create_layout_api)

            # Add CORS to all routes
            for route in list(app.router.routes()):
                cors.add(route)

            runner = web_runner.AppRunner(app)
            await runner.setup()

            site = web_runner.TCPSite(runner, self.host, self.port)
            await site.start()

            self.is_running = True
            self.logger.info(f"Dashboard server started at http://{self.host}:{self.port}")

            # Open browser
            url = f"http://{self.host}:{self.port}"
            self.logger.info(f"Opening dashboard in browser: {url}")
            webbrowser.open(url)

        except Exception as e:
            self.logger.error(f"Failed to start dashboard server: {e}")
            raise

    async def _handle_dashboard(self, request):
        """Handle dashboard page request."""
        from aiohttp import web
        html = self.generate_html_dashboard()
        return web.Response(text=html, content_type='text/html')

    async def _handle_metrics_api(self, request):
        """Handle metrics API request."""
        from aiohttp import web

        duration_minutes = int(request.query.get('duration', 60))
        metrics_data = {}

        for name, series in self.metrics.items():
            data = self.get_metric_data(name, duration_minutes)
            if data:
                timestamps = [ts.isoformat() for ts, _ in data]
                values = [val for _, val in data]
                metrics_data[name] = {
                    'timestamps': timestamps,
                    'values': values,
                    'unit': series.unit,
                    'description': series.description
                }

        return web.json_response(metrics_data)

    async def _handle_export_api(self, request):
        """Handle data export API request."""
        from aiohttp import web

        export_data = {
            'timestamp': datetime.now().isoformat(),
            'metrics': {},
            'layouts': {}
        }

        # Export all metric data
        for name, series in self.metrics.items():
            data = [(ts.isoformat(), val) for ts, val in series.values]
            export_data['metrics'][name] = {
                'data': data,
                'unit': series.unit,
                'description': series.description
            }

        # Export layout configurations
        for name, layout in self.layouts.items():
            export_data['layouts'][name] = {
                'title': layout.title,
                'charts': [
                    {
                        'title': chart.title,
                        'chart_type': chart.chart_type,
                        'metrics': chart.metrics,
                        'height': chart.height,
                        'width': chart.width
                    }
                    for chart in layout.charts
                ],
                'columns': layout.columns,
                'theme': layout.theme
            }

        return web.json_response(export_data)

    async def _handle_layouts_api(self, request):
        """Handle layouts API request."""
        from aiohttp import web

        layouts_info = {}
        for name, layout in self.layouts.items():
            layouts_info[name] = {
                'title': layout.title,
                'chart_count': len(layout.charts),
                'columns': layout.columns,
                'theme': layout.theme
            }

        return web.json_response({
            'current_layout': self.current_layout,
            'layouts': layouts_info
        })

    async def _handle_create_layout_api(self, request):
        """Handle create layout API request."""
        from aiohttp import web

        try:
            data = await request.json()
            layout = DashboardLayout(
                title=data['title'],
                charts=[
                    ChartConfig(**chart_data)
                    for chart_data in data.get('charts', [])
                ],
                columns=data.get('columns', 2),
                theme=data.get('theme', 'dark')
            )

            self.create_layout(data['name'], layout)
            return web.json_response({'status': 'success'})

        except Exception as e:
            return web.json_response({'status': 'error', 'message': str(e)})

    def stop_server(self):
        """Stop the dashboard server."""
        self.is_running = False
        self.logger.info("Dashboard server stopped")


class DashboardManager:
    """Manager for multiple dashboard instances."""

    def __init__(self):
        self.dashboards: Dict[str, DashboardServer] = {}
        self.logger = logging.getLogger(__name__)

    def create_dashboard(
        self,
        name: str,
        host: str = "localhost",
        port: int = 8080
    ) -> DashboardServer:
        """Create a new dashboard instance."""
        dashboard = DashboardServer(host, port)
        self.dashboards[name] = dashboard
        self.logger.info(f"Created dashboard: {name}")
        return dashboard

    def get_dashboard(self, name: str) -> Optional[DashboardServer]:
        """Get dashboard by name."""
        return self.dashboards.get(name)

    def remove_dashboard(self, name: str):
        """Remove dashboard instance."""
        if name in self.dashboards:
            dashboard = self.dashboards[name]
            dashboard.stop_server()
            del self.dashboards[name]
            self.logger.info(f"Removed dashboard: {name}")

    async def start_all_dashboards(self):
        """Start all dashboard servers."""
        for name, dashboard in self.dashboards.items():
            try:
                await dashboard.start_server()
            except Exception as e:
                self.logger.error(f"Failed to start dashboard {name}: {e}")

    def stop_all_dashboards(self):
        """Stop all dashboard servers."""
        for dashboard in self.dashboards.values():
            dashboard.stop_server()


# Global dashboard manager
dashboard_manager = DashboardManager()


def create_system_dashboard() -> DashboardServer:
    """Create default system monitoring dashboard."""
    dashboard = dashboard_manager.create_dashboard("system", port=8080)

    # Register common system metrics
    dashboard.register_metric("cpu_usage", "%", "CPU utilization percentage", "#ff6b6b")
    dashboard.register_metric("memory_usage", "%", "Memory utilization percentage", "#4ecdc4")
    dashboard.register_metric("disk_usage", "%", "Disk utilization percentage", "#45b7d1")
    dashboard.register_metric("network_bytes_sent", "bytes", "Network bytes sent", "#96ceb4")
    dashboard.register_metric("network_bytes_recv", "bytes", "Network bytes received", "#ffeaa7")
    dashboard.register_metric("response_time", "ms", "Average response time", "#dda0dd")
    dashboard.register_metric("error_rate", "%", "Error rate percentage", "#ff7675")
    dashboard.register_metric("system_load", "", "System load average", "#fd79a8")

    return dashboard


def create_performance_dashboard() -> DashboardServer:
    """Create performance monitoring dashboard."""
    dashboard = dashboard_manager.create_dashboard("performance", port=8081)

    # Create performance-focused layout
    perf_layout = DashboardLayout(
        title="Performance Monitoring",
        charts=[
            ChartConfig(
                title="Response Time Distribution",
                chart_type="line",
                metrics=["response_time_p50", "response_time_p95", "response_time_p99"],
                height=300
            ),
            ChartConfig(
                title="Throughput",
                chart_type="line",
                metrics=["requests_per_second", "transactions_per_second"],
                height=300
            ),
            ChartConfig(
                title="Error Rates",
                chart_type="bar",
                metrics=["error_rate_4xx", "error_rate_5xx"],
                height=300
            ),
            ChartConfig(
                title="Resource Utilization",
                chart_type="gauge",
                metrics=["cpu_usage"],
                height=300,
                y_max=100
            )
        ],
        columns=2,
        theme="dark"
    )

    dashboard.create_layout("performance", perf_layout)
    dashboard.set_current_layout("performance")

    return dashboard


async def start_monitoring_dashboards():
    """Start all monitoring dashboards."""
    # Create and start system dashboard
    system_dash = create_system_dashboard()
    await system_dash.start_server()

    # Create and start performance dashboard
    perf_dash = create_performance_dashboard()
    await perf_dash.start_server()

    return system_dash, perf_dash