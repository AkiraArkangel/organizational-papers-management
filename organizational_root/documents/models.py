from django.contrib.auth.models import User
from django.db import models
from django.utils import timezone
from pathlib import Path
import os
from supabase import create_client

# Supabase Storage configuration
SUPABASE_URL = os.environ.get('SUPABASE_URL')
SUPABASE_KEY = os.environ.get('SUPABASE_KEY')
SUPABASE_STORAGE_BUCKET = os.environ.get('SUPABASE_STORAGE_BUCKET', 'documents')

# Custom Supabase storage backend
class SupabaseStorage:
    def __init__(self):
        self._client = None
        self.bucket = SUPABASE_STORAGE_BUCKET
        
    @property
    def client(self):
        if self._client is None:
            self._client = create_client(SUPABASE_URL, SUPABASE_KEY)
        return self._client
        
    def _save(self, name, content):
        content.seek(0)
        file_data = content.read()
        
        response = self.client.storage.from_(self.bucket).upload(
            path=name,
            file=file_data,
            file_options={'content-type': 'application/pdf'}
        )
        
        return name
        
    def url(self, name):
        return f"{SUPABASE_URL}/storage/v1/object/public/{self.bucket}/{name}"
        
    def exists(self, name):
        try:
            self.client.storage.from_(self.bucket).get_public_url(name)
            return True
        except:
            return False
            
    def delete(self, name):
        self.client.storage.from_(self.bucket).remove([name])

# Create storage instance
supabase_storage = SupabaseStorage()


class CorrectionItem(models.Model):
    """Structured correction items for documents and folders"""
    CORRECTION_TYPES = [
        ('TEXT_CORRECTION', 'Text Correction'),
        ('FILE_ADDITION', 'File Addition'),
        ('SECTION_CORRECTION', 'Section Correction'),
        ('GENERAL_CORRECTION', 'General Correction'),
    ]

    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('IN_PROGRESS', 'In Progress'),
        ('RESOLVED', 'Resolved'),
        ('VERIFIED', 'Verified'),
    ]

    PRIORITY_CHOICES = [
        ('HIGH', 'High'),
        ('MEDIUM', 'Medium'),
        ('LOW', 'Low'),
    ]

    document = models.ForeignKey('Document', on_delete=models.CASCADE, null=True, blank=True, related_name='correction_items')
    folder = models.ForeignKey('SubmissionFolder', on_delete=models.CASCADE, null=True, blank=True, related_name='correction_items')
    correction_type = models.CharField(max_length=50, choices=CORRECTION_TYPES)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default='MEDIUM')
    
    # Location reference
    page_number = models.IntegerField(null=True, blank=True, help_text='Page number for text corrections')
    section = models.CharField(max_length=100, null=True, blank=True, help_text='Document section')
    
    # Correction details
    current_text = models.TextField(blank=True, help_text='Current text that needs to be changed')
    suggested_text = models.TextField(blank=True, help_text='Suggested replacement text')
    description = models.TextField(help_text='Detailed description of the correction needed')
    
    # Metadata
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='created_corrections')
    assigned_to = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='assigned_corrections')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    resolved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='resolved_corrections')
    resolution_notes = models.TextField(blank=True, help_text='Notes on how the correction was resolved')

    class Meta:
        ordering = ['-priority', 'status', '-created_at']

    def __str__(self):
        target = self.document.title if self.document else self.folder.title if self.folder else 'Unknown'
        return f'{self.get_correction_type_display()} for {target} ({self.get_status_display()})'


class Notification(models.Model):
    """Notifications for different account types"""
    NOTIFICATION_TYPES = [
        ('FILE_FORWARDED', 'File Forwarded'),
        ('FILE_SUBMITTED', 'File Submitted'),
        ('FILE_APPROVED', 'File Approved'),
        ('FILE_CORRECTED', 'File Corrected'),
        ('SIGNED_COPY_UPLOADED', 'Signed Copy Uploaded'),
        ('SIGNED_COPY_FORWARDED', 'Signed Copy Forwarded'),
    ]

    recipient = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    notification_type = models.CharField(max_length=50, choices=NOTIFICATION_TYPES)
    title = models.CharField(max_length=255)
    message = models.TextField()
    document = models.ForeignKey('Document', on_delete=models.CASCADE, null=True, blank=True, related_name='notifications')
    signed_copy = models.ForeignKey('SignedScannedCopy', on_delete=models.CASCADE, null=True, blank=True, related_name='notifications')
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.title} for {self.recipient.username}'


class OrganizationProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    organization_name = models.CharField(max_length=255)
    logo = models.FileField(upload_to='organization_logos/', null=True, blank=True, storage=supabase_storage)
    logo_updated_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.organization_name

    def save(self, *args, **kwargs):
        update_fields = kwargs.get('update_fields')
        if self.logo and (update_fields is None or 'logo' in update_fields):
            self.logo_updated_at = timezone.now()
            if update_fields is not None:
                kwargs['update_fields'] = set(update_fields) | {'logo_updated_at'}
        super().save(*args, **kwargs)


class OrganizationOfficer(models.Model):
    organization = models.ForeignKey(
        OrganizationProfile,
        on_delete=models.CASCADE,
        related_name='officers',
    )
    position = models.CharField(max_length=120)
    name = models.CharField(max_length=180)
    photo = models.FileField(upload_to='officers/', null=True, blank=True, storage=supabase_storage)
    photo_updated_at = models.DateTimeField(null=True, blank=True)
    display_order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['display_order', 'created_at', 'id']

    def __str__(self):
        return f'{self.position}: {self.name}'

    def save(self, *args, **kwargs):
        update_fields = kwargs.get('update_fields')
        if self.photo and (update_fields is None or 'photo' in update_fields):
            self.photo_updated_at = timezone.now()
            if update_fields is not None:
                kwargs['update_fields'] = set(update_fields) | {'photo_updated_at'}
        super().save(*args, **kwargs)


class AdviserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    organization = models.ForeignKey(
        OrganizationProfile,
        on_delete=models.CASCADE,
        related_name='advisers',
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'{self.user.username} - {self.organization.organization_name}'


class AdminProfile(models.Model):
    RANK_1 = 'RANK_1'
    RANK_2 = 'RANK_2'
    RANK_CHOICES = [
        (RANK_1, 'Director of Student Affairs and Services (DSAS)'),
        (RANK_2, 'Campus Organization In-charge (COI)'),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE)
    rank = models.CharField(max_length=10, choices=RANK_CHOICES, default=RANK_1)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'{self.user.username} - {self.get_rank_display()}'


class Document(models.Model):
    SECTION_CHOICES = [
        ('ORGANIZATION_ACTIVITIES', 'Organization Activities'),
        ('REACCREDITATION_ACCREDITATION', 'Reaccreditation and Accreditation'),
        ('ACCOMPLISHMENT_REPORT', 'Accomplishment Report'),
    ]

    ADVISER_STATUS_CHOICES = [
        ('PENDING', 'Pending Adviser Review'),
        ('CORRECTED', 'Corrected'),
        ('APPROVED', 'Approved by Adviser'),
    ]

    STATUS_CHOICES = [
        ('SUBMITTED', 'Submitted'),
        ('CORRECTED', 'Corrected'),
        ('RESUBMITTED', 'Resubmitted'),
        ('APPROVED_BY_COI', 'Approved by COI'),
        ('READY_FOR_PRINTING', 'Ready for Printing'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    folder = models.ForeignKey(
        'SubmissionFolder',
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name='documents',
    )
    section = models.CharField(
        max_length=40,
        choices=SECTION_CHOICES,
        default='ORGANIZATION_ACTIVITIES',
    )
    title = models.CharField(max_length=255)
    uploaded_file = models.CharField(max_length=500, null=True, blank=True)  # Store Supabase path
    corrected_file = models.CharField(max_length=500, null=True, blank=True)  # Store Supabase path
    correction_notes = models.TextField(blank=True)
    correction_checklist_state = models.JSONField(default=dict, blank=True)

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='SUBMITTED')
    adviser_status = models.CharField(
        max_length=20,
        choices=ADVISER_STATUS_CHOICES,
        default='PENDING',
    )
    adviser_reviewed_by = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='adviser_reviewed_documents',
    )
    uploaded_at = models.DateTimeField(auto_now_add=True)
    status_updated_at = models.DateTimeField(auto_now=True)
    adviser_status_updated_at = models.DateTimeField(null=True, blank=True)
    forwarded_to_admin_at = models.DateTimeField(null=True, blank=True)
    admin_notification_seen_at = models.DateTimeField(null=True, blank=True)
    rank2_reviewed_by = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='rank2_reviewed_documents',
    )
    forwarded_to_rank1_at = models.DateTimeField(null=True, blank=True)
    rank1_notification_seen_at = models.DateTimeField(null=True, blank=True)
    correction_reviewed_by = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='corrected_documents',
    )

    def __str__(self):
        return self.title

    def organization_name(self):
        profile = getattr(self.user, 'organizationprofile', None)
        if profile:
            return profile.organization_name
        return 'No Organization'

    def organization_display_name(self):
        profile = getattr(self.user, 'organizationprofile', None)
        if profile:
            return f'{profile.organization_name} ({self.user.username})'
        return 'No Organization'

    def uploaded_filename(self):
        return Path(self.uploaded_file.name).name

    def corrected_filename(self):
        return Path(self.corrected_file.name).name

    def current_filename(self):
        return self.uploaded_filename()

    def current_file_url(self):
        return self.uploaded_file.url

    def current_file_label(self):
        return 'Uploaded File'

    def status_labels(self):
        if self.status == 'CORRECTED':
            return [self.corrected_status_label()]

        labels = [self.get_status_display()]
        if self.adviser_status == 'APPROVED':
            labels.append(self.get_adviser_status_display())

        # Add forwarding destination indicator
        if self.forwarded_to_rank1_at:
            labels.append('Forwarded to DSAS')
        elif self.forwarded_to_admin_at:
            labels.append('Forwarded to COI')

        return labels

    def corrected_status_label(self):
        reviewer = self.correction_reviewed_by
        if reviewer:
            # Check if reviewer is adviser or admin
            adviser_profile = getattr(reviewer, 'adviserprofile', None)
            admin_profile = getattr(reviewer, 'adminprofile', None)
            
            if adviser_profile:
                return f'Corrected by {reviewer.username} (Adviser)'
            elif admin_profile:
                rank = admin_profile.rank
                if rank == AdminProfile.RANK_2:
                    return f'Corrected by {reviewer.username} (COI)'
                elif rank == AdminProfile.RANK_1:
                    return f'Corrected by {reviewer.username} (DSAS)'
                else:
                    return f'Corrected by {reviewer.username} (Admin)'
            else:
                return f'Corrected by {reviewer.username}'
        return 'Corrected'

    def correction_added_by_rank2(self):
        reviewer = self.correction_reviewed_by
        profile = getattr(reviewer, 'adminprofile', None)
        return bool(profile and profile.rank == AdminProfile.RANK_2)

    def rank2_status_labels(self):
        labels = self.status_labels()
        if self.forwarded_to_rank1_at:
            # When forwarded to DSAS, only show forwarding status (approval is implied)
            return ['Forwarded by COI to DSAS']
        if self.status == 'APPROVED_BY_COI':
            labels = ['Approved by COI']
        
        # Check if this is a new document that was re-forwarded
        # A document is "new" if it has adviser_status APPROVED but hasn't been processed by COI yet
        if self.adviser_status == 'APPROVED' and self.status in ['SUBMITTED', 'RESUBMITTED']:
            if 'New' not in labels:
                labels.insert(0, 'New')
        
        return labels

    def rank1_status_labels(self):
        if self.status == 'CORRECTED' and self.correction_added_by_rank2():
            return ['Corrected']

        labels = self.status_labels()
        if self.status != 'CORRECTED' and self.forwarded_to_rank1_at:
            labels.append('Forwarded by COI')
        return labels

    def adviser_status_labels(self):
        if self.status == 'CORRECTED':
            return [self.corrected_status_label()]

        if self.status == 'APPROVED_BY_COI':
            labels = ['Approved by COI']
            if self.forwarded_to_rank1_at:
                labels.append('Forwarded by COI to DSAS')
            return labels

        if self.adviser_status == 'APPROVED':
            labels = [self.get_status_display(), self.get_adviser_status_display()]
            if self.forwarded_to_admin_at:
                labels.append('Forwarded to COI')
            elif self.forwarded_to_rank1_at:
                labels.append('Forwarded to DSAS')
            return labels

        return [self.get_status_display()]

    def organization_status_labels(self):
        if self.status == 'CORRECTED':
            return [self.get_status_display(), self.corrected_status_label()]

        labels = [self.get_status_display()]
        if self.adviser_status == 'APPROVED':
            labels.append('Approved by Adviser')
        if self.forwarded_to_admin_at:
            labels.append('Forwarded by Adviser to COI')
        elif self.forwarded_to_rank1_at:
            labels.append('Forwarded by COI to DSAS')

        return labels

    def get_progress_percentage(self):
        """Calculate progress percentage for file workflow"""
        progress = 0

        # Base submission: 25%
        if self.status in ['SUBMITTED', 'RESUBMITTED', 'CORRECTED', 'APPROVED_BY_COI', 'READY_FOR_PRINTING']:
            progress += 25

        # Adviser approval: 50%
        if self.adviser_status == 'APPROVED':
            progress += 25

        # COI approval: 75%
        if self.status == 'APPROVED_BY_COI':
            progress += 25

        # Ready for printing: 100%
        if self.status == 'READY_FOR_PRINTING':
            progress += 25

        # If corrected, reset to 25% (needs resubmission)
        if self.status == 'CORRECTED':
            progress = 25

        return min(progress, 100)

    def get_progress_steps(self):
        """Get progress steps for display"""
        steps = [
            {'name': 'Submitted', 'completed': True, 'current': False},
            {'name': 'Adviser Review', 'completed': False, 'current': False},
            {'name': 'COI Review', 'completed': False, 'current': False},
            {'name': 'DSAS Review', 'completed': False, 'current': False},
        ]

        if self.adviser_status == 'APPROVED':
            steps[1]['completed'] = True
            steps[2]['current'] = True
        elif self.adviser_status == 'PENDING':
            steps[1]['current'] = True

        if self.status == 'APPROVED_BY_COI':
            steps[2]['completed'] = True
            steps[3]['current'] = True

        if self.status == 'READY_FOR_PRINTING':
            steps[3]['completed'] = True

        if self.status == 'CORRECTED':
            steps[1]['current'] = True
            steps[1]['completed'] = False

        return steps

    def is_forwardable_to_admin(self):
        return (
            self.adviser_status == 'APPROVED'
            and self.status != 'CORRECTED'
            and self.forwarded_to_admin_at is None
        )

    def is_forwardable_to_rank1(self):
        return (
            self.forwarded_to_admin_at is not None
            and self.forwarded_to_rank1_at is None
            and self.status == 'APPROVED_BY_COI'
        )

    def correction_checklist_items(self):
        items = []
        checklist_state = self.correction_checklist_state or {}

        for index, note in enumerate(self.correction_notes.splitlines()):
            note = note.strip()
            if note:
                key = str(index)
                items.append({
                    'key': key,
                    'text': note,
                    'checked': bool(checklist_state.get(key)),
                })

        return items

    def has_correction_checklist(self):
        return bool(self.correction_checklist_items())

    def correction_checklist_complete(self):
        items = self.correction_checklist_items()
        return bool(items) and all(item['checked'] for item in items)


class SubmissionFolder(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    section = models.CharField(max_length=40, choices=Document.SECTION_CHOICES)
    name = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    forwarded_to_admin_at = models.DateTimeField(null=True, blank=True)
    admin_notification_seen_at = models.DateTimeField(null=True, blank=True)
    rank2_reviewed_by = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='rank2_reviewed_folders',
    )
    forwarded_to_rank1_at = models.DateTimeField(null=True, blank=True)
    rank1_notification_seen_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['created_at', 'id']

    def __str__(self):
        return self.name

    def organization_name(self):
        profile = getattr(self.user, 'organizationprofile', None)
        if profile:
            return profile.organization_name
        return 'No Organization'

    def organization_display_name(self):
        profile = getattr(self.user, 'organizationprofile', None)
        if profile:
            return f'{profile.organization_name} ({self.user.username})'
        return 'No Organization'

    def status_labels(self):
        documents = list(self.documents.all())
        if not documents:
            return ['Empty Folder']
        if any(document.status == 'CORRECTED' for document in documents):
            return ['Contains Corrections']
        if self.forwarded_to_rank1_at:
            reviewer = self.rank2_reviewed_by
            if reviewer:
                profile = getattr(reviewer, 'adminprofile', None)
                if profile and profile.rank == AdminProfile.RANK_2:
                    reviewer_label = 'COI'
                elif profile and profile.rank == AdminProfile.RANK_1:
                    reviewer_label = 'DSAS'
                else:
                    reviewer_label = 'COI'
            else:
                reviewer_label = 'COI'
            return [f'Forwarded by {reviewer_label}']
        if self.forwarded_to_admin_at:
            # When forwarded_to_admin_at is set, it means forwarded to COI (RANK_2)
            # Check if there are new documents that haven't been processed by COI yet
            new_documents = [doc for doc in documents if doc.forwarded_to_admin_at is None]
            if new_documents:
                return ['Forwarded to COI', f'{len(new_documents)} New File(s)']
            return ['Forwarded to COI']
        if all(document.status == 'APPROVED_BY_COI' for document in documents):
            return ['Approved by COI']
        if all(document.adviser_status == 'APPROVED' for document in documents):
            return ['Approved by Adviser']
        return ['Submitted']

    def organization_status_labels(self):
        documents = list(self.documents.all())
        if not documents:
            return ['Empty Folder']
        if any(document.status == 'CORRECTED' for document in documents):
            return ['Contains Corrections']
        if self.forwarded_to_rank1_at:
            return ['Forwarded to DSAS by COI']
        if self.forwarded_to_admin_at:
            return ['Forwarded to COI']
        if all(document.adviser_status == 'APPROVED' for document in documents):
            return ['Approved by Adviser']
        return ['Submitted']

    def adviser_status_labels(self):
        documents = list(self.documents.all())
        if not documents:
            return ['Empty Folder']
        if any(document.status == 'CORRECTED' for document in documents):
            return ['Contains Corrections']
        if all(document.status == 'APPROVED_BY_COI' for document in documents):
            labels = ['Approved by COI']
            if self.forwarded_to_rank1_at:
                labels.append('Forwarded by COI to DSAS')
            return labels
        if self.forwarded_to_rank1_at:
            return ['Forwarded to DSAS']
        if self.forwarded_to_admin_at:
            return ['Forwarded to COI']
        if all(document.adviser_status == 'APPROVED' for document in documents):
            return ['Approved by Adviser']
        return ['Submitted']

    def is_forwardable_to_admin(self):
        documents = list(self.documents.all())
        if not documents:
            return False
        
        # If never forwarded, check if all documents are ready
        if self.forwarded_to_admin_at is None:
            return all(document.is_forwardable_to_admin() for document in documents)
        
        # If already forwarded, check if there are new documents that haven't been forwarded yet
        # A document is considered "new" if its forwarded_to_admin_at is None
        new_documents = [
            doc for doc in documents 
            if doc.forwarded_to_admin_at is None
        ]
        
        # Allow re-forwarding if there are new documents that are approved by adviser
        if new_documents:
            return all(doc.adviser_status == 'APPROVED' for doc in new_documents)
        
        return False

    def is_forwardable_to_rank1(self):
        documents = list(self.documents.all())
        return (
            bool(documents)
            and self.forwarded_to_admin_at is not None
            and self.forwarded_to_rank1_at is None
            and all(document.status == 'APPROVED_BY_COI' for document in documents)
        )


class FileSectionTemplate(models.Model):
    section = models.CharField(
        max_length=40,
        choices=Document.SECTION_CHOICES,
    )
    template_file = models.FileField(upload_to='templates/', storage=supabase_storage)
    uploaded_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    uploaded_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['section', '-uploaded_at', 'id']

    def __str__(self):
        return self.get_section_display()

    def filename(self):
        return Path(self.template_file.name).name


class SignedScannedCopy(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    folder = models.ForeignKey(
        SubmissionFolder,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='signed_copies',
    )
    title = models.CharField(max_length=255)
    signed_file = models.FileField(upload_to='signed_copies/', storage=supabase_storage)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    forwarded_to_adviser_at = models.DateTimeField(null=True, blank=True)
    forwarded_to_coi_at = models.DateTimeField(null=True, blank=True)
    forwarded_to_dsas_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-uploaded_at', 'id']

    def __str__(self):
        return self.title

    def filename(self):
        return Path(self.signed_file.name).name

    def organization_display_name(self):
        profile = getattr(self.user, 'organizationprofile', None)
        if profile:
            return f'{profile.organization_name} ({self.user.username})'
        return 'No Organization'
