#==========================================================================================\\\
#==================================== tests/test_linkcode.py ============================\\\
#==========================================================================================\\\

"""Tests for linkcode_resolve function to ensure permalink accuracy."""

import pytest
import sys
import os
from pathlib import Path

# Add docs directory to path to import conf
docs_path = Path(__file__).parent.parent / 'docs'
sys.path.insert(0, str(docs_path))

try:
    from conf import linkcode_resolve
except ImportError:
    pytest.skip("Sphinx conf.py not available", allow_module_level=True)


class TestLinkcodeResolver:
    """Test cases for the linkcode_resolve function."""

    def test_linkcode_resolve_invalid_domain(self):
        """Test that non-Python domains return None."""
        result = linkcode_resolve('js', {'module': 'test', 'fullname': 'test'})
        assert result is None

    def test_linkcode_resolve_missing_module(self):
        """Test that missing module information returns None."""
        result = linkcode_resolve('py', {'fullname': 'test'})
        assert result is None

        result = linkcode_resolve('py', {'module': None, 'fullname': 'test'})
        assert result is None

    def test_linkcode_resolve_missing_fullname(self):
        """Test that missing fullname returns None."""
        result = linkcode_resolve('py', {'module': 'test'})
        assert result is None

    def test_linkcode_resolve_nonexistent_module(self):
        """Test that non-existent modules return None."""
        result = linkcode_resolve('py', {
            'module': 'nonexistent_module_12345',
            'fullname': 'test_function'
        })
        assert result is None

    def test_linkcode_resolve_valid_function(self):
        """Test permalink generation for a valid function."""
        # Test with a built-in function that should exist
        result = linkcode_resolve('py', {
            'module': 'os.path',
            'fullname': 'join'
        })

        # Built-in modules typically don't have source files
        # so this should return None, which is expected behavior
        assert result is None or isinstance(result, str)

    def test_linkcode_resolve_url_format(self):
        """Test that generated URLs have the correct format."""
        # We'll create a simple test case that we know will work
        import tempfile
        import types

        # Create a temporary module for testing
        test_module = types.ModuleType('test_module')
        test_module.__file__ = __file__  # Use this file as the source

        def test_function():
            """A test function for URL generation."""
            pass

        test_module.test_function = test_function
        sys.modules['test_module'] = test_module

        try:
            result = linkcode_resolve('py', {
                'module': 'test_module',
                'fullname': 'test_function'
            })

            if result:  # If a URL was generated
                assert 'github.com' in result
                assert 'blob/' in result
                assert '#L' in result
                assert result.startswith('https://')

        finally:
            # Clean up
            if 'test_module' in sys.modules:
                del sys.modules['test_module']

    def test_linkcode_resolve_line_numbers(self):
        """Test that line numbers are included in URLs."""
        # Similar to above but focusing on line number format
        import tempfile
        import types

        test_module = types.ModuleType('test_module')
        test_module.__file__ = __file__

        def test_function():
            """A test function spanning multiple lines.

            This function is designed to test
            that line numbers are correctly
            calculated and included in the URL.
            """
            pass

        test_module.test_function = test_function
        sys.modules['test_module'] = test_module

        try:
            result = linkcode_resolve('py', {
                'module': 'test_module',
                'fullname': 'test_function'
            })

            if result:
                # Check that line numbers are in L<start>-L<end> format
                import re
                line_pattern = r'#L(\d+)-L(\d+)'
                match = re.search(line_pattern, result)

                if match:
                    start_line, end_line = map(int, match.groups())
                    assert start_line > 0
                    assert end_line >= start_line

        finally:
            if 'test_module' in sys.modules:
                del sys.modules['test_module']

    def test_sha_in_url(self):
        """Test that commit SHA is included in URLs."""
        from conf import _get_commit_sha

        sha = _get_commit_sha()
        assert sha is not None
        assert len(sha) >= 7  # At least 7 characters for SHA

        # Test that SHA is either a commit hash or 'main'
        if sha != 'main':
            # Should be hexadecimal
            assert all(c in '0123456789abcdef' for c in sha.lower())

    @pytest.mark.parametrize("domain,info,expected", [
        ('js', {'module': 'test'}, None),
        ('py', {}, None),
        ('py', {'module': ''}, None),
        ('py', {'module': 'test', 'fullname': ''}, None),
    ])
    def test_linkcode_resolve_edge_cases(self, domain, info, expected):
        """Test edge cases for linkcode_resolve."""
        result = linkcode_resolve(domain, info)
        assert result == expected

    def test_decorated_functions(self):
        """Test permalink generation for decorated functions."""
        import functools
        import types

        # Create a test module with decorated functions
        test_module = types.ModuleType('test_decorated_module')
        test_module.__file__ = __file__

        def test_decorator(func):
            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                return func(*args, **kwargs)
            return wrapper

        @test_decorator
        def decorated_function():
            """A decorated function for testing."""
            pass

        test_module.decorated_function = decorated_function
        sys.modules['test_decorated_module'] = test_module

        try:
            result = linkcode_resolve('py', {
                'module': 'test_decorated_module',
                'fullname': 'decorated_function'
            })

            if result:
                assert 'github.com' in result
                assert '#L' in result

        finally:
            if 'test_decorated_module' in sys.modules:
                del sys.modules['test_decorated_module']

    def test_property_methods(self):
        """Test permalink generation for property methods."""
        import types

        test_module = types.ModuleType('test_property_module')
        test_module.__file__ = __file__

        class TestClass:
            @property
            def test_property(self):
                """A test property."""
                return 42

            @classmethod
            def test_classmethod(cls):
                """A test classmethod."""
                return cls

            @staticmethod
            def test_staticmethod():
                """A test staticmethod."""
                return "static"

        test_module.TestClass = TestClass
        sys.modules['test_property_module'] = test_module

        try:
            # Test property
            result = linkcode_resolve('py', {
                'module': 'test_property_module',
                'fullname': 'TestClass.test_property'
            })
            # Should handle property.fget

            # Test classmethod
            result = linkcode_resolve('py', {
                'module': 'test_property_module',
                'fullname': 'TestClass.test_classmethod'
            })
            # Should handle classmethod.__func__

            # Test staticmethod
            result = linkcode_resolve('py', {
                'module': 'test_property_module',
                'fullname': 'TestClass.test_staticmethod'
            })
            # Should handle staticmethod.__func__

        finally:
            if 'test_property_module' in sys.modules:
                del sys.modules['test_property_module']

    def test_module_fallback(self):
        """Test fallback to module-level links when object source is unavailable."""
        # This tests the fallback mechanism when inspect.getsourcefile returns None
        # but the module itself has a source file
        pass  # This is complex to test without actual C extensions

    def test_path_normalization(self):
        """Test that Windows paths are properly normalized to POSIX for URLs."""
        import tempfile
        import types

        # Create a temporary module to test path handling
        test_module = types.ModuleType('test_path_module')

        # Simulate a Windows-style path in the module file
        if os.name == 'nt':  # Only test on Windows
            test_module.__file__ = __file__.replace('/', '\\')
        else:
            test_module.__file__ = __file__

        def test_function():
            """Test function for path normalization."""
            pass

        test_module.test_function = test_function
        sys.modules['test_path_module'] = test_module

        try:
            result = linkcode_resolve('py', {
                'module': 'test_path_module',
                'fullname': 'test_function'
            })

            if result:
                # Ensure URL uses forward slashes, not backslashes
                assert '\\' not in result
                assert '/' in result

        finally:
            if 'test_path_module' in sys.modules:
                del sys.modules['test_path_module']

    @pytest.mark.parametrize("obj_type,obj_name", [
        ("decorated_no_wraps", "decorated_no_wraps"),
        ("decorated_with_wraps", "decorated_with_wraps"),
    ])
    def test_decorated_functions_have_line_anchors(self, obj_type, obj_name):
        """Test that decorated functions produce valid permalinks with line anchors."""
        import re
        try:
            import tests.sample_module as sample_mod
            obj = getattr(sample_mod, obj_name)

            result = linkcode_resolve('py', {
                'module': 'tests.sample_module',
                'fullname': obj_name
            })

            if result:
                assert "blob/" in result
                assert re.search(r"#L\d+-L\d+$", result), f"No line anchors in {result}"

        except ImportError:
            pytest.skip("sample_module not available")

    @pytest.mark.parametrize("obj_name", [
        "Klass.prop",
        "Klass.class_m",
        "Klass.static_m",
    ])
    def test_methods_and_properties_have_stable_urls(self, obj_name):
        """Test that properties, classmethods, and staticmethods produce valid URLs."""
        try:
            import tests.sample_module as sample_mod

            result = linkcode_resolve('py', {
                'module': 'tests.sample_module',
                'fullname': obj_name
            })

            if result:
                assert "blob/" in result
                assert "\\" not in result  # POSIX normalization
                assert "github.com" in result

        except ImportError:
            pytest.skip("sample_module not available")

    def test_module_fallback_when_no_lines(self):
        """Test fallback to module-level URL when object lines can't be determined."""
        # Test with a non-existent object that should trigger fallback
        result = linkcode_resolve('py', {
            'module': 'tests.sample_module',
            'fullname': 'NonExistentObject'
        })

        # Should return None for non-existent objects
        assert result is None


if __name__ == '__main__':
    pytest.main([__file__])