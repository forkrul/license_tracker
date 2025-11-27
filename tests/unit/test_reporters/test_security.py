"""Tests for the Markdown reporter."""
import pytest

from license_tracker.models import LicenseLink, PackageMetadata
from license_tracker.reporters.markdown import MarkdownReporter


@pytest.fixture
def reporter():
    """Create a MarkdownReporter instance."""
    return MarkdownReporter()


def test_xss_protection_with_autoescape(reporter):
    """Test that package metadata with HTML is properly escaped."""
    xss_package = PackageMetadata(
        name='<script>alert("xss")</script>',
        version="1.0.0",
        description="<script>alert('xss')</script>",
        homepage="https://example.com/<script>alert('xss')</script>",
        repository_url="https://github.com/user/<script>alert('xss')</script>",
        author="<script>alert('xss')</script>",
        licenses=[
            LicenseLink(
                spdx_id="MIT",
                name='<script>alert("xss")</script>',
                url="https://example.com/<script>alert('xss')</script>",
                is_verified_file=False,
            )
        ],
    )

    output = reporter.render([xss_package])

    # Check that the HTML is escaped
    assert "&lt;script&gt;alert(&#34;xss&#34;)&lt;/script&gt;" in output

    # Check that the raw HTML is not present
    assert '<script>alert("xss")</script>' not in output
