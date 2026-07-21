"""
Validators for binary file uploads.
"""
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _


class FileSizeValidator:
    """
    Validate that uploaded file size does not exceed maximum limit.
    """
    def __init__(self, max_size_mb: int = 10):
        self.max_size_mb = max_size_mb
        self.max_size_bytes = max_size_mb * 1024 * 1024
    
    def __call__(self, file_data: bytes):
        if len(file_data) > self.max_size_bytes:
            raise ValidationError(
                _('File size exceeds maximum limit of %(max_size_mb)dMB.'),
                params={'max_size_mb': self.max_size_mb},
                code='file_too_large'
            )


class ContentTypeValidator:
    """
    Validate that file content type is in allowed list.
    """
    def __init__(self, allowed_types: list):
        self.allowed_types = allowed_types
    
    def __call__(self, content_type: str):
        if content_type not in self.allowed_types:
            raise ValidationError(
                _('File type %(content_type)s is not allowed. Allowed types: %(allowed_types)s.'),
                params={
                    'content_type': content_type,
                    'allowed_types': ', '.join(self.allowed_types)
                },
                code='invalid_content_type'
            )


class PDFValidator:
    """
    Validate that file is a PDF document.
    """
    ALLOWED_TYPES = ['application/pdf']
    
    def __call__(self, content_type: str, file_data: bytes = None):
        if content_type not in self.ALLOWED_TYPES:
            raise ValidationError(
                _('Only PDF files are allowed.'),
                code='invalid_pdf'
            )
        
        # Optional: Validate PDF magic bytes
        if file_data and not file_data.startswith(b'%PDF'):
            raise ValidationError(
                _('File is not a valid PDF document.'),
                code='invalid_pdf_format'
            )


class ImageValidator:
    """
    Validate that file is an image.
    """
    ALLOWED_TYPES = [
        'image/jpeg',
        'image/jpg',
        'image/png',
        'image/gif',
        'image/webp'
    ]
    
    def __call__(self, content_type: str, file_data: bytes = None):
        if content_type not in self.ALLOWED_TYPES:
            raise ValidationError(
                _('Only image files (JPEG, PNG, GIF, WebP) are allowed.'),
                code='invalid_image'
            )
        
        # Optional: Validate image magic bytes
        if file_data:
            if content_type in ['image/jpeg', 'image/jpg'] and not file_data.startswith(b'\xff\xd8'):
                raise ValidationError(
                    _('File is not a valid JPEG image.'),
                    code='invalid_jpeg'
                )
            elif content_type == 'image/png' and not file_data.startswith(b'\x89PNG'):
                raise ValidationError(
                    _('File is not a valid PNG image.'),
                    code='invalid_png'
                )
            elif content_type == 'image/gif' and not file_data.startswith(b'GIF8'):
                raise ValidationError(
                    _('File is not a valid GIF image.'),
                    code='invalid_gif'
                )


class FilenameValidator:
    """
    Validate that filename is safe and doesn't contain path traversal characters.
    """
    def __call__(self, filename: str):
        if not filename:
            raise ValidationError(
                _('Filename cannot be empty.'),
                code='empty_filename'
            )
        
        # Check for path traversal attempts
        if '..' in filename or filename.startswith('/') or filename.startswith('\\'):
            raise ValidationError(
                _('Filename contains invalid characters.'),
                code='invalid_filename'
            )
        
        # Check for null bytes
        if '\x00' in filename:
            raise ValidationError(
                _('Filename contains invalid characters.'),
                code='invalid_filename'
            )
