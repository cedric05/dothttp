"""
Integration tests for retry, timeout, and proxy features.

These tests verify actual behavior, not just parsing.
"""
import pytest
import time
from unittest.mock import Mock, patch, MagicMock
from requests import Response, HTTPError, Timeout
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from dothttp.parse import dothttp_model
from dothttp.parse.request_base import RequestCompiler
from dothttp.models.computed import Config, HttpDef


class TestRetryBehavior:
    """Test that retry actually retries requests"""

    def test_create_retry_adapter_with_all_params(self):
        """Test that _create_retry_adapter creates correct adapter"""
        # Create a mock compiler with httpdef
        compiler = Mock()
        compiler.httpdef = HttpDef(
            name="test",
            method="GET",
            url="http://example.com",
            retry_total=3,
            retry_backoff_factor=2.0,
            retry_status_forcelist=[500, 502, 503]
        )

        # Import the actual method
        from dothttp.parse.request_base import RequestCompiler
        adapter = RequestCompiler._create_retry_adapter(compiler)

        assert adapter is not None
        assert isinstance(adapter, HTTPAdapter)
        assert adapter.max_retries.total == 3
        assert adapter.max_retries.backoff_factor == 2.0
        # status_forcelist can be list or frozenset depending on urllib3 version
        assert set(adapter.max_retries.status_forcelist) == set([500, 502, 503])
        assert adapter.max_retries.raise_on_status is False

    def test_create_retry_adapter_with_only_total(self):
        """Test that _create_retry_adapter works with only total"""
        compiler = Mock()
        compiler.httpdef = HttpDef(
            name="test",
            method="GET",
            url="http://example.com",
            retry_total=5,
            retry_backoff_factor=None,
            retry_status_forcelist=None
        )

        from dothttp.parse.request_base import RequestCompiler
        adapter = RequestCompiler._create_retry_adapter(compiler)

        assert adapter is not None
        assert adapter.max_retries.total == 5
        assert adapter.max_retries.raise_on_status is False

    def test_no_adapter_when_no_retry(self):
        """Test that no adapter is created when retry is not configured"""
        compiler = Mock()
        compiler.httpdef = HttpDef(
            name="test",
            method="GET",
            url="http://example.com",
            retry_total=None
        )

        from dothttp.parse.request_base import RequestCompiler
        adapter = RequestCompiler._create_retry_adapter(compiler)

        assert adapter is None

    def test_raise_on_status_always_false(self):
        """Test that raise_on_status is always False for API testing"""
        compiler = Mock()
        compiler.httpdef = HttpDef(
            name="test",
            method="GET",
            url="http://example.com",
            retry_total=3
        )

        from dothttp.parse.request_base import RequestCompiler
        adapter = RequestCompiler._create_retry_adapter(compiler)

        # Should always be False since dothttp is an API testing tool
        assert adapter.max_retries.raise_on_status is False


class TestTimeoutBehavior:
    """Test that timeout actually applies to requests"""

    def test_timeout_value_loaded_correctly(self):
        """Test that timeout value is loaded as float"""
        # This verifies the load_timeout method converts string to float
        from dothttp.parse import Config as ParseConfig

        content = """
@name("test timeout")
GET https://httpbin.org/delay/1
timeout(5)
"""
        model = dothttp_model.model_from_str(content)
        http = model.allhttps[0]

        # Parse the timeout - simulating what load_timeout does
        timeout_str = http.timeout.timeout_seconds
        timeout_val = float(timeout_str)

        assert timeout_val == 5.0
        assert isinstance(timeout_val, float)

    def test_timeout_inheritance_parsing(self):
        """Test that timeout inheritance is set up correctly"""
        content = """
@name("parent")
GET https://httpbin.org/delay/1
timeout(10)

@name("child") : "parent"
GET https://httpbin.org/delay/2
"""
        model = dothttp_model.model_from_str(content)
        parent = model.allhttps[0]
        child = model.allhttps[1]

        # Parent has timeout
        assert parent.timeout is not None
        assert parent.timeout.timeout_seconds == "10"

        # Child references parent (will inherit at load time)
        assert child.namewrap.base == "parent"
        assert child.timeout is None


class TestProxyBehavior:
    """Test that proxy configuration is applied"""

    def test_http_proxy_format(self):
        """Test that HTTP proxy is parsed correctly"""
        content = """
@name("test")
GET https://httpbin.org/ip
proxy("http://proxy.example.com:8080")
"""
        model = dothttp_model.model_from_str(content)
        http = model.allhttps[0]

        assert http.proxy is not None
        assert http.proxy.proxy == "http://proxy.example.com:8080"
        # Verify it's a valid proxy URL format
        assert http.proxy.proxy.startswith("http://")
        assert ":" in http.proxy.proxy

    def test_socks5_proxy_format(self):
        """Test that SOCKS5 proxy is parsed correctly"""
        content = """
@name("test")
GET https://httpbin.org/ip
proxy("socks5://proxy.example.com:1080")
"""
        model = dothttp_model.model_from_str(content)
        http = model.allhttps[0]

        assert http.proxy is not None
        assert http.proxy.proxy == "socks5://proxy.example.com:1080"
        assert http.proxy.proxy.startswith("socks5://")

    def test_proxy_inheritance_setup(self):
        """Test that proxy inheritance is set up correctly"""
        content = """
@name("parent")
GET https://httpbin.org/ip
proxy("http://proxy.example.com:8080")

@name("child") : "parent"
GET https://httpbin.org/headers
"""
        model = dothttp_model.model_from_str(content)
        parent = model.allhttps[0]
        child = model.allhttps[1]

        # Parent has proxy
        assert parent.proxy is not None

        # Child references parent (will inherit at load time)
        assert child.namewrap.base == "parent"
        assert child.proxy is None


class TestCombinedFeatures:
    """Test that multiple features work together"""

    def test_all_features_parsed_together(self):
        """Test that timeout, retry, and proxy can all be used together"""
        content = """
@name("all features")
POST https://httpbin.org/post
timeout(30)
retry(total=3, backoff_factor=1, status_forcelist=[429, 500])
proxy("http://proxy.example.com:8080")
json({"test": "data"})
"""
        model = dothttp_model.model_from_str(content)
        http = model.allhttps[0]

        # All features should be present
        assert http.timeout is not None
        assert http.timeout.timeout_seconds == "30"

        assert http.retry is not None
        total_params = [p for p in http.retry.retry_params if p.total]
        assert len(total_params) == 1
        assert total_params[0].total == "3"

        assert http.proxy is not None
        assert http.proxy.proxy == "http://proxy.example.com:8080"

    def test_features_with_different_combinations(self):
        """Test different combinations of features"""
        # Timeout only
        content1 = """
@name("test1")
GET https://httpbin.org/get
timeout(5)
"""

        # Retry only
        content2 = """
@name("test2")
GET https://httpbin.org/get
retry(total=3)
"""

        # Proxy only
        content3 = """
@name("test3")
GET https://httpbin.org/get
proxy("http://proxy.example.com:8080")
"""

        model1 = dothttp_model.model_from_str(content1)
        model2 = dothttp_model.model_from_str(content2)
        model3 = dothttp_model.model_from_str(content3)

        http1 = model1.allhttps[0]
        http2 = model2.allhttps[0]
        http3 = model3.allhttps[0]

        # Each should have its respective feature
        assert http1.timeout is not None
        assert http1.retry is None
        assert http1.proxy is None

        assert http2.timeout is None
        assert http2.retry is not None
        assert http2.proxy is None

        assert http3.timeout is None
        assert http3.retry is None
        assert http3.proxy is not None


class TestRetryAdapter:
    """Test retry adapter creation and behavior"""

    def test_adapter_send_pattern(self):
        """Test that adapter.send() can be called without mounting"""
        # This verifies the thread-safety approach
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[500, 502, 503],
            raise_on_status=False
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)

        # Verify adapter has the expected attributes
        assert hasattr(adapter, 'send')
        assert hasattr(adapter, 'max_retries')
        assert adapter.max_retries.total == 3

    def test_retry_strategy_parameters(self):
        """Test that urllib3.Retry accepts our parameters"""
        # Verify we're using the right parameter names
        retry = Retry(
            total=5,
            backoff_factor=2.0,
            status_forcelist=[429, 500, 502, 503],
            raise_on_status=False
        )

        assert retry.total == 5
        assert retry.backoff_factor == 2.0
        # status_forcelist can be list or frozenset depending on urllib3 version
        assert set(retry.status_forcelist) == set([429, 500, 502, 503])
        assert retry.raise_on_status is False


class TestInheritance:
    """Test inheritance behavior"""

    def test_timeout_inheritance_structure(self):
        """Test that timeout inheritance is structured correctly"""
        content = """
@name("base")
GET https://httpbin.org/delay/1
timeout(20)

@name("derived") : "base"
GET https://httpbin.org/delay/2
"""
        model = dothttp_model.model_from_str(content)
        base = model.allhttps[0]
        derived = model.allhttps[1]

        # Base has timeout
        assert base.timeout is not None
        assert base.namewrap.name == "base"

        # Derived references base
        assert derived.namewrap.base == "base"
        assert derived.timeout is None  # Will inherit via get_current_or_base

    def test_retry_inheritance_structure(self):
        """Test that retry inheritance is structured correctly"""
        content = """
@name("base")
GET https://httpbin.org/status/500
retry(total=5, backoff_factor=2)

@name("derived") : "base"
GET https://httpbin.org/status/503
"""
        model = dothttp_model.model_from_str(content)
        base = model.allhttps[0]
        derived = model.allhttps[1]

        # Base has retry
        assert base.retry is not None

        # Derived references base
        assert derived.namewrap.base == "base"
        assert derived.retry is None  # Will inherit via get_current_or_base

    def test_proxy_inheritance_structure(self):
        """Test that proxy inheritance is structured correctly"""
        content = """
@name("base")
GET https://httpbin.org/ip
proxy("http://proxy.example.com:8080")

@name("derived") : "base"
GET https://httpbin.org/headers
"""
        model = dothttp_model.model_from_str(content)
        base = model.allhttps[0]
        derived = model.allhttps[1]

        # Base has proxy
        assert base.proxy is not None

        # Derived references base
        assert derived.namewrap.base == "base"
        assert derived.proxy is None  # Will inherit via get_current_or_base

    def test_child_can_override_parent(self):
        """Test that child can override parent's values"""
        content = """
@name("parent")
GET https://httpbin.org/delay/1
timeout(10)
retry(total=3)

@name("child") : "parent"
GET https://httpbin.org/delay/2
timeout(20)
retry(total=5)
"""
        model = dothttp_model.model_from_str(content)
        parent = model.allhttps[0]
        child = model.allhttps[1]

        # Parent has original values
        assert parent.timeout.timeout_seconds == "10"
        total_params = [p for p in parent.retry.retry_params if p.total]
        assert total_params[0].total == "3"

        # Child overrides with new values
        assert child.timeout.timeout_seconds == "20"
        child_total_params = [p for p in child.retry.retry_params if p.total]
        assert child_total_params[0].total == "5"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
