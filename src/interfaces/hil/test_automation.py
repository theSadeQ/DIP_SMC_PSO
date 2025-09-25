#==========================================================================================\\\
#==================== src/interfaces/hil/test_automation.py ============================\\\
#==========================================================================================\\\
"""
Automated testing framework for HIL systems.
This module provides comprehensive test automation capabilities including
test case management, assertion validation, performance testing, and
automated report generation for control system validation.
"""

import asyncio
import time
import json
from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List, Callable, Union
from enum import Enum
import logging


class TestStatus(Enum):
    """Test execution status enumeration."""
    PENDING = "pending"
    RUNNING = "running"
    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"
    ERROR = "error"


class AssertionType(Enum):
    """Test assertion type enumeration."""
    EQUALS = "equals"
    LESS_THAN = "less_than"
    GREATER_THAN = "greater_than"
    WITHIN_RANGE = "within_range"
    WITHIN_TOLERANCE = "within_tolerance"
    STEADY_STATE = "steady_state"
    STABILITY = "stability"
    RESPONSE_TIME = "response_time"


@dataclass
class TestAssertion:
    """Test assertion configuration."""
    name: str
    assertion_type: AssertionType
    target_signal: str
    expected_value: Any
    tolerance: float = 0.01
    timeout: float = 10.0
    description: str = ""


@dataclass
class TestCase:
    """Individual test case configuration."""
    name: str
    description: str
    duration: float
    initial_conditions: Dict[str, Any] = field(default_factory=dict)
    test_inputs: Dict[str, Any] = field(default_factory=dict)
    assertions: List[TestAssertion] = field(default_factory=list)
    fault_scenarios: List[str] = field(default_factory=list)
    setup_commands: List[str] = field(default_factory=list)
    teardown_commands: List[str] = field(default_factory=list)
    timeout: float = 60.0
    retry_count: int = 0


@dataclass
class TestSuite:
    """Test suite containing multiple test cases."""
    name: str
    description: str
    test_cases: List[TestCase] = field(default_factory=list)
    setup_suite: List[str] = field(default_factory=list)
    teardown_suite: List[str] = field(default_factory=list)
    parallel_execution: bool = False
    max_parallel: int = 4


@dataclass
class TestResult:
    """Test execution result."""
    test_name: str
    status: TestStatus
    start_time: float
    end_time: float
    duration: float
    assertions_passed: int = 0
    assertions_failed: int = 0
    error_message: Optional[str] = None
    data_log: Dict[str, Any] = field(default_factory=dict)
    performance_metrics: Dict[str, float] = field(default_factory=dict)


class HILTestFramework:
    """
    Comprehensive test automation framework for HIL systems.

    Provides automated test execution, assertion validation,
    performance testing, and report generation capabilities.
    """

    def __init__(self, hil_system: 'EnhancedHILSystem', test_scenarios: Optional[List['TestScenario']] = None):
        """Initialize HIL test framework."""
        self._hil_system = hil_system
        self._test_scenarios = test_scenarios or []

        # Test management
        self._test_suites: Dict[str, TestSuite] = {}
        self._test_results: List[TestResult] = []
        self._current_test: Optional[TestCase] = None

        # Execution control
        self._running = False
        self._stop_event = asyncio.Event()

        # Data collection
        self._test_data: Dict[str, List[Dict[str, Any]]] = {}
        self._assertion_results: List[Dict[str, Any]] = []

        # Configuration
        self._logger = logging.getLogger("hil_test_framework")
        self._report_generator = TestReportGenerator()

    def add_test_suite(self, suite: TestSuite) -> None:
        """Add test suite to framework."""
        self._test_suites[suite.name] = suite
        self._logger.info(f"Added test suite: {suite.name}")

    def add_test_case(self, suite_name: str, test_case: TestCase) -> None:
        """Add test case to existing suite."""
        if suite_name in self._test_suites:
            self._test_suites[suite_name].test_cases.append(test_case)
            self._logger.info(f"Added test case {test_case.name} to suite {suite_name}")

    async def run_test_suite(self, suite_name: str) -> Dict[str, Any]:
        """Run complete test suite."""
        try:
            if suite_name not in self._test_suites:
                raise ValueError(f"Test suite {suite_name} not found")

            suite = self._test_suites[suite_name]
            self._logger.info(f"Running test suite: {suite_name}")

            start_time = time.time()
            results = []

            # Setup suite
            await self._execute_setup_commands(suite.setup_suite)

            # Execute test cases
            if suite.parallel_execution:
                results = await self._run_parallel_tests(suite)
            else:
                results = await self._run_sequential_tests(suite)

            # Teardown suite
            await self._execute_teardown_commands(suite.teardown_suite)

            end_time = time.time()

            # Generate suite report
            suite_result = {
                'suite_name': suite_name,
                'start_time': start_time,
                'end_time': end_time,
                'duration': end_time - start_time,
                'total_tests': len(results),
                'passed': sum(1 for r in results if r.status == TestStatus.PASSED),
                'failed': sum(1 for r in results if r.status == TestStatus.FAILED),
                'errors': sum(1 for r in results if r.status == TestStatus.ERROR),
                'results': results
            }

            self._logger.info(f"Completed test suite {suite_name}: "
                            f"{suite_result['passed']}/{suite_result['total_tests']} passed")

            return suite_result

        except Exception as e:
            self._logger.error(f"Error running test suite {suite_name}: {e}")
            return {'suite_name': suite_name, 'error': str(e)}

    async def run_test_case(self, test_case: TestCase) -> TestResult:
        """Run individual test case."""
        try:
            self._current_test = test_case
            self._logger.info(f"Running test case: {test_case.name}")

            start_time = time.time()

            # Setup test
            await self._execute_setup_commands(test_case.setup_commands)
            await self._apply_initial_conditions(test_case.initial_conditions)

            # Execute test
            result = await self._execute_test_case(test_case)

            # Teardown test
            await self._execute_teardown_commands(test_case.teardown_commands)

            end_time = time.time()
            result.duration = end_time - start_time

            self._test_results.append(result)
            self._current_test = None

            self._logger.info(f"Test case {test_case.name} completed: {result.status.value}")
            return result

        except Exception as e:
            self._logger.error(f"Error running test case {test_case.name}: {e}")
            return TestResult(
                test_name=test_case.name,
                status=TestStatus.ERROR,
                start_time=start_time,
                end_time=time.time(),
                duration=time.time() - start_time,
                error_message=str(e)
            )

    async def run_all_suites(self) -> Dict[str, Any]:
        """Run all configured test suites."""
        try:
            self._logger.info("Running all test suites")
            suite_results = {}

            for suite_name in self._test_suites:
                result = await self.run_test_suite(suite_name)
                suite_results[suite_name] = result

            # Generate comprehensive report
            report = await self._report_generator.generate_comprehensive_report(
                suite_results, self._test_results
            )

            return report

        except Exception as e:
            self._logger.error(f"Error running all test suites: {e}")
            return {'error': str(e)}

    async def _run_sequential_tests(self, suite: TestSuite) -> List[TestResult]:
        """Run test cases sequentially."""
        results = []
        for test_case in suite.test_cases:
            result = await self.run_test_case(test_case)
            results.append(result)
        return results

    async def _run_parallel_tests(self, suite: TestSuite) -> List[TestResult]:
        """Run test cases in parallel."""
        semaphore = asyncio.Semaphore(suite.max_parallel)

        async def run_with_semaphore(test_case):
            async with semaphore:
                return await self.run_test_case(test_case)

        tasks = [run_with_semaphore(tc) for tc in suite.test_cases]
        return await asyncio.gather(*tasks)

    async def _execute_test_case(self, test_case: TestCase) -> TestResult:
        """Execute individual test case logic."""
        result = TestResult(
            test_name=test_case.name,
            status=TestStatus.RUNNING,
            start_time=time.time(),
            end_time=0.0,
            duration=0.0
        )

        try:
            # Apply test inputs
            await self._apply_test_inputs(test_case.test_inputs)

            # Inject faults if specified
            for fault_scenario in test_case.fault_scenarios:
                await self._hil_system._fault_injector.execute_scenario(fault_scenario)

            # Collect data and validate assertions
            await self._run_test_assertions(test_case, result)

            # Determine overall test result
            if result.assertions_failed == 0:
                result.status = TestStatus.PASSED
            else:
                result.status = TestStatus.FAILED

        except asyncio.TimeoutError:
            result.status = TestStatus.FAILED
            result.error_message = f"Test timeout after {test_case.timeout}s"

        except Exception as e:
            result.status = TestStatus.ERROR
            result.error_message = str(e)

        result.end_time = time.time()
        return result

    async def _run_test_assertions(self, test_case: TestCase, result: TestResult) -> None:
        """Run test assertions and collect results."""
        test_start = time.time()
        assertion_tasks = []

        # Start assertion monitoring tasks
        for assertion in test_case.assertions:
            task = asyncio.create_task(
                self._monitor_assertion(assertion, test_start, test_case.duration)
            )
            assertion_tasks.append(task)

        # Wait for test duration or all assertions to complete
        try:
            await asyncio.wait_for(
                asyncio.gather(*assertion_tasks),
                timeout=test_case.timeout
            )
        except asyncio.TimeoutError:
            # Cancel remaining tasks
            for task in assertion_tasks:
                task.cancel()

        # Collect assertion results
        for i, task in enumerate(assertion_tasks):
            try:
                if task.done() and not task.cancelled():
                    assertion_result = await task
                    if assertion_result['passed']:
                        result.assertions_passed += 1
                    else:
                        result.assertions_failed += 1
                    self._assertion_results.append(assertion_result)
                else:
                    result.assertions_failed += 1
            except Exception as e:
                result.assertions_failed += 1
                self._logger.error(f"Assertion {test_case.assertions[i].name} error: {e}")

    async def _monitor_assertion(self, assertion: TestAssertion,
                               start_time: float, duration: float) -> Dict[str, Any]:
        """Monitor and validate test assertion."""
        try:
            assertion_result = {
                'name': assertion.name,
                'type': assertion.assertion_type.value,
                'target_signal': assertion.target_signal,
                'expected_value': assertion.expected_value,
                'passed': False,
                'actual_value': None,
                'timestamp': None,
                'error_message': None
            }

            end_time = start_time + duration
            check_interval = 0.01  # 10ms check interval

            while time.time() < end_time:
                # Get current signal value
                current_value = await self._get_signal_value(assertion.target_signal)

                # Validate assertion
                validation_result = self._validate_assertion(assertion, current_value)

                if validation_result['passed']:
                    assertion_result.update({
                        'passed': True,
                        'actual_value': current_value,
                        'timestamp': time.time() - start_time
                    })
                    break

                await asyncio.sleep(check_interval)

            # If assertion never passed, record final state
            if not assertion_result['passed']:
                final_value = await self._get_signal_value(assertion.target_signal)
                assertion_result.update({
                    'actual_value': final_value,
                    'timestamp': duration,
                    'error_message': f"Assertion failed: expected {assertion.expected_value}, got {final_value}"
                })

            return assertion_result

        except Exception as e:
            return {
                'name': assertion.name,
                'passed': False,
                'error_message': str(e)
            }

    def _validate_assertion(self, assertion: TestAssertion, actual_value: Any) -> Dict[str, Any]:
        """Validate individual assertion."""
        try:
            if assertion.assertion_type == AssertionType.EQUALS:
                passed = abs(float(actual_value) - float(assertion.expected_value)) <= assertion.tolerance

            elif assertion.assertion_type == AssertionType.LESS_THAN:
                passed = float(actual_value) < float(assertion.expected_value)

            elif assertion.assertion_type == AssertionType.GREATER_THAN:
                passed = float(actual_value) > float(assertion.expected_value)

            elif assertion.assertion_type == AssertionType.WITHIN_RANGE:
                min_val, max_val = assertion.expected_value
                passed = min_val <= float(actual_value) <= max_val

            elif assertion.assertion_type == AssertionType.WITHIN_TOLERANCE:
                target_value, tolerance = assertion.expected_value
                passed = abs(float(actual_value) - float(target_value)) <= tolerance

            else:
                passed = False

            return {
                'passed': passed,
                'actual_value': actual_value
            }

        except Exception as e:
            return {
                'passed': False,
                'error': str(e)
            }

    async def _get_signal_value(self, signal_name: str) -> Any:
        """Get current value of specified signal."""
        try:
            # Get signal from HIL system data
            hil_status = await self._hil_system.get_system_status()

            # Search in input/output data
            if signal_name in self._hil_system._input_data:
                return self._hil_system._input_data[signal_name]
            elif signal_name in self._hil_system._output_data:
                return self._hil_system._output_data[signal_name]
            elif signal_name in self._hil_system._simulation_data:
                return self._hil_system._simulation_data[signal_name]
            else:
                # Try to get from devices
                for device_id in self._hil_system._device_manager.list_devices():
                    device = self._hil_system._device_manager.get_device(device_id)
                    data = await device.read_data()
                    if signal_name in data:
                        return data[signal_name]

                raise ValueError(f"Signal {signal_name} not found")

        except Exception as e:
            self._logger.error(f"Error getting signal {signal_name}: {e}")
            return None

    async def _execute_setup_commands(self, commands: List[str]) -> None:
        """Execute setup commands."""
        for command in commands:
            try:
                # Parse and execute command
                await self._execute_command(command)
            except Exception as e:
                self._logger.error(f"Setup command failed: {command} - {e}")

    async def _execute_teardown_commands(self, commands: List[str]) -> None:
        """Execute teardown commands."""
        for command in commands:
            try:
                await self._execute_command(command)
            except Exception as e:
                self._logger.error(f"Teardown command failed: {command} - {e}")

    async def _execute_command(self, command: str) -> None:
        """Execute individual command."""
        # Simple command parser - would be expanded for specific needs
        if command.startswith("set_"):
            # Parse set commands: set_signal_name:value
            parts = command[4:].split(":")
            if len(parts) == 2:
                signal_name, value = parts
                await self._set_signal_value(signal_name, float(value))

    async def _set_signal_value(self, signal_name: str, value: Any) -> None:
        """Set signal value in HIL system."""
        self._hil_system._output_data[signal_name] = value

    async def _apply_initial_conditions(self, conditions: Dict[str, Any]) -> None:
        """Apply initial conditions for test."""
        for signal_name, value in conditions.items():
            await self._set_signal_value(signal_name, value)

    async def _apply_test_inputs(self, inputs: Dict[str, Any]) -> None:
        """Apply test inputs."""
        for signal_name, value in inputs.items():
            await self._set_signal_value(signal_name, value)


class TestReportGenerator:
    """Generate comprehensive test reports."""

    def __init__(self):
        self._logger = logging.getLogger("test_report_generator")

    async def generate_comprehensive_report(self, suite_results: Dict[str, Any],
                                          test_results: List[TestResult]) -> Dict[str, Any]:
        """Generate comprehensive test report."""
        try:
            report = {
                'generated_at': time.time(),
                'summary': self._generate_summary(suite_results, test_results),
                'suite_results': suite_results,
                'detailed_results': [self._result_to_dict(r) for r in test_results],
                'statistics': self._generate_statistics(test_results),
                'recommendations': self._generate_recommendations(test_results)
            }

            return report

        except Exception as e:
            self._logger.error(f"Error generating report: {e}")
            return {'error': str(e)}

    def _generate_summary(self, suite_results: Dict[str, Any],
                         test_results: List[TestResult]) -> Dict[str, Any]:
        """Generate test summary."""
        total_tests = len(test_results)
        passed = sum(1 for r in test_results if r.status == TestStatus.PASSED)
        failed = sum(1 for r in test_results if r.status == TestStatus.FAILED)
        errors = sum(1 for r in test_results if r.status == TestStatus.ERROR)

        return {
            'total_suites': len(suite_results),
            'total_tests': total_tests,
            'passed': passed,
            'failed': failed,
            'errors': errors,
            'success_rate': passed / max(1, total_tests),
            'total_duration': sum(r.duration for r in test_results)
        }

    def _generate_statistics(self, test_results: List[TestResult]) -> Dict[str, Any]:
        """Generate test statistics."""
        if not test_results:
            return {}

        durations = [r.duration for r in test_results]

        return {
            'avg_duration': sum(durations) / len(durations),
            'max_duration': max(durations),
            'min_duration': min(durations),
            'total_assertions': sum(r.assertions_passed + r.assertions_failed for r in test_results),
            'assertion_success_rate': sum(r.assertions_passed for r in test_results) /
                                    max(1, sum(r.assertions_passed + r.assertions_failed for r in test_results))
        }

    def _generate_recommendations(self, test_results: List[TestResult]) -> List[str]:
        """Generate test recommendations."""
        recommendations = []

        failed_tests = [r for r in test_results if r.status == TestStatus.FAILED]
        if failed_tests:
            recommendations.append(f"Review {len(failed_tests)} failed test cases for potential issues")

        error_tests = [r for r in test_results if r.status == TestStatus.ERROR]
        if error_tests:
            recommendations.append(f"Fix {len(error_tests)} test cases with execution errors")

        return recommendations

    def _result_to_dict(self, result: TestResult) -> Dict[str, Any]:
        """Convert test result to dictionary."""
        return {
            'test_name': result.test_name,
            'status': result.status.value,
            'start_time': result.start_time,
            'end_time': result.end_time,
            'duration': result.duration,
            'assertions_passed': result.assertions_passed,
            'assertions_failed': result.assertions_failed,
            'error_message': result.error_message,
            'performance_metrics': result.performance_metrics
        }