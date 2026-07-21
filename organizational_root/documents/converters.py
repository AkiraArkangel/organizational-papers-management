import shutil
import subprocess
import tempfile
from pathlib import Path

from django.core.files.base import ContentFile
from django.core.files.uploadedfile import UploadedFile


class ConversionError(Exception):
    pass


def _converter_command():
    command = shutil.which('soffice') or shutil.which('libreoffice')
    if not command:
        raise ConversionError(
            'Document conversion needs LibreOffice or soffice installed on the server.'
        )
    return command


def _run_libreoffice(input_path, output_ext):
    input_path = Path(input_path)
    output_ext = output_ext.lstrip('.')
    output_dir = Path(tempfile.mkdtemp(prefix='orgsys-convert-'))

    command = [
        _converter_command(),
        '--headless',
        '--convert-to',
        output_ext,
        '--outdir',
        str(output_dir),
        str(input_path),
    ]
    result = subprocess.run(command, capture_output=True, text=True, timeout=120)
    if result.returncode != 0:
        detail = (result.stderr or result.stdout or '').strip()
        raise ConversionError(f'Could not convert {input_path.name}. {detail}'.strip())

    converted_path = output_dir / f'{input_path.stem}.{output_ext}'
    if not converted_path.exists():
        matches = list(output_dir.glob(f'*.{output_ext}'))
        if not matches:
            raise ConversionError(f'Could not create a .{output_ext} file from {input_path.name}.')
        converted_path = matches[0]

    return converted_path


def convert_pdf_path_to_docx(pdf_path):
    # This function is deprecated for binary storage
    # Use convert_pdf_binary_to_docx instead
    raise ConversionError('PDF to DOCX conversion from file path is deprecated. Use convert_pdf_binary_to_docx for binary data.')


def convert_pdf_binary_to_docx(pdf_binary_data, filename):
    """Convert PDF binary data to DOCX binary data"""
    if not pdf_binary_data:
        raise ConversionError('No PDF data provided for conversion.')
    
    original_name = Path(filename)
    with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as temp_file:
        temp_file.write(pdf_binary_data)
        source_path = Path(temp_file.name)

    try:
        converted_path = _run_libreoffice(source_path, 'docx')
        converted_content = converted_path.read_bytes()
        source_path.unlink(missing_ok=True)
        shutil.rmtree(converted_path.parent, ignore_errors=True)
        return converted_content, f'{original_name.stem}.docx'
    except Exception as e:
        source_path.unlink(missing_ok=True)
        raise ConversionError(f'Failed to convert PDF to DOCX: {str(e)}')


def convert_uploaded_docx_to_pdf(uploaded_file):
    if not isinstance(uploaded_file, UploadedFile):
        return uploaded_file

    original_name = Path(uploaded_file.name)
    if original_name.suffix.lower() != '.docx':
        return uploaded_file

    with tempfile.NamedTemporaryFile(suffix='.docx', delete=False) as temp_file:
        for chunk in uploaded_file.chunks():
            temp_file.write(chunk)
        source_path = Path(temp_file.name)

    converted_path = _run_libreoffice(source_path, 'pdf')
    converted_content = converted_path.read_bytes()
    source_path.unlink(missing_ok=True)
    shutil.rmtree(converted_path.parent, ignore_errors=True)
    return ContentFile(converted_content, name=f'{original_name.stem}.pdf')


def convert_docx_binary_to_pdf(docx_binary_data, filename):
    """Convert DOCX binary data to PDF binary data"""
    if not docx_binary_data:
        raise ConversionError('No DOCX data provided for conversion.')
    
    original_name = Path(filename)
    with tempfile.NamedTemporaryFile(suffix='.docx', delete=False) as temp_file:
        temp_file.write(docx_binary_data)
        source_path = Path(temp_file.name)

    try:
        converted_path = _run_libreoffice(source_path, 'pdf')
        converted_content = converted_path.read_bytes()
        source_path.unlink(missing_ok=True)
        shutil.rmtree(converted_path.parent, ignore_errors=True)
        return converted_content, f'{original_name.stem}.pdf'
    except Exception as e:
        source_path.unlink(missing_ok=True)
        raise ConversionError(f'Failed to convert DOCX to PDF: {str(e)}')


def docx_download_name(filename):
    return f'{Path(filename).stem}.docx'
