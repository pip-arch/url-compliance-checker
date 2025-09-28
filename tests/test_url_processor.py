"""
Tests for the URL processor module.
"""
import pytest
from app.core.url_processor import URLProcessor
from app.models.url import URL, URLStatus, URLFilterReason


def test_filter_urls():
    """
    Test URL filtering functionality.
    """
    # Create a processor
    processor = URLProcessor()
    
    # Create test URLs
    urls = [
        URL(id="1", url="https://example.com/admiralmarkets", batch_id="test"),
        URL(id="2", url="https://admiralmarkets.com/about", batch_id="test"),
        URL(id="3", url="https://cysec.gov.cy/licensed-providers", batch_id="test"),
        URL(id="4", url="not-a-valid-url", batch_id="test"),
    ]
    
    # Filter URLs
    filtered = processor.filter_urls(urls)
    
    # Check results
    assert len(filtered) == 1
    assert filtered[0].id == "1"
    
    # Check statuses
    assert urls[0].status == URLStatus.PENDING
    assert urls[1].status == URLStatus.SKIPPED
    assert urls[1].filter_reason == URLFilterReason.OWN_DOMAIN
    assert urls[2].status == URLStatus.SKIPPED
    assert urls[2].filter_reason == URLFilterReason.REGULATOR
    assert urls[3].status == URLStatus.SKIPPED
    assert urls[3].filter_reason == URLFilterReason.INVALID_URL


def test_extract_content():
    """
    Test content extraction functionality.
    """
    # Create a processor
    processor = URLProcessor()
    
    # Test content with mentions
    content = {
        "url": "https://example.com",
        "title": "Test Title",
        "full_text": "This is text before mentioning admiralmarkets in a sentence. This is text after."
    }
    
    # Extract content
    url_content = processor.extract_content(content, "https://example.com")
    
    # Check results
    assert url_content.url == "https://example.com"
    assert url_content.title == "Test Title"
    assert len(url_content.mentions) == 1
    assert "admiralmarkets" in url_content.mentions[0].text.lower()
    assert "text before mentioning" in url_content.mentions[0].context_before
    assert "in a sentence. This is text after" in url_content.mentions[0].context_after
    
    # Test content without mentions
    content = {
        "url": "https://example.com",
        "title": "Test Title",
        "full_text": "This text does not mention the broker."
    }
    
    # Extract content
    url_content = processor.extract_content(content, "https://example.com")
    
    # Check results
    assert len(url_content.mentions) == 0 