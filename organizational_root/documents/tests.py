import shutil
import tempfile
from datetime import timedelta
from pathlib import Path
from unittest.mock import patch

from django.conf import settings
from django.contrib.auth.models import User
from django.core.files.base import ContentFile
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from .forms import AccountRegisterForm, AdminDocumentForm
from .models import (
    AdminProfile,
    AdviserProfile,
    Document,
    FileSectionTemplate,
    OrganizationOfficer,
    OrganizationProfile,
    SubmissionFolder,
)


TEST_MEDIA_ROOT = tempfile.mkdtemp()


@override_settings(MEDIA_ROOT=TEST_MEDIA_ROOT)
class AdminDocumentEditTests(TestCase):
    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEST_MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        self.admin = User.objects.create_user(
            username='admin',
            password='password12345',
            is_staff=True,
        )
        self.admin_profile = AdminProfile.objects.create(
            user=self.admin,
            rank=AdminProfile.RANK_2,
        )
        self.rank1_admin = User.objects.create_user(
            username='rank1',
            password='password12345',
            is_staff=True,
        )
        self.rank1_profile = AdminProfile.objects.create(
            user=self.rank1_admin,
            rank=AdminProfile.RANK_1,
        )
        self.organization = User.objects.create_user(
            username='org',
            password='password12345',
        )
        self.organization_profile = OrganizationProfile.objects.create(
            user=self.organization,
            organization_name='Organization One',
        )
        self.adviser = User.objects.create_user(
            username='adviser',
            password='password12345',
        )
        self.adviser_profile = AdviserProfile.objects.create(
            user=self.adviser,
            organization=self.organization_profile,
        )

    def create_document(self, status='SUBMITTED', user=None, forwarded=True, **kwargs):
        title = kwargs.pop('title', 'Original Title')
        folder = kwargs.pop('folder', None)
        document = Document.objects.create(
            user=user or self.organization,
            title=title,
            uploaded_file='uploads/original.pdf',
            status=status,
            adviser_status='APPROVED' if forwarded else 'PENDING',
            forwarded_to_admin_at=timezone.now() if forwarded else None,
            **kwargs,
        )
        if folder is None:
            folder = SubmissionFolder.objects.create(
                user=document.user,
                section=document.section,
                name=title,
                forwarded_to_admin_at=document.forwarded_to_admin_at,
                admin_notification_seen_at=document.admin_notification_seen_at,
                rank2_reviewed_by=document.rank2_reviewed_by,
                forwarded_to_rank1_at=document.forwarded_to_rank1_at,
                rank1_notification_seen_at=document.rank1_notification_seen_at,
            )
        document.folder = folder
        document.save(update_fields=['folder'])
        return document

    def create_document_with_files(self, status='SUBMITTED', **kwargs):
        document = self.create_document(status=status, **kwargs)
        document.uploaded_file.save('original.pdf', ContentFile(b'%PDF-1.4\n'), save=False)
        document.save()
        return document

    def test_admin_form_uses_notes_and_ready_fields(self):
        form = AdminDocumentForm(
            instance=self.create_document(),
            admin_rank=AdminProfile.RANK_1,
        )

        self.assertEqual(list(form.fields), ['correction_notes', 'review_file', 'ready_for_printing'])
        self.assertNotIn('title', form.fields)
        self.assertNotIn('corrected_file', form.fields)

    def test_admin_save_marks_submitted_document_as_corrected_and_saves_notes(self):
        document = self.create_document_with_files(status='SUBMITTED')
        form = AdminDocumentForm(
            {'correction_notes': 'Fix page 2 heading.'},
            instance=document,
        )

        self.assertTrue(form.is_valid())
        form.save()
        document.refresh_from_db()

        self.assertEqual(document.title, 'Original Title')
        self.assertEqual(document.status, 'CORRECTED')
        self.assertEqual(document.correction_notes, 'Fix page 2 heading.')
        self.assertFalse(document.corrected_file)

    def test_admin_save_marks_resubmitted_document_as_corrected(self):
        document = self.create_document_with_files(status='RESUBMITTED')
        form = AdminDocumentForm(
            {'correction_notes': 'Use the correct signatory.'},
            instance=document,
        )

        self.assertTrue(form.is_valid())
        form.save()
        document.refresh_from_db()

        self.assertEqual(document.status, 'CORRECTED')

    def test_admin_can_mark_document_ready_for_printing(self):
        document = self.create_document_with_files(status='CORRECTED')
        form = AdminDocumentForm(
            {
                'correction_notes': '',
                'ready_for_printing': 'on',
            },
            instance=document,
            admin_rank=AdminProfile.RANK_1,
        )

        self.assertTrue(form.is_valid())
        form.save()
        document.refresh_from_db()

        self.assertEqual(document.status, 'READY_FOR_PRINTING')

    def test_ready_for_printing_checkbox_is_not_checked_by_default(self):
        document = self.create_document_with_files(status='READY_FOR_PRINTING')
        form = AdminDocumentForm(instance=document)

        self.assertFalse(form.fields['ready_for_printing'].initial)

    def test_admin_edit_view_saves_corrections_without_uploaded_file(self):
        document = self.create_document_with_files(status='SUBMITTED')
        self.client.force_login(self.admin)

        response = self.client.post(
            reverse('admin_edit_document', args=[document.id]),
            {
                'correction_notes': 'Correct the activity date.',
                'corrected_file': SimpleUploadedFile(
                    'new-correction.pdf',
                    b'not used',
                    content_type='application/pdf',
                ),
            },
        )
        document.refresh_from_db()

        self.assertRedirects(response, reverse('admin_dashboard'))
        self.assertEqual(document.title, 'Original Title')
        self.assertEqual(document.status, 'CORRECTED')
        self.assertEqual(document.correction_notes, 'Correct the activity date.')
        self.assertEqual(document.correction_reviewed_by, self.admin)
        self.assertFalse(document.corrected_file)

    def test_admin_edit_view_replaces_pdf_and_marks_corrected(self):
        document = self.create_document_with_files(status='SUBMITTED')
        self.client.force_login(self.admin)

        response = self.client.post(
            reverse('admin_edit_document', args=[document.id]),
            {
                'correction_notes': 'Added comments to the PDF.',
                'review_file': SimpleUploadedFile(
                    'reviewed.pdf',
                    b'%PDF-1.4\nreviewed',
                    content_type='application/pdf',
                ),
            },
        )
        document.refresh_from_db()

        self.assertRedirects(response, reverse('admin_dashboard'))
        self.assertEqual(document.status, 'CORRECTED')
        self.assertEqual(document.correction_reviewed_by, self.admin)
        self.assertTrue(document.uploaded_file.name.endswith('.pdf'))
        self.assertIn('reviewed', document.uploaded_file.name)

    def test_organization_can_add_and_reorder_officers(self):
        self.client.force_login(self.organization)

        response = self.client.post(
            reverse('add_organization_officer'),
            {
                'position': 'President',
                'name': 'Avery Santos',
            },
        )
        self.assertRedirects(response, f'{reverse("dashboard")}#organization-overview')
        self.assertFalse(OrganizationOfficer.objects.get(position='President').photo)

        second = OrganizationOfficer.objects.create(
            organization=self.organization_profile,
            position='Secretary',
            name='Bea Cruz',
            display_order=1,
        )
        response = self.client.post(reverse('move_organization_officer', args=[second.id, 'up']))
        self.assertRedirects(response, f'{reverse("dashboard")}#organization-overview')

        officers = list(self.organization_profile.officers.values_list('position', flat=True))
        self.assertEqual(officers, ['Secretary', 'President'])

    def test_organization_can_add_officer_photo_later(self):
        officer = OrganizationOfficer.objects.create(
            organization=self.organization_profile,
            position='Vice President',
            name='Eli Ramos',
        )
        self.client.force_login(self.organization)

        response = self.client.post(
            reverse('update_organization_officer_photo', args=[officer.id]),
            {
                'photo': SimpleUploadedFile(
                    'vice-president.png',
                    b'image',
                    content_type='image/png',
                ),
            },
        )
        officer.refresh_from_db()

        self.assertRedirects(response, f'{reverse("dashboard")}#organization-overview')
        self.assertIn('vice-president', officer.photo.name)

    def test_organization_can_update_officer_name_and_position(self):
        officer = OrganizationOfficer.objects.create(
            organization=self.organization_profile,
            position='Old Position',
            name='Old Name',
        )
        self.client.force_login(self.organization)

        response = self.client.post(
            reverse('update_organization_officer', args=[officer.id]),
            {
                'position': 'President',
                'name': 'Avery Santos',
            },
        )
        officer.refresh_from_db()

        self.assertRedirects(response, f'{reverse("dashboard")}#organization-overview')
        self.assertEqual(officer.position, 'President')
        self.assertEqual(officer.name, 'Avery Santos')

    def test_organization_can_delete_officer_profile(self):
        officer = OrganizationOfficer.objects.create(
            organization=self.organization_profile,
            position='Auditor',
            name='Dev Lim',
        )
        self.client.force_login(self.organization)

        response = self.client.post(reverse('delete_organization_officer', args=[officer.id]))

        self.assertRedirects(response, f'{reverse("dashboard")}#organization-overview')
        self.assertFalse(OrganizationOfficer.objects.filter(pk=officer.pk).exists())

    def test_organization_can_upload_logo_and_adviser_sees_it(self):
        self.client.force_login(self.organization)

        response = self.client.post(
            reverse('update_organization_logo'),
            {
                'logo': SimpleUploadedFile(
                    'org-logo.png',
                    b'image',
                    content_type='image/png',
                ),
            },
        )
        self.organization_profile.refresh_from_db()

        self.assertRedirects(response, f'{reverse("dashboard")}#organization-overview')
        self.assertIn('org-logo', self.organization_profile.logo.name)

        self.client.force_login(self.adviser)
        adviser_response = self.client.get(reverse('adviser_dashboard'))
        self.assertContains(adviser_response, self.organization_profile.logo.url)

    def test_organization_overview_displays_officers_as_position_name_rows(self):
        OrganizationOfficer.objects.create(
            organization=self.organization_profile,
            position='Treasurer',
            name='Cai Reyes',
        )
        self.client.force_login(self.organization)

        response = self.client.get(reverse('organization_overview'))

        self.assertContains(response, 'Organization Overview')
        self.assertContains(response, 'Treasurer: Cai Reyes')
        self.assertContains(response, 'Add Position')
        self.assertContains(response, 'Add Photo')
        self.assertNotContains(response, 'Organization Acronym')

    def test_admin_organization_list_links_to_read_only_overview(self):
        OrganizationOfficer.objects.create(
            organization=self.organization_profile,
            position='Auditor',
            name='Dev Lim',
        )
        self.client.force_login(self.admin)

        response = self.client.get(reverse('admin_organizations_list'))
        self.assertContains(response, reverse('admin_organization_overview', args=[self.organization_profile.id]))

        overview_response = self.client.get(reverse('admin_organization_overview', args=[self.organization_profile.id]))
        self.assertContains(overview_response, 'Read-only Organization Overview')
        self.assertContains(overview_response, 'Auditor: Dev Lim')
        self.assertNotContains(overview_response, 'Add Position')

    def test_login_page_uses_account_id_and_account_type(self):
        response = self.client.get(reverse('login'))

        self.assertContains(response, 'Account type')
        self.assertContains(response, 'Account ID')
        self.assertContains(response, 'Register Account')
        self.assertNotContains(response, 'Organization Acronym, Adviser ID, or Admin ID')

    def test_login_rejects_mismatched_account_type(self):
        response = self.client.post(
            reverse('login'),
            {
                'account_type': 'admin',
                'username': 'org',
                'password': 'password12345',
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertNotIn('_auth_user_id', self.client.session)
        self.assertContains(response, 'The selected account type does not match this account.')

    def test_login_allows_matching_account_type(self):
        response = self.client.post(
            reverse('login'),
            {
                'account_type': 'organization',
                'username': 'org',
                'password': 'password12345',
            },
        )

        self.assertRedirects(response, reverse('dashboard'))

    def test_admin_save_resets_existing_checklist_when_notes_change(self):
        document = self.create_document_with_files(status='CORRECTED')
        document.correction_notes = 'Old item'
        document.correction_checklist_state = {'0': True}
        document.save()
        form = AdminDocumentForm(
            {'correction_notes': 'New item'},
            instance=document,
        )

        self.assertTrue(form.is_valid())
        form.save()
        document.refresh_from_db()

        self.assertEqual(document.correction_checklist_state, {})

    def test_admin_can_add_new_checklist_after_organization_resubmits(self):
        document = self.create_document_with_files(status='RESUBMITTED')
        form = AdminDocumentForm(
            {'correction_notes': 'Review the revised budget.'},
            instance=document,
        )

        self.assertTrue(form.is_valid())
        form.save()
        document.refresh_from_db()

        self.assertEqual(document.status, 'CORRECTED')
        self.assertEqual(document.correction_notes, 'Review the revised budget.')

    def test_admin_empty_review_keeps_resubmitted_status_until_checklist_is_added(self):
        document = self.create_document_with_files(status='RESUBMITTED')
        form = AdminDocumentForm(
            {'correction_notes': ''},
            instance=document,
        )

        self.assertTrue(form.is_valid())
        form.save()
        document.refresh_from_db()

        self.assertEqual(document.title, 'Original Title')
        self.assertEqual(document.status, 'RESUBMITTED')
        self.assertEqual(document.correction_notes, '')

    def test_completed_checklist_same_title_upload_marks_document_resubmitted(self):
        document = self.create_document_with_files(status='CORRECTED')
        document.correction_notes = 'Fix date\nUpdate signatory'
        document.correction_checklist_state = {'0': True, '1': True}
        document.save()
        self.client.force_login(self.organization)

        response = self.client.post(
            f'{reverse("upload")}?document={document.id}',
            {
                'uploaded_file': SimpleUploadedFile(
                    'revised.pdf',
                    b'%PDF-1.4\nrevised',
                    content_type='application/pdf',
                ),
            },
        )
        document.refresh_from_db()

        self.assertRedirects(response, reverse('dashboard'))
        self.assertEqual(Document.objects.filter(user=self.organization, section=document.section).count(), 1)
        self.assertEqual(document.title, 'Original Title')
        self.assertEqual(document.status, 'RESUBMITTED')
        self.assertEqual(document.correction_notes, 'Fix date\nUpdate signatory')
        self.assertEqual(document.correction_checklist_state, {})

    def test_same_title_resubmission_updates_submitted_time(self):
        document = self.create_document_with_files(status='CORRECTED')
        original_time = timezone.now() - timedelta(days=2)
        resubmitted_time = timezone.now()
        Document.objects.filter(pk=document.pk).update(uploaded_at=original_time)
        self.client.force_login(self.organization)

        with patch('documents.views.timezone.now', return_value=resubmitted_time):
            response = self.client.post(
                f'{reverse("upload")}?document={document.id}',
                {
                    'uploaded_file': SimpleUploadedFile(
                        'revised.pdf',
                        b'%PDF-1.4\nrevised',
                        content_type='application/pdf',
                    ),
                },
            )
        document.refresh_from_db()

        self.assertRedirects(response, reverse('dashboard'))
        self.assertEqual(document.status, 'RESUBMITTED')
        self.assertEqual(document.uploaded_at, resubmitted_time)

    def test_current_file_uses_organization_upload(self):
        document = self.create_document_with_files()
        document.corrected_file.save('corrected.pdf', ContentFile(b'%PDF-1.4\n'), save=True)

        self.assertTrue(document.current_filename().startswith('original'))
        self.assertTrue(document.current_filename().endswith('.pdf'))
        self.assertEqual(document.current_file_label(), 'Uploaded File')

    def test_admin_edit_page_uses_pdf_actions_without_embedded_preview(self):
        document = self.create_document_with_files()
        self.client.force_login(self.admin)

        response = self.client.get(reverse('admin_edit_document', args=[document.id]))

        self.assertNotContains(response, '<iframe', html=False)
        self.assertContains(response, 'Document details')
        self.assertContains(response, 'document-meta-grid')
        self.assertContains(response, 'Open PDF')
        self.assertContains(response, reverse('admin_view_document', args=[document.id]))
        self.assertContains(response, reverse('admin_download_document', args=[document.id]))

    def test_admin_submission_notification_is_not_repeated_after_seen(self):
        document = self.create_document_with_files(status='SUBMITTED')
        self.client.force_login(self.admin)

        first_response = self.client.get(reverse('admin_dashboard'))
        document.refresh_from_db()
        second_response = self.client.get(reverse('admin_dashboard'))

        self.assertContains(first_response, 'New File Submitted')
        self.assertIsNotNone(document.admin_notification_seen_at)
        self.assertNotContains(second_response, 'New File Submitted')

    def test_corrected_admin_document_does_not_trigger_notification(self):
        self.create_document_with_files(status='CORRECTED')
        self.client.force_login(self.admin)

        response = self.client.get(reverse('admin_dashboard'))

        self.assertNotContains(response, 'New File Submitted')

    def test_admin_dashboard_displays_checklist_items_as_bullets(self):
        document = self.create_document_with_files(status='CORRECTED')
        document.correction_notes = 'Fix page 2 heading.\n\nUpdate signatory.'
        document.save()
        self.client.force_login(self.admin)

        response = self.client.get(reverse('admin_dashboard'))

        self.assertContains(response, 'class="admin-checklist-summary"', html=False)
        self.assertContains(response, '<li>Fix page 2 heading.</li>', html=True)
        self.assertContains(response, '<li>Update signatory.</li>', html=True)

    def test_organization_cannot_update_correction_checklist_before_resubmitting(self):
        document = self.create_document_with_files(status='CORRECTED')
        document.correction_notes = 'Fix date\nUpdate signatory'
        document.save()
        self.client.force_login(self.organization)

        response = self.client.post(
            reverse('update_correction_checklist', args=[document.id]),
            {'completed_items': ['0']},
        )
        document.refresh_from_db()

        self.assertRedirects(response, reverse('dashboard'))
        self.assertEqual(document.correction_checklist_state, {})
        self.assertEqual(document.status, 'CORRECTED')

    def test_completed_checklist_before_resubmission_does_not_mark_document_ready_for_printing(self):
        document = self.create_document_with_files(status='CORRECTED')
        document.correction_notes = 'Fix date\nUpdate signatory'
        document.save()
        self.client.force_login(self.organization)

        response = self.client.post(
            reverse('update_correction_checklist', args=[document.id]),
            {'completed_items': ['0', '1']},
        )
        document.refresh_from_db()

        self.assertRedirects(response, reverse('dashboard'))
        self.assertEqual(document.correction_checklist_state, {})
        self.assertEqual(document.status, 'CORRECTED')

    def test_completed_checklist_does_not_change_existing_status(self):
        document = self.create_document_with_files(status='RESUBMITTED')
        document.correction_notes = 'Confirm the revised file.'
        document.save()
        self.client.force_login(self.organization)

        response = self.client.post(
            reverse('update_correction_checklist', args=[document.id]),
            {'completed_items': ['0']},
        )
        document.refresh_from_db()

        self.assertRedirects(response, reverse('dashboard'))
        self.assertEqual(document.correction_checklist_state, {'0': True})
        self.assertEqual(document.status, 'RESUBMITTED')

    def test_project_uses_philippine_time(self):
        self.assertEqual(settings.TIME_ZONE, 'Asia/Manila')

    def test_adviser_registration_requires_existing_organization(self):
        response = self.client.post(
            reverse('register'),
            {
                'account_type': 'adviser',
                'account_name': 'newadviser',
                'organization_name': '',
                'password': 'SnsuPass12345!',
                'password_confirm': 'SnsuPass12345!',
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(User.objects.filter(username='newadviser').exists())
        self.assertContains(response, 'Choose the organization this adviser represents.')

    def test_adviser_registration_creates_profile_for_selected_organization(self):
        response = self.client.post(
            reverse('register'),
            {
                'account_type': 'adviser',
                'account_name': 'newadviser',
                'adviser_organization': self.organization_profile.id,
                'password': 'SnsuPass12345!',
                'password_confirm': 'SnsuPass12345!',
            },
        )

        self.assertRedirects(response, reverse('login'))
        adviser = User.objects.get(username='newadviser')
        self.assertEqual(adviser.adviserprofile.organization, self.organization_profile)
        self.assertFalse(adviser.is_staff)

    def test_organization_upload_goes_to_adviser_before_admin(self):
        self.client.force_login(self.organization)

        response = self.client.post(
            reverse('upload'),
            {
                'section': 'REACCREDITATION_ACCREDITATION',
                'folder_name': 'Accreditation Visit',
                'uploaded_file': SimpleUploadedFile(
                    'accreditation.pdf',
                    b'%PDF-1.4\nnew',
                    content_type='application/pdf',
                ),
            },
        )

        document = Document.objects.get(section='REACCREDITATION_ACCREDITATION')
        self.assertRedirects(response, reverse('dashboard'))
        self.assertEqual(document.title, 'accreditation.pdf')
        self.assertEqual(document.folder.name, 'Accreditation Visit')
        self.assertEqual(document.section, 'REACCREDITATION_ACCREDITATION')
        self.assertEqual(document.status, 'SUBMITTED')
        self.assertEqual(document.adviser_status, 'PENDING')
        self.assertIsNone(document.forwarded_to_admin_at)

        self.client.force_login(self.admin)
        admin_response = self.client.get(reverse('admin_dashboard'))
        self.assertNotContains(admin_response, 'accreditation.pdf')

        self.client.force_login(self.adviser)
        adviser_response = self.client.get(reverse('adviser_dashboard'))
        self.assertContains(adviser_response, 'accreditation')

    def test_adviser_sees_only_their_organization_files(self):
        other_user = User.objects.create_user(username='other-org', password='password12345')
        OrganizationProfile.objects.create(user=other_user, organization_name='Other Organization')
        self.create_document_with_files(title='Owned File', forwarded=False)
        self.create_document_with_files(user=other_user, title='Other File', forwarded=False)
        self.client.force_login(self.adviser)

        response = self.client.get(reverse('adviser_dashboard'))

        self.assertContains(response, 'Organization One')
        self.assertNotContains(response, 'Other Organization')

    def test_adviser_can_approve_and_forward_file_to_admin(self):
        document = self.create_document_with_files(title='For Adviser', forwarded=False)
        self.client.force_login(self.adviser)

        response = self.client.post(
            reverse('adviser_edit_document', args=[document.id]),
            {
                'correction_notes': '',
                'approve_by_adviser': 'on',
            },
        )
        document.refresh_from_db()

        self.assertRedirects(response, reverse('adviser_dashboard'))
        self.assertEqual(document.adviser_status, 'APPROVED')
        self.assertIsNone(document.forwarded_to_admin_at)

        response = self.client.post(reverse('adviser_forward_document', args=[document.id]))
        document.refresh_from_db()

        self.assertRedirects(response, reverse('adviser_dashboard'))
        self.assertIsNotNone(document.forwarded_to_admin_at)

        self.client.force_login(self.admin)
        response = self.client.get(reverse('admin_dashboard'))
        self.assertContains(response, 'original')
        self.assertContains(response, 'Submitted')
        self.assertContains(response, 'Approved by Adviser')
        self.assertNotContains(response, 'Forward Folder to rank1')

        self.client.force_login(self.rank1_admin)
        rank1_response = self.client.get(reverse('admin_dashboard'))
        self.assertNotContains(rank1_response, 'original')

        self.client.force_login(self.admin)
        response = self.client.post(
            reverse('admin_edit_document', args=[document.id]),
            {
                'correction_notes': '',
                'approve_by_coi': 'on',
            },
        )
        document.refresh_from_db()

        self.assertRedirects(response, reverse('admin_dashboard'))
        self.assertEqual(document.status, 'APPROVED_BY_COI')

        response = self.client.post(reverse('rank2_forward_document', args=[document.id]))
        document.refresh_from_db()

        self.assertRedirects(response, reverse('admin_dashboard'))
        self.assertIsNotNone(document.forwarded_to_rank1_at)
        self.assertEqual(document.rank2_reviewed_by, self.admin)

        response = self.client.get(reverse('admin_dashboard'))
        self.assertContains(response, 'original')
        self.assertContains(response, 'Approved by admin')

        self.client.force_login(self.rank1_admin)
        rank1_response = self.client.get(reverse('admin_dashboard'))
        self.assertContains(rank1_response, 'original')
        self.assertContains(rank1_response, 'Forwarded by admin')
        self.assertContains(rank1_response, '<th>Corrections</th>', html=False)

    def test_rank1_correction_removes_forwarded_status_and_shows_corrector(self):
        document = self.create_document_with_files(
            status='SUBMITTED',
            rank2_reviewed_by=self.admin,
            forwarded_to_rank1_at=timezone.now(),
        )
        self.client.force_login(self.rank1_admin)

        response = self.client.post(
            reverse('admin_edit_document', args=[document.id]),
            {'correction_notes': 'Fix the signature block.'},
        )
        document.refresh_from_db()

        self.assertRedirects(response, reverse('admin_dashboard'))
        self.assertEqual(document.status, 'CORRECTED')
        self.assertEqual(document.correction_reviewed_by, self.rank1_admin)

        response = self.client.get(reverse('admin_dashboard'))
        self.assertContains(response, 'Corrected by rank1')
        self.assertContains(response, 'Fix the signature block.')
        self.assertNotContains(response, 'Forwarded by admin')

    def test_rank2_correction_is_hidden_from_rank1_dashboard(self):
        document = self.create_document_with_files(
            status='CORRECTED',
            rank2_reviewed_by=self.admin,
            forwarded_to_rank1_at=timezone.now(),
            correction_reviewed_by=self.admin,
        )
        document.correction_notes = 'Rank 2 internal correction.'
        document.save()
        self.client.force_login(self.rank1_admin)

        response = self.client.get(reverse('admin_dashboard'))

        self.assertContains(response, 'Corrected')
        self.assertNotContains(response, 'Corrected by admin')
        self.assertNotContains(response, 'Rank 2 internal correction.')

        edit_response = self.client.get(reverse('admin_edit_document', args=[document.id]))
        self.assertContains(edit_response, 'Edit Submitted Document')
        self.assertNotContains(edit_response, 'Rank 2 internal correction.')

    def test_adviser_correction_stands_alone_and_is_not_forwarded(self):
        document = self.create_document_with_files(title='Needs Work', forwarded=False)
        self.client.force_login(self.adviser)

        response = self.client.post(
            reverse('adviser_edit_document', args=[document.id]),
            {
                'correction_notes': 'Fix the activity date.',
            },
        )
        document.refresh_from_db()

        self.assertRedirects(response, reverse('adviser_dashboard'))
        self.assertEqual(document.status, 'CORRECTED')
        self.assertEqual(document.adviser_status, 'CORRECTED')
        self.assertEqual(document.correction_reviewed_by, self.adviser)

        response = self.client.get(reverse('adviser_dashboard'))
        self.assertContains(response, 'Corrected by adviser')
        self.assertNotContains(response, 'Approved by Adviser')

        self.client.force_login(self.admin)
        response = self.client.get(reverse('admin_dashboard'))
        self.assertNotContains(response, 'Needs Work')

    def test_resubmission_returns_to_adviser_and_resets_forwarding(self):
        document = self.create_document_with_files(status='CORRECTED')
        document.correction_notes = 'Fix date'
        document.save()
        self.client.force_login(self.organization)

        response = self.client.post(
            f'{reverse("upload")}?document={document.id}',
            {
                'uploaded_file': SimpleUploadedFile(
                    'revised.pdf',
                    b'%PDF-1.4\nrevised',
                    content_type='application/pdf',
                ),
            },
        )
        document.refresh_from_db()

        self.assertRedirects(response, reverse('dashboard'))
        self.assertEqual(document.status, 'RESUBMITTED')
        self.assertEqual(document.adviser_status, 'PENDING')
        self.assertIsNone(document.forwarded_to_admin_at)
        self.assertEqual(document.section, 'ORGANIZATION_ACTIVITIES')
        self.assertEqual(document.title, 'Original Title')

    def test_admin_groups_sections_in_major_section_order(self):
        old_time = timezone.now() - timedelta(days=2)
        new_time = timezone.now()
        older = self.create_document_with_files(
            title='Accreditation File',
            section='REACCREDITATION_ACCREDITATION',
        )
        newer = self.create_document_with_files(
            title='Activity File',
            section='ORGANIZATION_ACTIVITIES',
        )
        Document.objects.filter(pk=older.pk).update(uploaded_at=old_time)
        Document.objects.filter(pk=newer.pk).update(uploaded_at=new_time)
        self.client.force_login(self.admin)

        response = self.client.get(reverse('admin_dashboard'))
        content = response.content.decode()

        self.assertLess(
            content.index('Organization Activities'),
            content.index('Reaccreditation and Accreditation'),
        )

    def test_admin_uploaded_section_template_shows_on_organization_dashboard(self):
        self.client.force_login(self.admin)
        response = self.client.post(
            reverse('admin_dashboard'),
            {
                'section': 'ACCOMPLISHMENT_REPORT',
                'template_upload': '1',
                'template_file': SimpleUploadedFile(
                    'template.pdf',
                    b'%PDF-1.4\ntemplate',
                    content_type='application/pdf',
                ),
            },
        )

        self.assertRedirects(response, reverse('admin_dashboard'))
        self.assertTrue(FileSectionTemplate.objects.filter(section='ACCOMPLISHMENT_REPORT').exists())

        self.client.force_login(self.organization)
        response = self.client.get(reverse('dashboard'))
        self.assertContains(response, 'Accomplishment Report')
        self.assertContains(response, 'template.pdf')
        self.assertNotContains(response, 'File Section Templates')

    def test_admin_can_upload_multiple_section_templates(self):
        self.client.force_login(self.admin)
        response = self.client.post(
            reverse('admin_dashboard'),
            {
                'section': 'ACCOMPLISHMENT_REPORT',
                'template_upload': '1',
                'template_file': [
                    SimpleUploadedFile(
                        'format.pdf',
                        b'%PDF-1.4\nformat',
                        content_type='application/pdf',
                    ),
                    SimpleUploadedFile(
                        'sample.pdf',
                        b'%PDF-1.4\nsample',
                        content_type='application/pdf',
                    ),
                ],
            },
        )

        self.assertRedirects(response, reverse('admin_dashboard'))
        self.assertEqual(
            FileSectionTemplate.objects.filter(section='ACCOMPLISHMENT_REPORT').count(),
            2,
        )

        self.client.force_login(self.organization)
        response = self.client.get(reverse('dashboard'))
        self.assertContains(response, 'format.pdf')
        self.assertContains(response, 'sample.pdf')

    def test_admin_can_change_existing_template_file(self):
        template = FileSectionTemplate.objects.create(
            section='ORGANIZATION_ACTIVITIES',
            template_file='templates/old-template.pdf',
            uploaded_by=self.admin,
        )
        self.client.force_login(self.admin)

        response = self.client.post(
            reverse('admin_dashboard'),
            {
                'section': 'ORGANIZATION_ACTIVITIES',
                'template_id': str(template.id),
                'template_upload': '1',
                'template_file': SimpleUploadedFile(
                    'new-template.pdf',
                    b'%PDF-1.4\nnew',
                    content_type='application/pdf',
                ),
            },
        )
        template.refresh_from_db()

        self.assertRedirects(response, reverse('admin_dashboard'))
        self.assertIn('new-template', template.template_file.name)
        self.assertEqual(FileSectionTemplate.objects.filter(section='ORGANIZATION_ACTIVITIES').count(), 1)

    def test_existing_admin_template_uses_hover_change_control(self):
        FileSectionTemplate.objects.create(
            section='ORGANIZATION_ACTIVITIES',
            template_file='templates/template.pdf',
            uploaded_by=self.admin,
        )
        self.client.force_login(self.admin)

        response = self.client.get(reverse('admin_dashboard'))

        self.assertContains(response, 'template-file-wrap')
        self.assertContains(response, 'template-change-btn')
        self.assertNotContains(response, 'Upload New Template')

    def test_organization_can_forward_resubmitted_folder_directly_to_admin(self):
        document = self.create_document_with_files(status='RESUBMITTED', forwarded=False)
        self.client.force_login(self.organization)

        dashboard_response = self.client.get(reverse('dashboard'))
        self.assertContains(dashboard_response, 'Upload Revision')
        self.assertContains(dashboard_response, 'Forward Folder')

        response = self.client.post(
            reverse('organization_forward_folder', args=[document.folder.id]),
            {'forward_target': 'admin'},
        )
        document.refresh_from_db()
        document.folder.refresh_from_db()

        self.assertRedirects(response, reverse('dashboard'))
        self.assertIsNotNone(document.forwarded_to_admin_at)
        self.assertIsNotNone(document.folder.forwarded_to_admin_at)

        self.client.force_login(self.admin)
        admin_response = self.client.get(reverse('admin_dashboard'))
        self.assertContains(admin_response, document.uploaded_filename())

    def test_existing_officer_photo_uses_replace_without_save_button(self):
        officer = OrganizationOfficer.objects.create(
            organization=self.organization_profile,
            position='President',
            name='Avery Santos',
        )
        officer.photo.save('president.png', ContentFile(b'image'), save=True)
        self.client.force_login(self.organization)

        response = self.client.get(reverse('dashboard'))

        self.assertContains(response, 'Replace')
        self.assertContains(response, f'{officer.photo.url}?v=')
        self.assertContains(response, 'Add Logo')
        self.assertNotContains(response, 'name="photo" accept="image/*" required onchange="this.form.submit();">\\n                                \\n                                    <button type="submit" class="photo-save-btn">Save</button>', html=False)

    def test_admin_registration_allows_duplicate_positions(self):
        form = AccountRegisterForm({
            'account_type': 'admin',
            'account_name': 'another-coi',
            'admin_position': AdminProfile.RANK_2,
            'password': 'SnsuPass12345!',
            'password_confirm': 'SnsuPass12345!',
        })

        self.assertTrue(form.is_valid())

    def test_organization_can_rename_account(self):
        self.client.force_login(self.organization)

        response = self.client.post(
            reverse('rename_organization'),
            {'organization_name': 'Renamed Organization'},
        )
        self.organization_profile.refresh_from_db()

        self.assertRedirects(response, f'{reverse("dashboard")}#organization-overview')
        self.assertEqual(self.organization_profile.organization_name, 'Renamed Organization')

    def test_organization_can_delete_account_and_related_adviser(self):
        self.client.force_login(self.organization)

        response = self.client.post(reverse('delete_account'))

        self.assertRedirects(response, reverse('home'))
        self.assertFalse(User.objects.filter(pk=self.organization.pk).exists())
        self.assertFalse(User.objects.filter(pk=self.adviser.pk).exists())
        self.assertFalse(OrganizationProfile.objects.filter(pk=self.organization_profile.pk).exists())

    def test_adviser_can_delete_account_without_deleting_organization(self):
        self.client.force_login(self.adviser)

        response = self.client.post(reverse('delete_account'))

        self.assertRedirects(response, reverse('home'))
        self.assertFalse(User.objects.filter(pk=self.adviser.pk).exists())
        self.assertTrue(User.objects.filter(pk=self.organization.pk).exists())

    def test_rank1_corrections_column_flashes_reviewed_before_forwarding(self):
        document = self.create_document_with_files(
            status='SUBMITTED',
            rank2_reviewed_by=self.admin,
            forwarded_to_rank1_at=timezone.now(),
        )
        self.client.force_login(self.rank1_admin)

        response = self.client.get(reverse('admin_dashboard'))

        self.assertContains(response, 'reviewed-forwarding-flash')
        self.assertContains(response, 'reviewed before forwarding')
        self.assertContains(response, document.uploaded_filename())

    def test_admin_download_converts_pdf_to_docx(self):
        document = self.create_document_with_files()
        converted_path = Path(TEST_MEDIA_ROOT) / 'converted.docx'
        converted_path.write_bytes(b'docx bytes')
        self.client.force_login(self.admin)

        with patch('documents.views.convert_pdf_path_to_docx', return_value=converted_path):
            response = self.client.get(reverse('admin_download_document', args=[document.id]))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response['Content-Type'],
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        )
        self.assertIn('.docx', response['Content-Disposition'])
        self.assertEqual(response.content, b'docx bytes')

    def test_admin_docx_review_upload_is_converted_to_pdf(self):
        document = self.create_document_with_files(status='SUBMITTED')
        self.client.force_login(self.admin)

        with patch(
            'documents.forms.convert_uploaded_docx_to_pdf',
            return_value=ContentFile(b'%PDF-1.4\nconverted', name='reviewed.pdf'),
        ):
            response = self.client.post(
                reverse('admin_edit_document', args=[document.id]),
                {
                    'correction_notes': 'Converted DOCX correction.',
                    'review_file': SimpleUploadedFile(
                        'reviewed.docx',
                        b'docx',
                        content_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document',
                    ),
                },
            )
        document.refresh_from_db()

        self.assertRedirects(response, reverse('admin_dashboard'))
        self.assertEqual(document.status, 'CORRECTED')
        self.assertTrue(document.uploaded_file.name.endswith('.pdf'))
        self.assertIn('reviewed', document.uploaded_file.name)
