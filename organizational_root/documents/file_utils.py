"""
Utility functions for handling binary file storage in PostgreSQL.
"""
import hashlib
from io import BytesIO
from typing import Tuple, Optional


def calculate_sha256_checksum(file_data: bytes) -> str:
    """
    Calculate SHA-256 checksum of binary data.
    
    Args:
        file_data: Binary file data
        
    Returns:
        Hexadecimal SHA-256 checksum string
    """
    return hashlib.sha256(file_data).hexdigest()


def validate_file_size(file_data: bytes, max_size_mb: int = 10) -> bool:
    """
    Validate file size does not exceed maximum limit.
    
    Args:
        file_data: Binary file data
        max_size_mb: Maximum file size in megabytes
        
    Returns:
        True if file size is within limit, False otherwise
    """
    max_size_bytes = max_size_mb * 1024 * 1024
    return len(file_data) <= max_size_bytes


def extract_file_metadata(uploaded_file, max_size_mb: int = 10) -> Tuple[bytes, str, str, int, str]:
    """
    Extract binary data and metadata from uploaded file.
    
    Args:
        uploaded_file: Django UploadedFile object
        max_size_mb: Maximum file size in megabytes
        
    Returns:
        Tuple of (file_data, filename, content_type, file_size, checksum)
        
    Raises:
        ValueError: If file size exceeds limit
    """
    # Read file data
    uploaded_file.seek(0)
    file_data = uploaded_file.read()
    
    # Validate file size
    if not validate_file_size(file_data, max_size_mb):
        raise ValueError(f'File size exceeds maximum limit of {max_size_mb}MB')
    
    # Extract metadata
    filename = uploaded_file.name
    content_type = uploaded_file.content_type or 'application/octet-stream'
    file_size = len(file_data)
    checksum = calculate_sha256_checksum(file_data)
    
    return file_data, filename, content_type, file_size, checksum


def create_file_response(file_data: bytes, filename: str, content_type: str) -> BytesIO:
    """
    Create a file-like object from binary data for response.
    
    Args:
        file_data: Binary file data
        filename: Original filename
        content_type: MIME content type
        
    Returns:
        BytesIO object containing the file data
    """
    return BytesIO(file_data)


def get_safe_filename(filename: str) -> str:
    """
    Sanitize filename to prevent path traversal attacks.
    
    Args:
        filename: Original filename
        
    Returns:
        Sanitized filename
    """
    # Remove path components
    filename = filename.replace('\\', '/').split('/')[-1]
    
    # Remove potentially dangerous characters
    dangerous_chars = ['..', '\0', '<', '>', ':', '"', '|', '?', '*']
    for char in dangerous_chars:
        filename = filename.replace(char, '')
    
    return filename


def validate_content_type(content_type: str, allowed_types: list) -> bool:
    """
    Validate content type against allowed types.
    
    Args:
        content_type: MIME content type
        allowed_types: List of allowed content types
        
    Returns:
        True if content type is allowed, False otherwise
    """
    return content_type in allowed_types
