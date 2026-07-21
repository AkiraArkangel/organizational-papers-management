-- Migration 0023: Remove FileField columns and add BinaryField columns
-- Run this SQL directly on your PostgreSQL database

BEGIN;

-- Remove old FileField columns from documents_document
ALTER TABLE documents_document DROP COLUMN IF EXISTS corrected_file;
ALTER TABLE documents_document DROP COLUMN IF EXISTS uploaded_file;

-- Remove old FileField columns from documents_filesectiontemplate
ALTER TABLE documents_filesectiontemplate DROP COLUMN IF EXISTS template_file;

-- Remove old FileField columns from documents_organizationofficer
ALTER TABLE documents_organizationofficer DROP COLUMN IF EXISTS photo;

-- Remove old FileField columns from documents_organizationprofile
ALTER TABLE documents_organizationprofile DROP COLUMN IF EXISTS logo;

-- Remove old FileField columns from documents_signedscannedcopy
ALTER TABLE documents_signedscannedcopy DROP COLUMN IF EXISTS signed_file;

-- Add new BinaryField and metadata columns to documents_document
ALTER TABLE documents_document ADD COLUMN IF NOT EXISTS corrected_file_checksum VARCHAR(64);
ALTER TABLE documents_document ADD COLUMN IF NOT EXISTS corrected_file_content_type VARCHAR(100);
ALTER TABLE documents_document ADD COLUMN IF NOT EXISTS corrected_file_data BYTEA;
ALTER TABLE documents_document ADD COLUMN IF NOT EXISTS corrected_file_name VARCHAR(255);
ALTER TABLE documents_document ADD COLUMN IF NOT EXISTS corrected_file_size BIGINT;
ALTER TABLE documents_document ADD COLUMN IF NOT EXISTS corrected_file_uploaded_at TIMESTAMP;
ALTER TABLE documents_document ADD COLUMN IF NOT EXISTS corrected_file_uploaded_by_id INTEGER REFERENCES auth_user(id) ON DELETE SET NULL;

ALTER TABLE documents_document ADD COLUMN IF NOT EXISTS uploaded_file_checksum VARCHAR(64);
ALTER TABLE documents_document ADD COLUMN IF NOT EXISTS uploaded_file_content_type VARCHAR(100);
ALTER TABLE documents_document ADD COLUMN IF NOT EXISTS uploaded_file_data BYTEA;
ALTER TABLE documents_document ADD COLUMN IF NOT EXISTS uploaded_file_name VARCHAR(255);
ALTER TABLE documents_document ADD COLUMN IF NOT EXISTS uploaded_file_size BIGINT;

-- Add new BinaryField and metadata columns to documents_filesectiontemplate
ALTER TABLE documents_filesectiontemplate ADD COLUMN IF NOT EXISTS template_file_checksum VARCHAR(64);
ALTER TABLE documents_filesectiontemplate ADD COLUMN IF NOT EXISTS template_file_content_type VARCHAR(100);
ALTER TABLE documents_filesectiontemplate ADD COLUMN IF NOT EXISTS template_file_data BYTEA;
ALTER TABLE documents_filesectiontemplate ADD COLUMN IF NOT EXISTS template_file_name VARCHAR(255);
ALTER TABLE documents_filesectiontemplate ADD COLUMN IF NOT EXISTS template_file_size BIGINT;

-- Add new BinaryField and metadata columns to documents_organizationofficer
ALTER TABLE documents_organizationofficer ADD COLUMN IF NOT EXISTS photo_checksum VARCHAR(64);
ALTER TABLE documents_organizationofficer ADD COLUMN IF NOT EXISTS photo_content_type VARCHAR(100);
ALTER TABLE documents_organizationofficer ADD COLUMN IF NOT EXISTS photo_data BYTEA;
ALTER TABLE documents_organizationofficer ADD COLUMN IF NOT EXISTS photo_name VARCHAR(255);
ALTER TABLE documents_organizationofficer ADD COLUMN IF NOT EXISTS photo_size BIGINT;
ALTER TABLE documents_organizationofficer ADD COLUMN IF NOT EXISTS photo_uploaded_at TIMESTAMP;
ALTER TABLE documents_organizationofficer ADD COLUMN IF NOT EXISTS photo_uploaded_by_id INTEGER REFERENCES auth_user(id) ON DELETE SET NULL;

-- Add new BinaryField and metadata columns to documents_organizationprofile
ALTER TABLE documents_organizationprofile ADD COLUMN IF NOT EXISTS logo_checksum VARCHAR(64);
ALTER TABLE documents_organizationprofile ADD COLUMN IF NOT EXISTS logo_content_type VARCHAR(100);
ALTER TABLE documents_organizationprofile ADD COLUMN IF NOT EXISTS logo_data BYTEA;
ALTER TABLE documents_organizationprofile ADD COLUMN IF NOT EXISTS logo_name VARCHAR(255);
ALTER TABLE documents_organizationprofile ADD COLUMN IF NOT EXISTS logo_size BIGINT;
ALTER TABLE documents_organizationprofile ADD COLUMN IF NOT EXISTS logo_uploaded_at TIMESTAMP;
ALTER TABLE documents_organizationprofile ADD COLUMN IF NOT EXISTS logo_uploaded_by_id INTEGER REFERENCES auth_user(id) ON DELETE SET NULL;

-- Add new BinaryField and metadata columns to documents_signedscannedcopy
ALTER TABLE documents_signedscannedcopy ADD COLUMN IF NOT EXISTS signed_file_checksum VARCHAR(64);
ALTER TABLE documents_signedscannedcopy ADD COLUMN IF NOT EXISTS signed_file_content_type VARCHAR(100);
ALTER TABLE documents_signedscannedcopy ADD COLUMN IF NOT EXISTS signed_file_data BYTEA;
ALTER TABLE documents_signedscannedcopy ADD COLUMN IF NOT EXISTS signed_file_name VARCHAR(255);
ALTER TABLE documents_signedscannedcopy ADD COLUMN IF NOT EXISTS signed_file_size BIGINT;

-- Record the migration in Django's migration table
INSERT INTO django_migrations (app, name, applied) 
VALUES ('documents', '0023_remove_document_corrected_file_and_more', NOW())
ON CONFLICT (app, name) DO NOTHING;

COMMIT;
