from django import forms
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from django.db import transaction
from django.utils import timezone
from .converters import ConversionError, convert_uploaded_docx_to_pdf
from .models import (
    AdminProfile,
    AdviserProfile,
    CorrectionItem,
    Document,
    FileSectionTemplate,
    OrganizationOfficer,
    OrganizationProfile,
    SignedScannedCopy,
    SubmissionFolder,
)
from django.contrib.auth.models import User


class AccountLoginForm(AuthenticationForm):
    ACCOUNT_TYPE_CHOICES = [
        ('organization', 'Organization'),
        ('adviser', 'Adviser'),
        ('admin', 'Admin'),
    ]

    account_type = forms.ChoiceField(
        label='Account type',
        choices=ACCOUNT_TYPE_CHOICES,
        required=True,
    )
    username = forms.CharField(label='Account ID')

    def clean(self):
        cleaned_data = super().clean()
        user = self.get_user()
        selected_account_type = cleaned_data.get('account_type')

        if user and selected_account_type:
            actual_account_type = self.account_type_for_user(user)
            if selected_account_type != actual_account_type:
                raise forms.ValidationError(
                    'The selected account type does not match this account.'
                )

        return cleaned_data

    def account_type_for_user(self, user):
        if user.is_staff:
            return 'admin'
        if getattr(user, 'adviserprofile', None):
            return 'adviser'
        return 'organization'


class AccountRegisterForm(forms.Form):
    ACCOUNT_TYPE_CHOICES = [
        ('organization', 'Organization Account'),
        ('adviser', 'Adviser Account'),
        ('admin', 'Admin Account'),
    ]

    account_type = forms.ChoiceField(choices=ACCOUNT_TYPE_CHOICES)
    account_name = forms.CharField(
        label='Organization Acronym, Adviser ID, or Admin ID',
        max_length=150,
        help_text='Use this value when logging in.',
    )
    organization_name = forms.CharField(max_length=255, required=False)
    adviser_organization = forms.ModelChoiceField(
        queryset=OrganizationProfile.objects.none(),
        required=False,
        label='Organization represented',
        empty_label='Choose an existing organization',
    )
    ADMIN_POSITION_CHOICES = [
        (AdminProfile.RANK_2, 'Campus Organization In-charge (COI)'),
        (AdminProfile.RANK_1, 'Director of Student Affairs and Services (DSAS)'),
    ]

    admin_position = forms.ChoiceField(
        choices=ADMIN_POSITION_CHOICES,
        required=False,
        label='Admin position',
    )
    password = forms.CharField(widget=forms.PasswordInput)
    password_confirm = forms.CharField(
        label='Confirm password',
        widget=forms.PasswordInput,
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['adviser_organization'].queryset = (
            OrganizationProfile.objects.select_related('user').order_by('organization_name')
        )

    def clean_account_name(self):
        account_name = self.cleaned_data['account_name']
        if User.objects.filter(username=account_name).exists():
            raise forms.ValidationError('This account ID is already taken.')
        return account_name

    def clean_password(self):
        password = self.cleaned_data['password']
        validate_password(password)
        return password

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get('password')
        password_confirm = cleaned_data.get('password_confirm')

        if password and password_confirm and password != password_confirm:
            self.add_error('password_confirm', 'Passwords do not match.')

        account_type = cleaned_data.get('account_type')

        if account_type == 'organization' and not cleaned_data.get('organization_name'):
            self.add_error('organization_name', 'Organization name is required.')

        if account_type == 'adviser' and not cleaned_data.get('adviser_organization'):
            self.add_error('adviser_organization', 'Choose the organization this adviser represents.')

        if account_type == 'admin' and not cleaned_data.get('admin_position'):
            self.add_error('admin_position', 'Choose the admin position for this account.')

        return cleaned_data

    def save(self):
        account_type = self.cleaned_data['account_type']

        with transaction.atomic():
            user = User.objects.create_user(
                username=self.cleaned_data['account_name'],
                password=self.cleaned_data['password'],
                is_staff=account_type == 'admin',
            )

            if account_type == 'organization':
                OrganizationProfile.objects.create(
                    user=user,
                    organization_name=self.cleaned_data['organization_name'],
                )
            elif account_type == 'adviser':
                AdviserProfile.objects.create(
                    user=user,
                    organization=self.cleaned_data['adviser_organization'],
                )
            elif account_type == 'admin':
                AdminProfile.objects.create(
                    user=user,
                    rank=self.cleaned_data['admin_position'],
                )

        return user


class DocumentUploadForm(forms.Form):
    section = forms.ChoiceField(
        label='Section',
        choices=[
            ('ORGANIZATION_ACTIVITIES', 'Organization Activities'),
            ('ORGANIZATION_STRUCTURE', 'Organization Structure'),
            ('OFFICERS_LIST', 'Officers List'),
            ('CONSTITUTION_BYLAWS', 'Constitution and Bylaws'),
            ('ACTIVITY_PLANS', 'Activity Plans'),
            ('FINANCIAL_REPORTS', 'Financial Reports'),
            ('PROJECT_PROPOSALS', 'Project Proposals'),
            ('CERTIFICATES', 'Certificates'),
            ('OTHER_DOCUMENTS', 'Other Documents'),
        ],
        required=True,
    )
    folder_name = forms.CharField(
        label='Folder name',
        max_length=255,
        required=False,
        help_text='Name the folder the Activity Name or Report that you will be submitting.',
    )
    uploaded_file = forms.FileField(label='Upload PDF file', required=True)

    def __init__(self, *args, locked_section=None, existing_folder=None, resubmitting=False, **kwargs):
        super().__init__(*args, **kwargs)
        self.existing_folder = existing_folder
        self.resubmitting = resubmitting
        if locked_section:
            self.fields['section'].initial = locked_section
            self.fields['section'].disabled = True
            self.fields['section'].help_text = 'This file stays in the selected section.'
        if existing_folder:
            self.fields['folder_name'].initial = existing_folder.name
            self.fields['folder_name'].disabled = True
            self.fields['folder_name'].help_text = 'This file will be added to the selected folder.'
        if resubmitting:
            self.fields['folder_name'].help_text = 'Resubmission keeps this file in its current folder.'

    def clean_folder_name(self):
        folder_name = self.cleaned_data.get('folder_name', '').strip()
        if self.existing_folder or self.resubmitting:
            return folder_name
        if not folder_name:
            raise forms.ValidationError('Enter a folder name.')
        return folder_name

    def clean_uploaded_file(self):
        uploaded_file = self.cleaned_data['uploaded_file']
        if not uploaded_file.name.lower().endswith('.pdf'):
            raise forms.ValidationError('Upload a PDF file.')
        return uploaded_file


class AdviserDocumentForm(forms.ModelForm):
    review_file = forms.FileField(
        label='Upload edited PDF or DOCX',
        required=False,
        help_text='DOCX files are converted to PDF automatically when the corrected file is saved.',
        widget=forms.FileInput(attrs={
            'accept': 'application/pdf,.pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document,.docx',
        }),
    )
    approve_by_adviser = forms.BooleanField(
        label='Mark this file as approved by adviser',
        required=False,
        help_text='Approved files can be forwarded to admin accounts.',
    )

    class Meta:
        model = Document
        fields = ['correction_notes']
        widgets = {
            'correction_notes': forms.Textarea(attrs={
                'class': 'correction-notes',
                'rows': 12,
                'placeholder': 'Write one correction per line. Each line becomes a checklist item.',
            }),
        }
        labels = {
            'correction_notes': 'Comments for the organization',
        }
        help_texts = {
            'correction_notes': 'Enter one comment or required change per line. Each line appears on the organization checklist.',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.original_correction_notes = self.instance.correction_notes if self.instance.pk else ''
        self.fields['approve_by_adviser'].initial = False

    def clean_review_file(self):
        review_file = self.cleaned_data.get('review_file')
        if review_file and not review_file.name.lower().endswith(('.pdf', '.docx')):
            raise forms.ValidationError('Upload a PDF or DOCX file.')
        if review_file and review_file.name.lower().endswith('.docx'):
            try:
                review_file = convert_uploaded_docx_to_pdf(review_file)
            except ConversionError as error:
                raise forms.ValidationError(str(error))
        return review_file

    def save(self, adviser_user=None, commit=True):
        document = super().save(commit=False)
        has_correction_notes = bool(document.correction_notes.strip())
        notes_changed = document.correction_notes != self.original_correction_notes
        review_file = self.cleaned_data.get('review_file')

        if notes_changed:
            document.correction_checklist_state = {}

        if review_file:
            if document.uploaded_file:
                document.uploaded_file.delete(save=False)
            document.uploaded_file = review_file
            document.status = 'CORRECTED'
            document.adviser_status = 'CORRECTED'
            document.adviser_reviewed_by = adviser_user
            document.correction_reviewed_by = adviser_user
            document.adviser_status_updated_at = timezone.now()
            document.forwarded_to_admin_at = None
        elif self.cleaned_data.get('approve_by_adviser'):
            document.adviser_status = 'APPROVED'
            document.adviser_reviewed_by = adviser_user
            document.adviser_status_updated_at = timezone.now()
        elif has_correction_notes and (notes_changed or document.status in ['SUBMITTED', 'RESUBMITTED']):
            document.status = 'CORRECTED'
            document.adviser_status = 'CORRECTED'
            document.adviser_reviewed_by = adviser_user
            document.correction_reviewed_by = adviser_user
            document.adviser_status_updated_at = timezone.now()
            document.forwarded_to_admin_at = None

        if commit:
            document.save()
            self.save_m2m()

        return document


class FileSectionTemplateForm(forms.ModelForm):
    class Meta:
        model = FileSectionTemplate
        fields = ['section', 'template_file']

    def clean_template_file(self):
        template_file = self.cleaned_data['template_file']
        if not template_file.name.lower().endswith('.pdf'):
            raise forms.ValidationError('Upload a PDF template.')
        return template_file


class AdminDocumentForm(forms.ModelForm):
    review_file = forms.FileField(
        label='Upload edited PDF or DOCX',
        required=False,
        help_text='DOCX files are converted to PDF automatically when the corrected file is saved.',
        widget=forms.FileInput(attrs={
            'accept': 'application/pdf,.pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document,.docx',
        }),
    )
    ready_for_printing = forms.BooleanField(
        label='Mark this file as ready for printing',
        required=False,
        help_text='Only check this after the submitted file is approved for printing.',
    )
    approve_by_coi = forms.BooleanField(
        label='Mark file as approved by COI',
        required=False,
        help_text='Approved files can be forwarded to DSAS.',
    )

    class Meta:
        model = Document
        fields = ['correction_notes']
        widgets = {
            'correction_notes': forms.Textarea(attrs={
                'class': 'correction-notes',
                'rows': 12,
                'placeholder': 'Write one correction per line. Each line becomes a checklist item.',
            }),
        }
        labels = {
            'correction_notes': 'Comments for the organization',
        }
        help_texts = {
            'correction_notes': 'Enter one comment or required change per line. Saving comments sends them to the organization as a checklist and marks the file corrected.',
        }

    def __init__(self, *args, hide_existing_corrections=False, admin_rank=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.original_correction_notes = self.instance.correction_notes if self.instance.pk else ''
        self.fields['ready_for_printing'].initial = False
        self.fields['approve_by_coi'].initial = False
        if admin_rank == AdminProfile.RANK_2:
            self.fields.pop('ready_for_printing')
        elif admin_rank == AdminProfile.RANK_1:
            self.fields.pop('approve_by_coi')
        if hide_existing_corrections:
            self.initial['correction_notes'] = ''

    def clean_review_file(self):
        review_file = self.cleaned_data.get('review_file')
        if review_file and not review_file.name.lower().endswith(('.pdf', '.docx')):
            raise forms.ValidationError('Upload a PDF or DOCX file.')
        if review_file and review_file.name.lower().endswith('.docx'):
            try:
                review_file = convert_uploaded_docx_to_pdf(review_file)
            except ConversionError as error:
                raise forms.ValidationError(str(error))
        return review_file

    def save(self, reviewed_by=None, commit=True):
        document = super().save(commit=False)
        has_correction_notes = bool(document.correction_notes.strip())
        notes_changed = document.correction_notes != self.original_correction_notes
        review_file = self.cleaned_data.get('review_file')

        if notes_changed:
            document.correction_checklist_state = {}

        if review_file:
            if document.uploaded_file:
                document.uploaded_file.delete(save=False)
            document.uploaded_file = review_file
            document.status = 'CORRECTED'
            document.correction_reviewed_by = reviewed_by
        elif has_correction_notes and notes_changed:
            document.status = 'CORRECTED'
            document.correction_reviewed_by = reviewed_by
        elif self.cleaned_data.get('approve_by_coi'):
            document.status = 'APPROVED_BY_COI'
            document.rank2_reviewed_by = reviewed_by
        elif self.cleaned_data.get('ready_for_printing'):
            document.status = 'READY_FOR_PRINTING'

        if commit:
            document.save()
            self.save_m2m()

        return document


class SignedScannedCopyUploadForm(forms.ModelForm):
    forward_to_adviser = forms.BooleanField(
        label='Forward to Adviser account',
        required=False,
    )
    forward_to_coi = forms.BooleanField(
        label='Forward to COI account',
        required=False,
    )
    forward_to_dsas = forms.BooleanField(
        label='Forward to DSAS account',
        required=False,
    )

    class Meta:
        model = SignedScannedCopy
        fields = ['folder', 'title', 'signed_file']
        labels = {
            'folder': 'Related folder',
            'title': 'Reference title',
            'signed_file': 'Signed scanned copy',
        }

    def __init__(self, *args, organization_user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['folder'].queryset = SubmissionFolder.objects.none()
        self.fields['folder'].required = False
        self.fields['folder'].empty_label = 'No related folder'
        if organization_user:
            self.fields['folder'].queryset = SubmissionFolder.objects.filter(
                user=organization_user,
            ).order_by('-created_at')

    def clean_signed_file(self):
        signed_file = self.cleaned_data['signed_file']
        allowed_extensions = ('.pdf', '.jpg', '.jpeg', '.png')
        if not signed_file.name.lower().endswith(allowed_extensions):
            raise forms.ValidationError('Upload a PDF, JPG, or PNG scanned copy.')
        return signed_file


class OrganizationOfficerForm(forms.ModelForm):
    class Meta:
        model = OrganizationOfficer
        fields = ['position', 'name', 'photo']
        labels = {
            'position': 'Position',
            'name': 'Officer name',
            'photo': 'Officer photo',
        }
        help_texts = {
            'photo': 'Optional. You can add a photo later.',
        }

    def clean_photo(self):
        photo = self.cleaned_data.get('photo')
        if photo:
            allowed_extensions = ('.jpg', '.jpeg', '.png', '.gif', '.webp')
            if not photo.name.lower().endswith(allowed_extensions):
                raise forms.ValidationError('Upload an image file: JPG, PNG, GIF, or WEBP.')
        return photo


class OrganizationOfficerDetailsForm(forms.ModelForm):
    class Meta:
        model = OrganizationOfficer
        fields = ['position', 'name']
        labels = {
            'position': 'Position',
            'name': 'Officer name',
        }


class OrganizationLogoForm(forms.ModelForm):
    class Meta:
        model = OrganizationProfile
        fields = ['logo']
        labels = {
            'logo': 'Organization logo',
        }

    def clean_logo(self):
        logo = self.cleaned_data.get('logo')
        if not logo:
            raise forms.ValidationError('Choose an organization logo to upload.')

        allowed_extensions = ('.jpg', '.jpeg', '.png', '.gif', '.webp')
        if not logo.name.lower().endswith(allowed_extensions):
            raise forms.ValidationError('Upload an image file: JPG, PNG, GIF, or WEBP.')

        return logo


class OrganizationNameForm(forms.ModelForm):
    class Meta:
        model = OrganizationProfile
        fields = ['organization_name']
        labels = {
            'organization_name': 'Organization name',
        }


class OfficerPhotoForm(forms.ModelForm):
    class Meta:
        model = OrganizationOfficer
        fields = ['photo']

    def clean_photo(self):
        photo = self.cleaned_data.get('photo')
        if not photo:
            raise forms.ValidationError('Choose a photo to upload.')

        allowed_extensions = ('.jpg', '.jpeg', '.png', '.gif', '.webp')
        if not photo.name.lower().endswith(allowed_extensions):
            raise forms.ValidationError('Upload an image file: JPG, PNG, GIF, or WEBP.')

        return photo


class CorrectionItemForm(forms.ModelForm):
    class Meta:
        model = CorrectionItem
        fields = [
            'correction_type',
            'status',
            'priority',
            'page_number',
            'section',
            'current_text',
            'suggested_text',
            'description',
            'assigned_to',
            'resolution_notes',
        ]
        widgets = {
            'correction_type': forms.Select(attrs={'class': 'form-control'}),
            'status': forms.Select(attrs={'class': 'form-control'}),
            'priority': forms.Select(attrs={'class': 'form-control'}),
            'page_number': forms.NumberInput(attrs={'class': 'form-control', 'min': '1'}),
            'section': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., Section 1.2'}),
            'current_text': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Current text that needs to be changed'}),
            'suggested_text': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Suggested replacement text'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 4, 'placeholder': 'Detailed description of the correction needed'}),
            'assigned_to': forms.Select(attrs={'class': 'form-control'}),
            'resolution_notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Notes on how the correction was resolved'}),
        }
        labels = {
            'correction_type': 'Correction Type',
            'status': 'Status',
            'priority': 'Priority',
            'page_number': 'Page Number',
            'section': 'Section',
            'current_text': 'Current Text',
            'suggested_text': 'Suggested Text',
            'description': 'Description',
            'assigned_to': 'Assigned To',
            'resolution_notes': 'Resolution Notes',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Filter assigned_to field to show only organization users
        if 'assigned_to' in self.fields:
            self.fields['assigned_to'].queryset = User.objects.filter(
                organizationprofile__isnull=False
            ).select_related('organizationprofile')
            self.fields['assigned_to'].required = False
            self.fields['assigned_to'].empty_label = "Unassigned"
