#==========================================================================================\\\
#======= tests/test_utils/platform/test_cross_platform_compatibility.py ===============\\\
#==========================================================================================\\\

"""
Cross-Platform Compatibility Tests - System Reliability Foundation

This module provides comprehensive testing of cross-platform operation consistency
to validate Windows/Linux/Mac operation consistency and enable confident
cross-platform deployment.

MISSION: Validate Windows/Linux/Mac operation consistency
PRIORITY: HIGH (3x ROI - Deployment readiness)
COVERAGE TARGET: 100% (Critical for deployment)
"""

from __future__ import annotations

import pytest
import os
import sys
import platform
import tempfile
import pathlib
import math
import time
from unittest.mock import Mock, patch
from typing import Dict, Any, List

# Test imports
import numpy as np


class TestPlatformDetection:
    """Test platform detection and platform-specific behavior."""

    def test_current_platform_detection(self):
        """Test that current platform is correctly detected."""
        current_platform = platform.system()
        assert current_platform in ['Windows', 'Linux', 'Darwin'], f"Unsupported platform: {current_platform}"

        # Test platform-specific attributes
        assert platform.machine() is not None
        assert platform.processor() is not None
        assert platform.platform() is not None

    def test_python_version_compatibility(self):
        """Test Python version compatibility across platforms."""
        version_info = sys.version_info

        # Ensure Python 3.9+
        assert version_info.major == 3, f"Wrong Python major version: {version_info.major}"
        assert version_info.minor >= 9, f"Python version too old: {version_info.minor}"

        # Test version string format
        version_str = platform.python_version()
        assert len(version_str.split('.')) >= 2, f"Invalid version string: {version_str}"

    def test_platform_specific_paths(self):
        """Test platform-specific path handling."""
        # Test home directory detection
        home = pathlib.Path.home()
        assert home.exists(), "Home directory not accessible"
        assert home.is_dir(), "Home path is not a directory"

        # Test temp directory
        temp_dir = pathlib.Path(tempfile.gettempdir())
        assert temp_dir.exists(), "Temp directory not accessible"
        assert temp_dir.is_dir(), "Temp path is not a directory"

        # Test path separator consistency
        if platform.system() == 'Windows':
            assert os.sep == '\\', f"Wrong path separator on Windows: {os.sep}"
        else:
            assert os.sep == '/', f"Wrong path separator on Unix: {os.sep}"


class TestNumericalConsistency:
    """Test numerical computation consistency across platforms."""

    def test_floating_point_precision(self):
        """Test floating-point precision consistency."""
        # Basic arithmetic
        result = 0.1 + 0.2
        assert abs(result - 0.3) < 1e-15, "Floating point precision issue"

        # Trigonometric functions
        angle = math.pi / 4
        sin_val = math.sin(angle)
        cos_val = math.cos(angle)

        expected = math.sqrt(2) / 2
        assert abs(sin_val - expected) < 1e-15, "sin() precision issue"
        assert abs(cos_val - expected) < 1e-15, "cos() precision issue"

        # Exponential functions
        exp_val = math.exp(1.0)
        assert abs(exp_val - math.e) < 1e-15, "exp() precision issue"

    def test_numpy_consistency(self):
        """Test NumPy consistency across platforms."""
        # Array creation and operations
        arr = np.array([1.0, 2.0, 3.0])
        assert arr.dtype == np.float64, f"Wrong default dtype: {arr.dtype}"

        # Mathematical operations
        sqrt_arr = np.sqrt(arr)
        expected = np.array([1.0, math.sqrt(2), math.sqrt(3)])
        assert np.allclose(sqrt_arr, expected), "NumPy sqrt inconsistency"

        # Linear algebra
        matrix = np.array([[1, 2], [3, 4]])
        det = np.linalg.det(matrix)
        expected_det = -2.0
        assert abs(det - expected_det) < 1e-12, "NumPy determinant inconsistency"

    def test_random_number_reproducibility(self):
        """Test random number generation reproducibility."""
        # NumPy random seed
        np.random.seed(42)
        arr1 = np.random.random(10)

        np.random.seed(42)
        arr2 = np.random.random(10)

        assert np.array_equal(arr1, arr2), "NumPy random seed not reproducible"

        # Python random module
        import random
        random.seed(123)
        vals1 = [random.random() for _ in range(10)]

        random.seed(123)
        vals2 = [random.random() for _ in range(10)]

        assert vals1 == vals2, "Python random seed not reproducible"

    def test_mathematical_constants(self):
        """Test mathematical constants consistency."""
        # Test that constants are consistent across platforms
        assert abs(math.pi - 3.141592653589793) < 1e-15, "pi constant inconsistency"
        assert abs(math.e - 2.718281828459045) < 1e-15, "e constant inconsistency"

        # NumPy constants
        assert abs(np.pi - math.pi) < 1e-15, "NumPy pi inconsistency"
        assert abs(np.e - math.e) < 1e-15, "NumPy e inconsistency"


class TestFileSystemOperations:
    """Test file system operations across platforms."""

    def test_temporary_file_operations(self):
        """Test temporary file creation and operations."""
        # Create temporary file
        with tempfile.NamedTemporaryFile(mode='w+', delete=False) as tmp:
            tmp_path = pathlib.Path(tmp.name)

            # Write data
            tmp.write("test data\nline 2\n")
            tmp.flush()

        try:
            # Read data back
            assert tmp_path.exists(), "Temp file not created"

            content = tmp_path.read_text()
            assert "test data" in content, "File write/read failed"
            assert "line 2" in content, "Multiline write failed"

        finally:
            # Cleanup
            if tmp_path.exists():
                tmp_path.unlink()

    def test_directory_operations(self):
        """Test directory operations across platforms."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = pathlib.Path(tmp_dir)

            # Create subdirectory
            subdir = tmp_path / "subdir"
            subdir.mkdir()
            assert subdir.exists(), "Directory creation failed"
            assert subdir.is_dir(), "Created path is not directory"

            # Create file in subdirectory
            test_file = subdir / "test.txt"
            test_file.write_text("test content")
            assert test_file.exists(), "File creation in subdir failed"

            # List directory contents
            contents = list(tmp_path.iterdir())
            assert len(contents) == 1, f"Wrong directory contents count: {len(contents)}"
            assert contents[0] == subdir, "Directory listing incorrect"

    def test_path_normalization(self):
        """Test path normalization across platforms."""
        # Test different path separators
        test_paths = [
            "path/to/file.txt",
            "path\\to\\file.txt",
            "./path/to/file.txt",
            "path/../path/to/file.txt"
        ]

        for path_str in test_paths:
            path = pathlib.Path(path_str)
            normalized = path.resolve()
            assert isinstance(normalized, pathlib.Path), "Path normalization failed"

    def test_file_permissions(self):
        """Test file permissions handling across platforms."""
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            tmp_path = pathlib.Path(tmp.name)

        try:
            # Test readable
            assert tmp_path.is_file(), "Test file not created"

            # Check stat info is available
            stat_info = tmp_path.stat()
            assert stat_info.st_size >= 0, "Invalid file size"
            assert stat_info.st_mtime > 0, "Invalid modification time"

            # Platform-specific permission tests
            if platform.system() != 'Windows':
                # Unix-like systems have more granular permissions
                mode = stat_info.st_mode
                assert mode > 0, "Invalid file mode"

        finally:
            if tmp_path.exists():
                tmp_path.unlink()


class TestEnvironmentVariables:
    """Test environment variable handling across platforms."""

    def test_standard_environment_variables(self):
        """Test standard environment variables."""
        # PATH should always exist
        path_env = os.environ.get('PATH')
        assert path_env is not None, "PATH environment variable missing"
        assert len(path_env) > 0, "PATH environment variable empty"

        # Test path separation
        path_parts = path_env.split(os.pathsep)
        assert len(path_parts) > 0, "PATH has no components"

    def test_platform_specific_environment_variables(self):
        """Test platform-specific environment variables."""
        system = platform.system()

        if system == 'Windows':
            # Windows-specific variables
            assert 'USERPROFILE' in os.environ or 'HOME' in os.environ, "No user home variable"

        elif system in ['Linux', 'Darwin']:
            # Unix-like variables
            assert 'HOME' in os.environ, "HOME variable missing on Unix"
            assert 'USER' in os.environ or 'USERNAME' in os.environ, "No username variable"

    def test_environment_variable_modification(self):
        """Test environment variable modification."""
        test_var = 'PYTEST_CROSS_PLATFORM_TEST'
        test_value = 'test_value_123'

        # Set variable
        os.environ[test_var] = test_value
        assert os.environ[test_var] == test_value, "Environment variable setting failed"

        # Delete variable
        del os.environ[test_var]
        assert test_var not in os.environ, "Environment variable deletion failed"


class TestProcessAndThreading:
    """Test process and threading behavior across platforms."""

    def test_process_identification(self):
        """Test process identification."""
        # Process ID should be available
        pid = os.getpid()
        assert pid > 0, f"Invalid process ID: {pid}"
        assert isinstance(pid, int), f"Process ID not integer: {type(pid)}"

    def test_basic_threading(self):
        """Test basic threading functionality."""
        import threading

        result = []

        def worker():
            result.append(threading.current_thread().ident)

        # Create and start thread
        thread = threading.Thread(target=worker)
        thread.start()
        thread.join()

        # Verify thread executed
        assert len(result) == 1, "Thread did not execute"
        assert result[0] is not None, "Thread ID is None"
        assert result[0] != threading.current_thread().ident, "Thread ID same as main"

    def test_time_functions(self):
        """Test time functions consistency."""
        # Time should be monotonic
        start = time.perf_counter()
        time.sleep(0.01)  # 10ms sleep
        end = time.perf_counter()

        elapsed = end - start
        assert 0.005 < elapsed < 0.1, f"Time measurement inconsistent: {elapsed}s"

    @pytest.mark.skipif(platform.system() == 'Windows', reason="Unix-specific test")
    def test_unix_specific_features(self):
        """Test Unix-specific features."""
        # Test signal handling availability
        import signal
        assert hasattr(signal, 'SIGTERM'), "SIGTERM not available"
        assert hasattr(signal, 'SIGINT'), "SIGINT not available"

    @pytest.mark.skipif(platform.system() != 'Windows', reason="Windows-specific test")
    def test_windows_specific_features(self):
        """Test Windows-specific features."""
        # Test Windows-specific modules
        try:
            import winsound
            # If available, it should work
            assert hasattr(winsound, 'Beep'), "Windows sound module incomplete"
        except ImportError:
            # winsound might not be available in all Python installations
            pass


class TestScientificComputingConsistency:
    """Test scientific computing consistency across platforms."""

    def test_control_system_calculations(self):
        """Test control system calculation consistency."""
        # Test matrix operations common in control theory
        A = np.array([[0, 1], [-2, -3]])  # System matrix
        B = np.array([[0], [1]])          # Input matrix

        # Eigenvalues (poles)
        eigenvals = np.linalg.eigvals(A)

        # Should have two eigenvalues
        assert len(eigenvals) == 2, f"Wrong eigenvalue count: {len(eigenvals)}"

        # For this specific matrix, eigenvalues should be -1 and -2
        sorted_eigenvals = sorted(eigenvals.real)
        expected = [-2, -1]
        assert np.allclose(sorted_eigenvals, expected, atol=1e-10), "Eigenvalue calculation inconsistent"

    def test_differential_equation_integration(self):
        """Test differential equation integration consistency."""
        from scipy.integrate import solve_ivp

        # Simple harmonic oscillator: y'' + y = 0
        def harmonic_oscillator(t, y):
            return [y[1], -y[0]]

        # Initial conditions
        t_span = (0, 2*np.pi)
        y0 = [1, 0]  # x(0) = 1, x'(0) = 0

        # Solve
        sol = solve_ivp(harmonic_oscillator, t_span, y0, dense_output=True)
        assert sol.success, "Integration failed"

        # Check final value (should complete one period)
        final_state = sol.sol(2*np.pi)
        expected = [1, 0]  # Should return to initial state
        assert np.allclose(final_state, expected, atol=1e-2), "Integration inconsistent"

    def test_fft_consistency(self):
        """Test FFT computation consistency."""
        # Create a simple signal
        t = np.linspace(0, 1, 1000, endpoint=False)
        signal = np.sin(2*np.pi*10*t) + 0.5*np.sin(2*np.pi*20*t)

        # Compute FFT
        fft_result = np.fft.fft(signal)
        freqs = np.fft.fftfreq(len(signal), t[1] - t[0])

        # Find peaks (should be at 10 Hz and 20 Hz)
        magnitudes = np.abs(fft_result)
        peak_indices = np.argsort(magnitudes)[-4:]  # Top 4 peaks (positive and negative frequencies)
        peak_freqs = np.abs(freqs[peak_indices])

        # Should contain 10 and 20 Hz
        assert 10 in np.round(peak_freqs), "10 Hz peak not found"
        assert 20 in np.round(peak_freqs), "20 Hz peak not found"


class TestConfigurationConsistency:
    """Test configuration and data format consistency."""

    def test_yaml_parsing_consistency(self):
        """Test YAML parsing consistency across platforms."""
        try:
            import yaml
        except ImportError:
            pytest.skip("PyYAML not available")

        # Test configuration data
        config_data = {
            'physics': {
                'cart_mass': 1.5,
                'pendulum_mass': 0.5,
                'pendulum_length': 0.8
            },
            'control': {
                'gains': [10.0, 5.0, 8.0],
                'saturation': 50.0
            }
        }

        # Convert to YAML and back
        yaml_str = yaml.dump(config_data)
        parsed_data = yaml.safe_load(yaml_str)

        assert parsed_data == config_data, "YAML round-trip inconsistent"

    def test_json_consistency(self):
        """Test JSON handling consistency."""
        import json

        # Test data with floating point numbers
        test_data = {
            "parameters": [1.0, 2.5, 3.14159],
            "settings": {
                "enabled": True,
                "count": 42
            }
        }

        # JSON round-trip
        json_str = json.dumps(test_data)
        parsed_data = json.loads(json_str)

        assert parsed_data == test_data, "JSON round-trip inconsistent"

    def test_pickle_consistency(self):
        """Test pickle serialization consistency."""
        import pickle

        # Test complex data structure
        test_data = {
            'array': np.array([1, 2, 3]),
            'tuple': (1, 2, 3),
            'dict': {'a': 1, 'b': 2}
        }

        # Pickle round-trip
        pickled = pickle.dumps(test_data)
        unpickled = pickle.loads(pickled)

        # Compare arrays separately (due to NumPy comparison behavior)
        assert np.array_equal(unpickled['array'], test_data['array']), "Array pickle inconsistent"
        assert unpickled['tuple'] == test_data['tuple'], "Tuple pickle inconsistent"
        assert unpickled['dict'] == test_data['dict'], "Dict pickle inconsistent"


class TestPlatformResourceUsage:
    """Test platform resource usage patterns."""

    def test_memory_usage_patterns(self):
        """Test memory usage patterns across platforms."""
        try:
            import psutil
        except ImportError:
            pytest.skip("psutil not available")

        # Get initial memory usage
        process = psutil.Process()
        initial_memory = process.memory_info().rss

        # Allocate some memory
        large_array = np.zeros((1000, 1000))

        # Check memory increase
        current_memory = process.memory_info().rss
        memory_increase = current_memory - initial_memory

        # Should have increased significantly (at least 1MB)
        assert memory_increase > 1024 * 1024, f"Memory increase too small: {memory_increase}"

        # Cleanup
        del large_array

    def test_cpu_count_detection(self):
        """Test CPU count detection."""
        import multiprocessing

        cpu_count = multiprocessing.cpu_count()
        assert cpu_count > 0, f"Invalid CPU count: {cpu_count}"
        assert cpu_count <= 256, f"Unrealistic CPU count: {cpu_count}"  # Reasonable upper bound


class TestPlatformErrorHandling:
    """Test error handling consistency across platforms."""

    def test_file_operation_errors(self):
        """Test file operation error consistency."""
        # Try to read non-existent file
        with pytest.raises(FileNotFoundError):
            pathlib.Path("non_existent_file_12345.txt").read_text()

        # Try to write to invalid path
        if platform.system() == 'Windows':
            invalid_path = "Z:\\invalid\\path\\file.txt"  # Non-existent drive on Windows
        else:
            invalid_path = "/dev/null/invalid"  # Invalid path on Unix

        with pytest.raises((OSError, PermissionError, FileNotFoundError)):
            pathlib.Path(invalid_path).write_text("test")

    def test_division_by_zero_handling(self):
        """Test division by zero handling consistency."""
        # Integer division by zero
        with pytest.raises(ZeroDivisionError):
            result = 1 / 0

        # NumPy handling
        with pytest.warns(RuntimeWarning):
            result = np.array([1.0]) / 0.0
            assert np.isinf(result[0]), "NumPy division by zero inconsistent"

    def test_overflow_handling(self):
        """Test numeric overflow handling."""
        # Python integers can grow arbitrarily large
        big_int = 10**1000
        assert big_int > 0, "Large integer handling failed"

        # NumPy overflow behavior
        with pytest.warns(RuntimeWarning):
            result = np.float64(1e308) * 10
            assert np.isinf(result), "NumPy overflow handling inconsistent"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])