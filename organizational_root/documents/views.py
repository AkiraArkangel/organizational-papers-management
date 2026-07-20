import json
from django.http import FileResponse, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth import logout
from django.views.decorators.http import require_POST
from django.utils import timezone
from django.db.models import Count, Max, Q
from django.urls import reverse
from .converters import ConversionError, convert_pdf_path_to_docx, docx_download_name
from .forms import (
    AccountRegisterForm,
    AdminDocumentForm,
    AdviserDocumentForm,
    CorrectionItemForm,
    DocumentUploadForm,
    OfficerPhotoForm,
    OrganizationOfficerDetailsForm,
    OrganizationLogoForm,
    OrganizationNameForm,
    OrganizationOfficerForm,
    SignedScannedCopyUploadForm,
)
from .models import (
    AdminProfile,
    AdviserProfile,
    CorrectionItem,
    Document,
    FileSectionTemplate,
    Notification,
    OrganizationOfficer,
    OrganizationProfile,
    SignedScannedCopy,
    SubmissionFolder,
)


def section_title(section):
    return dict(Document.SECTION_CHOICES).get(section, section)


def create_notification(recipient, notification_type, title, message, document=None, signed_copy=None):
    """Helper function to create notifications for different account types"""
    Notification.objects.create(
        recipient=recipient,
        notification_type=notification_type,
        title=title,
        message=message,
        document=document,
        signed_copy=signed_copy,
    )


def adviser_profile_for(user):
    return getattr(user, 'adviserprofile', None)


def organization_profile_for(user):
    return getattr(user, 'organizationprofile', None)


def admin_profile_for(user):
    return getattr(user, 'adminprofile', None)


def admin_rank_for(user):
    profile = getattr(user, 'adminprofile', None)
    if profile:
        return profile.rank
    return AdminProfile.RANK_1


def admin_rank_label_for(user):
    return dict(AdminProfile.RANK_CHOICES).get(
        admin_rank_for(user),
        'Director of Student Affairs and Services (DSAS)',
    )


def rank1_admin_id():
    profile = AdminProfile.objects.filter(
        rank=AdminProfile.RANK_1,
    ).select_related('user').order_by('user__username').first()
    if profile:
        return profile.user.username
    return 'DSAS'


def template_queryset():
    return FileSectionTemplate.objects.select_related('uploaded_by').order_by(
        'section',
        '-uploaded_at',
        'id',
    )


def templates_by_section():
    grouped = {section: [] for section, _ in Document.SECTION_CHOICES}
    for template in template_queryset():
        grouped.setdefault(template.section, []).append(template)
    return grouped


def admin_document_queryset_for(user):
    documents = Document.objects.select_related(
        'user',
        'user__organizationprofile',
    ).filter(
        forwarded_to_admin_at__isnull=False,
    )

    if admin_rank_for(user) == AdminProfile.RANK_2:
        # For COI (RANK_2), show all documents that have been forwarded to admin
        # This includes both originally forwarded documents and re-forwarded documents
        return documents

    return documents.filter(forwarded_to_rank1_at__isnull=False)


def admin_folder_queryset_for(user):
    folders = SubmissionFolder.objects.select_related(
        'user',
        'user__organizationprofile',
        'rank2_reviewed_by',
    ).prefetch_related(
        'documents',
        'documents__user',
        'documents__user__organizationprofile',
    ).filter(
        forwarded_to_admin_at__isnull=False,
    )

    if admin_rank_for(user) == AdminProfile.RANK_2:
        # For COI (RANK_2), show all forwarded folders
        # Folders with new documents will naturally be included since they have forwarded_to_admin_at set
        return folders

    return folders.filter(forwarded_to_rank1_at__isnull=False)


def redirect_for_user(user):
    if user.is_staff:
        return redirect('admin_dashboard')
    if adviser_profile_for(user):
        return redirect('adviser_dashboard')
    return redirect('dashboard')


def build_section_groups(folders, include_empty=False):
    templates = templates_by_section()
    groups_by_section = {}
    for section, label in Document.SECTION_CHOICES:
        section_templates = templates.get(section, [])
        groups_by_section[section] = {
            'section': section,
            'section_label': label,
            'first_uploaded_at': None,
            'folders': [],
            'templates': section_templates,
            'template': section_templates[0] if section_templates else None,
            'note': (
                'include these files when submitting a hardcopy of your accomplishment report'
                if section == 'ORGANIZATION_ACTIVITIES'
                else ''
            ),
        }

    for folder in folders:
        group = groups_by_section[folder.section]
        group['folders'].append(folder)
        if group['first_uploaded_at'] is None:
            group['first_uploaded_at'] = folder.created_at

    groups = [
        group
        for group in groups_by_section.values()
        if include_empty or group['folders']
    ]
    original_order = {section: index for index, (section, _) in enumerate(Document.SECTION_CHOICES)}

    return sorted(groups, key=lambda group: original_order[group['section']])


def signed_copy_queryset_for_admin(user):
    copies = SignedScannedCopy.objects.select_related(
        'user',
        'user__organizationprofile',
        'folder',
    )
    if admin_rank_for(user) == AdminProfile.RANK_2:
        return copies.filter(forwarded_to_coi_at__isnull=False)
    return copies.filter(forwarded_to_dsas_at__isnull=False)


def build_overview_context(
    organization,
    can_edit=False,
    officer_form=None,
    logo_form=None,
    name_form=None,
    submissions_url='dashboard',
):
    return {
        'organization': organization,
        'officers': organization.officers.all(),
        'can_edit': can_edit,
        'officer_form': officer_form or OrganizationOfficerForm(),
        'logo_form': logo_form or OrganizationLogoForm(instance=organization),
        'name_form': name_form or OrganizationNameForm(instance=organization),
        'submissions_url': submissions_url,
    }


def organization_overview_tab_redirect():
    return redirect(f'{reverse("dashboard")}#organization-overview')


def delete_document_files(document):
    if document.uploaded_file:
        document.uploaded_file.delete(save=False)
    if document.corrected_file:
        document.corrected_file.delete(save=False)


def handle_template_upload(request):
    if request.method != 'POST' or 'template_upload' not in request.POST:
        return False

    section = request.POST.get('section')
    valid_sections = {section_key for section_key, _ in Document.SECTION_CHOICES}
    template_files = request.FILES.getlist('template_file')

    if section not in valid_sections:
        messages.error(request, 'Choose a valid major file section.')
        return True
    if not template_files:
        messages.error(request, 'Choose at least one PDF template or sample.')
        return True

    invalid_files = [
        template_file.name
        for template_file in template_files
        if not template_file.name.lower().endswith('.pdf')
    ]
    if invalid_files:
        messages.error(request, 'Only PDF templates and samples can be uploaded.')
        return True

    template_id = request.POST.get('template_id')
    if template_id:
        template = get_object_or_404(FileSectionTemplate, pk=template_id, section=section)
        if template.template_file:
            template.template_file.delete(save=False)
        template.template_file = template_files[0]
        template.uploaded_by = request.user
        template.save()
        messages.success(request, 'Template/sample file changed.')
        return True

    for template_file in template_files:
        FileSectionTemplate.objects.create(
            section=section,
            template_file=template_file,
            uploaded_by=request.user,
        )

    messages.success(request, f'{len(template_files)} template/sample file(s) uploaded.')
    return True


def delete_adviser_user(user):
    user.delete()


def delete_organization_user(user):
    organization = organization_profile_for(user)
    if organization:
        adviser_users = [
            adviser.user
            for adviser in organization.advisers.select_related('user')
        ]
        for document in Document.objects.filter(user=user):
            delete_document_files(document)
        for signed_copy in SignedScannedCopy.objects.filter(user=user):
            if signed_copy.signed_file:
                signed_copy.signed_file.delete(save=False)
        for officer in organization.officers.all():
            if officer.photo:
                officer.photo.delete(save=False)
        if organization.logo:
            organization.logo.delete(save=False)
        for adviser_user in adviser_users:
            delete_adviser_user(adviser_user)
    user.delete()


def document_docx_response(document):
    try:
        converted_path = convert_pdf_path_to_docx(document.uploaded_file.path)
    except ConversionError as error:
        return None, str(error)

    with converted_path.open('rb') as converted_file:
        response = HttpResponse(
            converted_file.read(),
            content_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        )
    converted_path.unlink(missing_ok=True)
    response['Content-Disposition'] = (
        f'attachment; filename="{docx_download_name(document.uploaded_filename())}"'
    )
    return response, None


def register_account(request):
    if request.method == 'POST':
        form = AccountRegisterForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('login')
    else:
        form = AccountRegisterForm()

    return render(request, 'documents/register.html', {'form': form})


@login_required
def upload_document(request):
    if request.user.is_staff or adviser_profile_for(request.user):
        return redirect_for_user(request.user)

    valid_sections = {section for section, _ in Document.SECTION_CHOICES}
    locked_section = request.GET.get('section')
    if locked_section not in valid_sections:
        locked_section = None
    existing_folder = None
    folder_id = request.GET.get('folder')
    if folder_id:
        existing_folder = get_object_or_404(SubmissionFolder, pk=folder_id, user=request.user)
        locked_section = existing_folder.section

    resubmit_document = None
    document_id = request.GET.get('document')
    if document_id:
        resubmit_document = get_object_or_404(Document, pk=document_id, user=request.user)
        existing_folder = resubmit_document.folder
        locked_section = resubmit_document.section

    if request.method == 'POST':
        form = DocumentUploadForm(
            request.POST,
            request.FILES,
            locked_section=locked_section,
            existing_folder=existing_folder,
            resubmitting=resubmit_document is not None,
        )
        if form.is_valid():
            section = locked_section or form.cleaned_data['section']
            uploaded_file = form.cleaned_data['uploaded_file']

            if resubmit_document:
                if resubmit_document.uploaded_file:
                    resubmit_document.uploaded_file.delete(save=False)
                if resubmit_document.corrected_file:
                    resubmit_document.corrected_file.delete(save=False)

                resubmit_document.uploaded_file = uploaded_file
                resubmit_document.corrected_file = None
                resubmit_document.correction_checklist_state = {}
                resubmit_document.correction_reviewed_by = None
                resubmit_document.status = 'RESUBMITTED'
                resubmit_document.adviser_status = 'PENDING'
                resubmit_document.adviser_reviewed_by = None
                resubmit_document.adviser_status_updated_at = None
                resubmit_document.forwarded_to_admin_at = None
                resubmit_document.admin_notification_seen_at = None
                resubmit_document.rank2_reviewed_by = None
                resubmit_document.forwarded_to_rank1_at = None
                resubmit_document.rank1_notification_seen_at = None
                resubmit_document.uploaded_at = timezone.now()
                resubmit_document.save(update_fields=[
                    'uploaded_file',
                    'corrected_file',
                    'correction_checklist_state',
                    'correction_reviewed_by',
                    'status',
                    'adviser_status',
                    'adviser_reviewed_by',
                    'adviser_status_updated_at',
                    'forwarded_to_admin_at',
                    'admin_notification_seen_at',
                    'rank2_reviewed_by',
                    'forwarded_to_rank1_at',
                    'rank1_notification_seen_at',
                    'uploaded_at',
                    'status_updated_at',
                ])
            else:
                folder = existing_folder
                if folder is None:
                    folder = SubmissionFolder.objects.create(
                        user=request.user,
                        section=section,
                        name=form.cleaned_data['folder_name'],
                    )

                doc = form.save(commit=False)
                doc.user = request.user
                doc.folder = folder
                doc.section = folder.section
                doc.title = uploaded_file.name
                doc.status = 'SUBMITTED'
                
                # Handle file upload to Supabase directly
                if uploaded_file:
                    import os
                    from supabase import create_client
                    
                    supabase_url = os.environ.get('SUPABASE_URL')
                    supabase_key = os.environ.get('SUPABASE_KEY')
                    supabase_bucket = os.environ.get('SUPABASE_STORAGE_BUCKET', 'documents')
                    
                    # Upload to Supabase
                    client = create_client(supabase_url, supabase_key)
                    file_path = f"uploads/{uploaded_file.name}"
                    
                    # Read file content
                    uploaded_file.seek(0)
                    file_content = uploaded_file.read()
                    
                    # Upload to Supabase Storage
                    client.storage.from_(supabase_bucket).upload(
                        path=file_path,
                        file=file_content,
                        file_options={'content-type': 'application/pdf'}
                    )
                    
                    # Save only the filename, not the actual file
                    doc.uploaded_file.name = file_path
                
                doc.save()

                if folder.forwarded_to_admin_at:
                    folder.forwarded_to_admin_at = None
                    folder.admin_notification_seen_at = None
                    folder.rank2_reviewed_by = None
                    folder.forwarded_to_rank1_at = None
                    folder.rank1_notification_seen_at = None
                    folder.save(update_fields=[
                        'forwarded_to_admin_at',
                        'admin_notification_seen_at',
                        'rank2_reviewed_by',
                        'forwarded_to_rank1_at',
                        'rank1_notification_seen_at',
                    ])

            return redirect('dashboard')
    else:
        form = DocumentUploadForm(
            locked_section=locked_section,
            existing_folder=existing_folder,
            resubmitting=resubmit_document is not None,
        )

    return render(request, 'documents/upload.html', {
        'form': form,
        'section_templates': template_queryset(),
        'resubmit_section': locked_section,
        'resubmit_section_label': section_title(locked_section) if locked_section else '',
        'existing_folder': existing_folder,
        'resubmit_document': resubmit_document,
    })


def home(request):
    return render(request, 'documents/home.html')


@login_required
def dashboard(request):
    if request.user.is_staff:
        return redirect('admin_dashboard')
    if adviser_profile_for(request.user):
        return redirect('adviser_dashboard')

    documents = Document.objects.filter(
        user=request.user,
    ).select_related('user', 'folder').order_by('uploaded_at')
    folders = SubmissionFolder.objects.filter(
        user=request.user,
    ).prefetch_related('documents').order_by('created_at')

    # Calculate status statistics for Organization
    status_stats = {
        'total': documents.count(),
        'submitted': documents.filter(status='SUBMITTED').count(),
        'corrected': documents.filter(status='CORRECTED').count(),
        'resubmitted': documents.filter(status='RESUBMITTED').count(),
        'approved_by_adviser': documents.filter(adviser_status='APPROVED').count(),
        'approved_by_coi': documents.filter(status='APPROVED_BY_COI').count(),
        'ready_for_printing': documents.filter(status='READY_FOR_PRINTING').count(),
    }

    # Only show notification for documents with status updated by adviser/admin
    # and not already dismissed by the user
    organization_notification = documents.filter(
        status__in=['CORRECTED', 'APPROVED_BY_COI', 'READY_FOR_PRINTING'],
    ).order_by('-status_updated_at').first()

    # Filter out dismissed notifications from session storage
    dismissed_ids = request.session.get('dismissed_notifications', [])
    if organization_notification and str(organization_notification.id) in dismissed_ids:
        organization_notification = None

    organization = organization_profile_for(request.user)
    if not organization:
        return redirect('home')

    # Prepare calendar events
    calendar_events = []
    for doc in documents:
        calendar_events.append({
            'date': doc.uploaded_at.strftime('%Y-%m-%d'),
            'title': doc.title,
            'status': doc.status
        })

    # Get notifications for the user
    notifications = Notification.objects.filter(recipient=request.user).order_by('-created_at')[:20]
    notifications_data = [
        {
            'id': n.id,
            'title': n.title,
            'message': n.message,
            'is_read': n.is_read,
            'created_at': n.created_at.isoformat()
        }
        for n in notifications
    ]

    # Get correction items for the organization's documents
    correction_items = CorrectionItem.objects.filter(
        document__user=request.user
    ).select_related('document', 'created_by', 'assigned_to').order_by('-priority', 'status', '-created_at')

    return render(request, 'documents/dashboard.html', {
        'documents': documents,
        'folders': folders,
        'section_groups': build_section_groups(folders, include_empty=True),
        'section_templates': template_queryset(),
        'organization_notification': organization_notification,
        'signed_copy_form': SignedScannedCopyUploadForm(organization_user=request.user),
        'signed_copies': SignedScannedCopy.objects.filter(user=request.user).select_related('folder'),
        'status_stats': status_stats,
        'calendar_events': json.dumps(calendar_events),
        'notifications_data': json.dumps(notifications_data),
        'correction_items': correction_items,
        **build_overview_context(
            organization,
            can_edit=True,
            submissions_url='dashboard',
        ),
    })


@login_required
@require_POST
def dismiss_notification(request):
    """Handle notification dismissal via AJAX"""
    notification_id = request.POST.get('notification_id')
    if notification_id:
        dismissed = request.session.get('dismissed_notifications', [])
        if notification_id not in dismissed:
            dismissed.append(notification_id)
            request.session['dismissed_notifications'] = dismissed
    return JsonResponse({'success': True})


@login_required
def organization_overview(request):
    if request.user.is_staff:
        return redirect('admin_organizations_list')

    adviser_profile = adviser_profile_for(request.user)
    organization = adviser_profile.organization if adviser_profile else organization_profile_for(request.user)

    if not organization:
        return redirect_for_user(request.user)

    return render(request, 'documents/organization_overview.html', build_overview_context(
        organization,
        can_edit=adviser_profile is None,
        submissions_url='adviser_dashboard' if adviser_profile else 'dashboard',
    ))


@login_required
@require_POST
def add_organization_officer(request):
    if request.user.is_staff or adviser_profile_for(request.user):
        return redirect_for_user(request.user)

    organization = get_object_or_404(OrganizationProfile, user=request.user)
    form = OrganizationOfficerForm(request.POST, request.FILES)
    if form.is_valid():
        officer = form.save(commit=False)
        officer.organization = organization
        next_order = organization.officers.aggregate(max_order=Max('display_order'))['max_order']
        officer.display_order = 0 if next_order is None else next_order + 1
        officer.save()
        return organization_overview_tab_redirect()

    documents = Document.objects.filter(user=request.user).select_related('user').order_by('uploaded_at')
    folders = SubmissionFolder.objects.filter(user=request.user).prefetch_related('documents')
    return render(request, 'documents/dashboard.html', {
        'documents': documents,
        'folders': folders,
        'section_groups': build_section_groups(folders, include_empty=True),
        'section_templates': template_queryset(),
        'organization_notification': documents.filter(
            status__in=['CORRECTED', 'APPROVED_BY_COI', 'READY_FOR_PRINTING'],
        ).order_by('-status_updated_at').first(),
        'signed_copy_form': SignedScannedCopyUploadForm(organization_user=request.user),
        'signed_copies': SignedScannedCopy.objects.filter(user=request.user).select_related('folder'),
        **build_overview_context(
            organization,
            can_edit=True,
            officer_form=form,
            submissions_url='dashboard',
        ),
        'active_dashboard_tab': 'organization-overview',
    })


@login_required
@require_POST
def update_organization_logo(request):
    if request.user.is_staff or adviser_profile_for(request.user):
        return redirect_for_user(request.user)

    organization = get_object_or_404(OrganizationProfile, user=request.user)
    form = OrganizationLogoForm(request.POST, request.FILES, instance=organization)

    if form.is_valid():
        new_logo = form.cleaned_data['logo']
        if organization.logo and organization.logo.name != new_logo.name:
            organization.logo.delete(save=False)
        form.save()
        return organization_overview_tab_redirect()

    documents = Document.objects.filter(user=request.user).select_related('user').order_by('uploaded_at')
    folders = SubmissionFolder.objects.filter(user=request.user).prefetch_related('documents')
    return render(request, 'documents/dashboard.html', {
        'documents': documents,
        'folders': folders,
        'section_groups': build_section_groups(folders, include_empty=True),
        'section_templates': template_queryset(),
        'organization_notification': documents.filter(
            status__in=['CORRECTED', 'APPROVED_BY_COI', 'READY_FOR_PRINTING'],
        ).order_by('-status_updated_at').first(),
        'signed_copy_form': SignedScannedCopyUploadForm(organization_user=request.user),
        'signed_copies': SignedScannedCopy.objects.filter(user=request.user).select_related('folder'),
        **build_overview_context(
            organization,
            can_edit=True,
            logo_form=form,
            submissions_url='dashboard',
        ),
        'active_dashboard_tab': 'organization-overview',
    })


@login_required
@require_POST
def rename_organization(request):
    if request.user.is_staff or adviser_profile_for(request.user):
        return redirect_for_user(request.user)

    organization = get_object_or_404(OrganizationProfile, user=request.user)
    form = OrganizationNameForm(request.POST, instance=organization)

    if form.is_valid():
        form.save()
        messages.success(request, 'Organization account renamed.')
        return organization_overview_tab_redirect()

    documents = Document.objects.filter(user=request.user).select_related('user').order_by('uploaded_at')
    folders = SubmissionFolder.objects.filter(user=request.user).prefetch_related('documents')
    return render(request, 'documents/dashboard.html', {
        'documents': documents,
        'folders': folders,
        'section_groups': build_section_groups(folders, include_empty=True),
        'section_templates': template_queryset(),
        'organization_notification': documents.filter(
            status__in=['CORRECTED', 'APPROVED_BY_COI', 'READY_FOR_PRINTING'],
        ).order_by('-status_updated_at').first(),
        'signed_copy_form': SignedScannedCopyUploadForm(organization_user=request.user),
        'signed_copies': SignedScannedCopy.objects.filter(user=request.user).select_related('folder'),
        **build_overview_context(
            organization,
            can_edit=True,
            name_form=form,
            submissions_url='dashboard',
        ),
        'active_dashboard_tab': 'organization-overview',
    })


@login_required
@require_POST
def delete_account(request):
    if request.user.is_staff:
        return redirect('admin_dashboard')

    user = request.user
    redirect_url = reverse('home')
    logout(request)

    if adviser_profile_for(user):
        delete_adviser_user(user)
    else:
        delete_organization_user(user)

    return redirect(redirect_url)


@login_required
@require_POST
def move_organization_officer(request, officer_id, direction):
    if request.user.is_staff or adviser_profile_for(request.user):
        return redirect_for_user(request.user)

    organization = get_object_or_404(OrganizationProfile, user=request.user)
    officer = get_object_or_404(OrganizationOfficer, pk=officer_id, organization=organization)
    officers = list(organization.officers.all())
    current_index = next((index for index, item in enumerate(officers) if item.pk == officer.pk), None)

    if current_index is not None:
        target_index = current_index - 1 if direction == 'up' else current_index + 1
        if 0 <= target_index < len(officers):
            officers[current_index], officers[target_index] = officers[target_index], officers[current_index]
            for index, item in enumerate(officers):
                if item.display_order != index:
                    item.display_order = index
                    item.save(update_fields=['display_order'])

    return organization_overview_tab_redirect()


@login_required
@require_POST
def delete_organization_officer(request, officer_id):
    if request.user.is_staff or adviser_profile_for(request.user):
        return redirect_for_user(request.user)

    organization = get_object_or_404(OrganizationProfile, user=request.user)
    officer = get_object_or_404(OrganizationOfficer, pk=officer_id, organization=organization)
    if officer.photo:
        officer.photo.delete(save=False)
    officer.delete()

    for index, item in enumerate(organization.officers.all()):
        if item.display_order != index:
            item.display_order = index
            item.save(update_fields=['display_order'])

    return organization_overview_tab_redirect()


@login_required
@require_POST
def update_organization_officer(request, officer_id):
    if request.user.is_staff or adviser_profile_for(request.user):
        return redirect_for_user(request.user)

    organization = get_object_or_404(OrganizationProfile, user=request.user)
    officer = get_object_or_404(OrganizationOfficer, pk=officer_id, organization=organization)
    form = OrganizationOfficerDetailsForm(request.POST, instance=officer)

    if form.is_valid():
        form.save()

    return organization_overview_tab_redirect()


@login_required
@require_POST
def update_organization_officer_photo(request, officer_id):
    if request.user.is_staff or adviser_profile_for(request.user):
        return redirect_for_user(request.user)

    organization = get_object_or_404(OrganizationProfile, user=request.user)
    officer = get_object_or_404(OrganizationOfficer, pk=officer_id, organization=organization)
    form = OfficerPhotoForm(request.POST, request.FILES, instance=officer)

    if form.is_valid():
        new_photo = form.cleaned_data['photo']
        if officer.photo and officer.photo.name != new_photo.name:
            officer.photo.delete(save=False)
        form.save()

    return organization_overview_tab_redirect()


@login_required
@require_POST
def delete_document(request, document_id):
    if request.user.is_staff or adviser_profile_for(request.user):
        return redirect_for_user(request.user)

    document = get_object_or_404(Document, pk=document_id, user=request.user)
    folder = document.folder
    delete_document_files(document)
    document.delete()
    if folder and not folder.documents.exists() and not folder.signed_copies.exists():
        folder.delete()
    return redirect('dashboard')


@login_required
@require_POST
def organization_forward_folder(request, folder_id):
    if request.user.is_staff or adviser_profile_for(request.user):
        return redirect_for_user(request.user)

    folder = get_object_or_404(
        SubmissionFolder.objects.prefetch_related('documents'),
        pk=folder_id,
        user=request.user,
    )
    target = request.POST.get('forward_target')
    documents = list(folder.documents.all())

    if not documents:
        messages.error(request, 'Add at least one file before forwarding this folder.')
        return redirect('dashboard')

    if target == 'adviser':
        folder.forwarded_to_admin_at = None
        folder.admin_notification_seen_at = None
        folder.rank2_reviewed_by = None
        folder.forwarded_to_rank1_at = None
        folder.rank1_notification_seen_at = None
        folder.save(update_fields=[
            'forwarded_to_admin_at',
            'admin_notification_seen_at',
            'rank2_reviewed_by',
            'forwarded_to_rank1_at',
            'rank1_notification_seen_at',
        ])
        folder.documents.update(
            forwarded_to_admin_at=None,
            admin_notification_seen_at=None,
            rank2_reviewed_by=None,
            forwarded_to_rank1_at=None,
            rank1_notification_seen_at=None,
            status_updated_at=timezone.now(),
        )
        
        # Create notification for adviser
        adviser = folder.organization.advisers.first()
        if adviser:
            create_notification(
                recipient=adviser.user,
                notification_type='FILE_FORWARDED',
                title='Folder Returned for Review',
                message=f'Folder "{folder.title}" has been returned to you for review.',
                document=None
            )
        
        messages.success(request, 'Folder returned to adviser review.')
    elif target in ['coi', 'dsas']:
        if any(document.status == 'CORRECTED' for document in documents):
            messages.error(request, 'Upload the revised files before forwarding this folder.')
            return redirect('dashboard')

        now = timezone.now()
        folder.forwarded_to_rank1_at = now
        folder.rank1_notification_seen_at = None
        folder.forwarded_to_admin_at = None
        folder.admin_notification_seen_at = None
        folder.rank2_reviewed_by = None
        folder.save(update_fields=[
            'forwarded_to_rank1_at',
            'rank1_notification_seen_at',
            'forwarded_to_admin_at',
            'admin_notification_seen_at',
            'rank2_reviewed_by',
        ])
        folder.documents.exclude(status='CORRECTED').update(
            forwarded_to_rank1_at=now,
            rank1_notification_seen_at=None,
            forwarded_to_admin_at=None,
            admin_notification_seen_at=None,
            rank2_reviewed_by=None,
            status_updated_at=now,
        )
        
        # Create notification for DSAS (RANK_1 admin)
        if target == 'dsas':
            rank1_admin = AdminProfile.objects.filter(rank=AdminProfile.RANK_1).first()
            if rank1_admin:
                create_notification(
                    recipient=rank1_admin.user,
                    notification_type='FILE_FORWARDED',
                    title='Folder Forwarded for Review',
                    message=f'Folder "{folder.title}" has been forwarded to you for review.',
                    document=None
                )
        
        messages.success(request, f'Folder forwarded directly to {target.upper()}.')
    else:
        messages.error(request, 'Choose where to forward this folder.')

    return redirect('dashboard')


@login_required
@require_POST
def update_correction_checklist(request, document_id):
    if request.user.is_staff or adviser_profile_for(request.user):
        return redirect_for_user(request.user)

    document = get_object_or_404(Document, pk=document_id, user=request.user)
    if document.status != 'RESUBMITTED':
        return redirect('dashboard')

    checklist_items = document.correction_checklist_items()
    valid_keys = {item['key'] for item in checklist_items}
    checked_keys = set(request.POST.getlist('completed_items'))

    document.correction_checklist_state = {
        key: True
        for key in valid_keys
        if key in checked_keys
    }

    document.save(update_fields=['correction_checklist_state'])
    return redirect('dashboard')


@login_required
@require_POST
def upload_signed_copy(request):
    if request.user.is_staff or adviser_profile_for(request.user):
        return redirect_for_user(request.user)

    form = SignedScannedCopyUploadForm(
        request.POST,
        request.FILES,
        organization_user=request.user,
    )
    if form.is_valid():
        signed_copy = form.save(commit=False)
        signed_copy.user = request.user
        now = timezone.now()
        
        # Get organization for notifications
        organization = organization_profile_for(request.user)
        
        if form.cleaned_data.get('forward_to_adviser'):
            signed_copy.forwarded_to_adviser_at = now
            # Create notification for adviser
            adviser = organization.advisers.first()
            if adviser:
                create_notification(
                    recipient=adviser.user,
                    notification_type='SIGNED_COPY_FORWARDED',
                    title='Signed Copy Forwarded',
                    message=f'Signed copy for "{signed_copy.folder.title}" has been forwarded to you.',
                    signed_copy=signed_copy
                )
        if form.cleaned_data.get('forward_to_coi'):
            signed_copy.forwarded_to_coi_at = now
            # Create notification for COI (RANK_2 admin)
            rank2_admin = AdminProfile.objects.filter(rank=AdminProfile.RANK_2).first()
            if rank2_admin:
                create_notification(
                    recipient=rank2_admin.user,
                    notification_type='SIGNED_COPY_FORWARDED',
                    title='Signed Copy Forwarded',
                    message=f'Signed copy for "{signed_copy.folder.title}" has been forwarded to COI.',
                    signed_copy=signed_copy
                )
        if form.cleaned_data.get('forward_to_dsas'):
            signed_copy.forwarded_to_dsas_at = now
            # Create notification for DSAS (RANK_1 admin)
            rank1_admin = AdminProfile.objects.filter(rank=AdminProfile.RANK_1).first()
            if rank1_admin:
                create_notification(
                    recipient=rank1_admin.user,
                    notification_type='SIGNED_COPY_FORWARDED',
                    title='Signed Copy Forwarded',
                    message=f'Signed copy for "{signed_copy.folder.title}" has been forwarded to DSAS.',
                    signed_copy=signed_copy
                )
        signed_copy.save()
        messages.success(request, 'Signed scanned copy uploaded.')
    else:
        messages.error(request, 'Signed scanned copy was not uploaded. Check the file and fields.')

    return redirect(f'{reverse("dashboard")}#signed-copies')


@login_required
def admin_dashboard(request):
    if not request.user.is_staff:
        return redirect_for_user(request.user)

    admin_rank = admin_rank_for(request.user)

    if handle_template_upload(request):
        return redirect('admin_dashboard')

    organizations = OrganizationProfile.objects.select_related('user').order_by('organization_name')
    notification_filter = {
        'status__in': ['SUBMITTED', 'RESUBMITTED'],
        'forwarded_to_admin_at__isnull': False,
    }
    if admin_rank == AdminProfile.RANK_2:
        notification_filter.update({
            'forwarded_to_rank1_at__isnull': True,
            'admin_notification_seen_at__isnull': True,
        })
        notification_seen_field = 'admin_notification_seen_at'
        notification_order = '-forwarded_to_admin_at'
    else:
        notification_filter.update({
            'forwarded_to_rank1_at__isnull': False,
            'rank1_notification_seen_at__isnull': True,
        })
        notification_seen_field = 'rank1_notification_seen_at'
        notification_order = '-forwarded_to_rank1_at'

    latest_notification = Document.objects.filter(
        **notification_filter,
    ).select_related(
        'user',
        'user__organizationprofile',
    ).order_by(notification_order).first()

    if latest_notification:
        Document.objects.filter(
            **notification_filter,
        ).update(**{notification_seen_field: timezone.now()})

    documents = admin_document_queryset_for(request.user).order_by('uploaded_at')
    folders = admin_folder_queryset_for(request.user).order_by('created_at')
    documented_user_ids = set(SubmissionFolder.objects.values_list('user_id', flat=True))
    organizations_without_documents = organizations.exclude(user_id__in=documented_user_ids)

    # Calculate status statistics based on admin rank
    if admin_rank == AdminProfile.RANK_2:
        # COI (RANK_2) specific statistics
        status_stats = {
            'total': documents.count(),
            'pending_review': documents.filter(status__in=['SUBMITTED', 'RESUBMITTED']).count(),
            'approved_by_coi': documents.filter(status='APPROVED_BY_COI').count(),
            'corrected': documents.filter(status='CORRECTED').count(),
            'forwarded_to_dsas': documents.filter(forwarded_to_rank1_at__isnull=False).count(),
            'ready_for_printing': documents.filter(status='READY_FOR_PRINTING').count(),
        }
    else:
        # DSAS (RANK_1) specific statistics
        status_stats = {
            'total': documents.count(),
            'pending_review': documents.filter(status='APPROVED_BY_COI').count(),
            'approved_by_dsas': documents.filter(status='READY_FOR_PRINTING').count(),
            'ready_for_printing': documents.filter(status='READY_FOR_PRINTING').count(),
            'corrected': documents.filter(status='CORRECTED').count(),
            'forwarded_from_coi': documents.filter(forwarded_to_rank1_at__isnull=False).count(),
        }

    # Prepare calendar events
    calendar_events = []
    for doc in documents:
        calendar_events.append({
            'date': doc.uploaded_at.strftime('%Y-%m-%d'),
            'title': doc.title,
            'status': doc.status
        })

    # Get notifications for the user
    notifications = Notification.objects.filter(recipient=request.user).order_by('-created_at')[:20]
    notifications_data = [
        {
            'id': n.id,
            'title': n.title,
            'message': n.message,
            'is_read': n.is_read,
            'created_at': n.created_at.isoformat()
        }
        for n in notifications
    ]

    # Get correction items created by admin or assigned to admin
    correction_items = CorrectionItem.objects.filter(
        Q(created_by=request.user) | Q(assigned_to=request.user)
    ).select_related('document', 'created_by', 'assigned_to').order_by('-priority', 'status', '-created_at')

    return render(request, 'documents/admin_dashboard.html', {
        'documents': documents,
        'folders': folders,
        'section_groups': build_section_groups(folders, include_empty=True),
        'organizations': organizations,
        'organizations_without_documents': organizations_without_documents,
        'latest_notification': latest_notification,
        'status_stats': status_stats,
        'calendar_events': json.dumps(calendar_events),
        'notifications_data': json.dumps(notifications_data),
        'correction_items': correction_items,
        'section_templates': template_queryset(),
        'signed_copies': signed_copy_queryset_for_admin(request.user),
        'admin_rank': admin_rank,
        'admin_rank_label': admin_rank_label_for(request.user),
        'rank1_admin_id': rank1_admin_id(),
    })


@login_required
def admin_edit_document(request, document_id):
    if not request.user.is_staff:
        return redirect_for_user(request.user)

    document = get_object_or_404(
        admin_document_queryset_for(request.user),
        pk=document_id,
    )
    hide_existing_corrections = (
        admin_rank_for(request.user) == AdminProfile.RANK_1
        and document.correction_added_by_rank2()
    )

    if request.method == 'POST':
        form = AdminDocumentForm(
            request.POST,
            request.FILES,
            instance=document,
            hide_existing_corrections=hide_existing_corrections,
            admin_rank=admin_rank_for(request.user),
        )
        if form.is_valid():
            document = form.save(reviewed_by=request.user)
            return redirect('admin_dashboard')
    else:
        form = AdminDocumentForm(
            instance=document,
            hide_existing_corrections=hide_existing_corrections,
            admin_rank=admin_rank_for(request.user),
        )

    return render(request, 'documents/admin_document_edit.html', {
        'document': document,
        'form': form,
        'admin_rank': admin_rank_for(request.user),
        'admin_rank_label': admin_rank_label_for(request.user),
        'rank1_admin_id': rank1_admin_id(),
    })


@login_required
@require_POST
def rank2_forward_document(request, document_id):
    if not request.user.is_staff or admin_rank_for(request.user) != AdminProfile.RANK_2:
        return redirect_for_user(request.user)

    document = get_object_or_404(
        admin_document_queryset_for(request.user),
        pk=document_id,
    )

    if document.is_forwardable_to_rank1():
        now = timezone.now()
        document.rank2_reviewed_by = request.user
        document.forwarded_to_rank1_at = now
        document.rank1_notification_seen_at = None
        document.save(update_fields=[
            'rank2_reviewed_by',
            'forwarded_to_rank1_at',
            'rank1_notification_seen_at',
            'status_updated_at',
        ])
        folder = document.folder
        if (
            folder
            and folder.forwarded_to_rank1_at is None
            and folder.documents.exists()
            and all(
                item.forwarded_to_rank1_at is not None
                for item in folder.documents.all()
            )
        ):
            folder.rank2_reviewed_by = request.user
            folder.forwarded_to_rank1_at = now
            folder.rank1_notification_seen_at = None
            folder.save(update_fields=[
                'rank2_reviewed_by',
                'forwarded_to_rank1_at',
                'rank1_notification_seen_at',
            ])

    return redirect('admin_dashboard')


@login_required
@require_POST
def rank2_forward_folder(request, folder_id):
    if not request.user.is_staff or admin_rank_for(request.user) != AdminProfile.RANK_2:
        return redirect_for_user(request.user)

    folder = get_object_or_404(
        admin_folder_queryset_for(request.user),
        pk=folder_id,
    )

    if folder.is_forwardable_to_rank1():
        now = timezone.now()
        folder.rank2_reviewed_by = request.user
        folder.forwarded_to_rank1_at = now
        folder.rank1_notification_seen_at = None
        folder.save(update_fields=[
            'rank2_reviewed_by',
            'forwarded_to_rank1_at',
            'rank1_notification_seen_at',
        ])
        folder.documents.exclude(status='CORRECTED').update(
            rank2_reviewed_by=request.user,
            forwarded_to_rank1_at=now,
            rank1_notification_seen_at=None,
            status_updated_at=now,
        )

    return redirect('admin_dashboard')


@login_required
def admin_organizations_list(request):
    if not request.user.is_staff:
        return redirect_for_user(request.user)

    organizations = OrganizationProfile.objects.select_related('user').order_by('organization_name')

    return render(request, 'documents/admin_organizations_list.html', {
        'organizations': organizations,
    })


@login_required
def admin_organization_overview(request, organization_id):
    if not request.user.is_staff:
        return redirect_for_user(request.user)

    organization = get_object_or_404(
        OrganizationProfile.objects.select_related('user'),
        pk=organization_id,
    )

    return render(request, 'documents/admin_organization_overview.html', build_overview_context(
        organization,
        can_edit=False,
        submissions_url='admin_dashboard',
    ))


@login_required
def admin_view_document(request, document_id):
    if not request.user.is_staff:
        return redirect_for_user(request.user)

    document = get_object_or_404(admin_document_queryset_for(request.user), pk=document_id)
    return FileResponse(
        document.uploaded_file.open('rb'),
        as_attachment=False,
        filename=document.uploaded_filename(),
        content_type='application/pdf',
    )


@login_required
def admin_download_document(request, document_id):
    if not request.user.is_staff:
        return redirect_for_user(request.user)

    document = get_object_or_404(admin_document_queryset_for(request.user), pk=document_id)
    response, error = document_docx_response(document)
    if error:
        messages.error(request, error)
        return redirect('admin_edit_document', document_id=document.id)
    return response


@login_required
def adviser_dashboard(request):
    adviser_profile = adviser_profile_for(request.user)
    if request.user.is_staff:
        return redirect('admin_dashboard')
    if not adviser_profile:
        return redirect('dashboard')

    documents = Document.objects.filter(
        user=adviser_profile.organization.user,
    ).select_related(
        'user',
        'user__organizationprofile',
        'folder',
    ).order_by('uploaded_at')
    folders = SubmissionFolder.objects.filter(
        user=adviser_profile.organization.user,
    ).select_related(
        'user',
        'user__organizationprofile',
    ).prefetch_related('documents').order_by('created_at')

    latest_notification = documents.filter(
        status__in=['SUBMITTED', 'RESUBMITTED'],
        adviser_status='PENDING',
    ).order_by('-uploaded_at').first()

    # Calculate status statistics for Adviser
    status_stats = {
        'total': documents.count(),
        'pending_review': documents.filter(adviser_status='PENDING').count(),
        'approved_by_adviser': documents.filter(adviser_status='APPROVED').count(),
        'corrected': documents.filter(status='CORRECTED').count(),
        'forwarded_to_coi': documents.filter(forwarded_to_admin_at__isnull=False, forwarded_to_rank1_at__isnull=True).count(),
        'forwarded_to_dsas': documents.filter(forwarded_to_rank1_at__isnull=False).count(),
    }

    # Prepare calendar events
    calendar_events = []
    for doc in documents:
        calendar_events.append({
            'date': doc.uploaded_at.strftime('%Y-%m-%d'),
            'title': doc.title,
            'status': doc.status
        })

    # Get notifications for the user
    notifications = Notification.objects.filter(recipient=request.user).order_by('-created_at')[:20]
    notifications_data = [
        {
            'id': n.id,
            'title': n.title,
            'message': n.message,
            'is_read': n.is_read,
            'created_at': n.created_at.isoformat()
        }
        for n in notifications
    ]

    # Get correction items created by adviser or assigned to adviser
    correction_items = CorrectionItem.objects.filter(
        Q(created_by=request.user) | Q(assigned_to=request.user)
    ).select_related('document', 'created_by', 'assigned_to').order_by('-priority', 'status', '-created_at')

    return render(request, 'documents/adviser_dashboard.html', {
        'adviser_profile': adviser_profile,
        'documents': documents,
        'folders': folders,
        'section_groups': build_section_groups(folders, include_empty=True),
        'latest_notification': latest_notification,
        'status_stats': status_stats,
        'calendar_events': json.dumps(calendar_events),
        'notifications_data': json.dumps(notifications_data),
        'correction_items': correction_items,
        'signed_copies': SignedScannedCopy.objects.filter(
            user=adviser_profile.organization.user,
            forwarded_to_adviser_at__isnull=False,
        ).select_related('folder'),
        **build_overview_context(
            adviser_profile.organization,
            can_edit=False,
            submissions_url='adviser_dashboard',
        ),
    })


@login_required
def adviser_edit_document(request, document_id):
    adviser_profile = adviser_profile_for(request.user)
    if request.user.is_staff:
        return redirect('admin_dashboard')
    if not adviser_profile:
        return redirect('dashboard')

    document = get_object_or_404(
        Document.objects.select_related('user', 'user__organizationprofile'),
        pk=document_id,
        user=adviser_profile.organization.user,
    )

    if request.method == 'POST':
        form = AdviserDocumentForm(request.POST, request.FILES, instance=document)
        if form.is_valid():
            form.save(adviser_user=request.user)
            return redirect('adviser_dashboard')
    else:
        form = AdviserDocumentForm(instance=document)

    return render(request, 'documents/adviser_document_edit.html', {
        'document': document,
        'form': form,
    })


@login_required
@require_POST
def adviser_forward_document(request, document_id):
    adviser_profile = adviser_profile_for(request.user)
    if request.user.is_staff:
        return redirect('admin_dashboard')
    if not adviser_profile:
        return redirect('dashboard')

    document = get_object_or_404(
        Document,
        pk=document_id,
        user=adviser_profile.organization.user,
        adviser_status='APPROVED',
    )

    # Allow forwarding individual documents even if folder is already forwarded
    if document.status != 'CORRECTED' and document.forwarded_to_admin_at is None:
        now = timezone.now()
        forward_target = request.POST.get('forward_target', 'coi')
        
        if forward_target == 'dsas':
            # Forward directly to DSAS (Rank 1)
            document.forwarded_to_admin_at = now
            document.admin_notification_seen_at = None
            document.rank2_reviewed_by = None
            document.forwarded_to_rank1_at = now
            document.rank1_notification_seen_at = None
            document.save(update_fields=[
                'forwarded_to_admin_at',
                'admin_notification_seen_at',
                'rank2_reviewed_by',
                'forwarded_to_rank1_at',
                'rank1_notification_seen_at',
                'status_updated_at',
            ])
        else:
            # Forward to COI (Rank 2)
            document.forwarded_to_admin_at = now
            document.admin_notification_seen_at = None
            document.rank2_reviewed_by = None
            document.forwarded_to_rank1_at = None
            document.rank1_notification_seen_at = None
            document.save(update_fields=[
                'forwarded_to_admin_at',
                'admin_notification_seen_at',
                'rank2_reviewed_by',
                'forwarded_to_rank1_at',
                'rank1_notification_seen_at',
                'status_updated_at',
            ])
        
        folder = document.folder
        if (
            folder
            and folder.forwarded_to_admin_at is None
            and folder.documents.exists()
            and all(
                item.forwarded_to_admin_at is not None
                for item in folder.documents.all()
            )
        ):
            folder.forwarded_to_admin_at = now
            folder.admin_notification_seen_at = None
            folder.rank2_reviewed_by = None
            folder.forwarded_to_rank1_at = None
            folder.rank1_notification_seen_at = None
            folder.save(update_fields=[
                'forwarded_to_admin_at',
                'admin_notification_seen_at',
                'rank2_reviewed_by',
                'forwarded_to_rank1_at',
                'rank1_notification_seen_at',
            ])

    return redirect('adviser_dashboard')


@login_required
@require_POST
def adviser_forward_folder(request, folder_id):
    adviser_profile = adviser_profile_for(request.user)
    if request.user.is_staff:
        return redirect('admin_dashboard')
    if not adviser_profile:
        return redirect('dashboard')

    folder = get_object_or_404(
        SubmissionFolder.objects.prefetch_related('documents'),
        pk=folder_id,
        user=adviser_profile.organization.user,
    )

    if folder.is_forwardable_to_admin():
        now = timezone.now()
        forward_target = request.POST.get('forward_target', 'coi')
        
        # Check if this is a re-forward (folder already forwarded)
        is_reforward = folder.forwarded_to_admin_at is not None
        
        if forward_target == 'dsas':
            # Forward directly to DSAS (Rank 1)
            folder.forwarded_to_admin_at = now
            folder.admin_notification_seen_at = None
            folder.rank2_reviewed_by = None
            folder.forwarded_to_rank1_at = now
            folder.rank1_notification_seen_at = None
            folder.save(update_fields=[
                'forwarded_to_admin_at',
                'admin_notification_seen_at',
                'rank2_reviewed_by',
                'forwarded_to_rank1_at',
                'rank1_notification_seen_at',
            ])
            
            # If re-forwarding, only update documents that haven't been forwarded yet
            if is_reforward:
                folder.documents.filter(forwarded_to_admin_at__isnull=True).update(
                    forwarded_to_admin_at=now,
                    admin_notification_seen_at=None,
                    rank2_reviewed_by=None,
                    forwarded_to_rank1_at=now,
                    rank1_notification_seen_at=None,
                    status_updated_at=now,
                )
            else:
                folder.documents.update(
                    forwarded_to_admin_at=now,
                    admin_notification_seen_at=None,
                    rank2_reviewed_by=None,
                    forwarded_to_rank1_at=now,
                    rank1_notification_seen_at=None,
                    status_updated_at=now,
                )
        else:
            # Forward to COI (Rank 2)
            folder.forwarded_to_admin_at = now
            folder.admin_notification_seen_at = None
            folder.rank2_reviewed_by = None
            folder.forwarded_to_rank1_at = None
            folder.rank1_notification_seen_at = None
            folder.save(update_fields=[
                'forwarded_to_admin_at',
                'admin_notification_seen_at',
                'rank2_reviewed_by',
                'forwarded_to_rank1_at',
                'rank1_notification_seen_at',
            ])
            
            # If re-forwarding, only update documents that haven't been forwarded yet
            if is_reforward:
                folder.documents.filter(forwarded_to_admin_at__isnull=True).update(
                    forwarded_to_admin_at=now,
                    admin_notification_seen_at=None,
                    rank2_reviewed_by=None,
                    forwarded_to_rank1_at=None,
                    rank1_notification_seen_at=None,
                    status_updated_at=now,
                )
            else:
                folder.documents.update(
                    forwarded_to_admin_at=now,
                    admin_notification_seen_at=None,
                    rank2_reviewed_by=None,
                    forwarded_to_rank1_at=None,
                    rank1_notification_seen_at=None,
                    status_updated_at=now,
                )

    return redirect('adviser_dashboard')


@login_required
def adviser_view_document(request, document_id):
    adviser_profile = adviser_profile_for(request.user)
    if request.user.is_staff:
        return redirect('admin_dashboard')
    if not adviser_profile:
        return redirect('dashboard')

    document = get_object_or_404(Document, pk=document_id, user=adviser_profile.organization.user)
    return FileResponse(
        document.uploaded_file.open('rb'),
        as_attachment=False,
        filename=document.uploaded_filename(),
        content_type='application/pdf',
    )


@login_required
def adviser_download_document(request, document_id):
    adviser_profile = adviser_profile_for(request.user)
    if request.user.is_staff:
        return redirect('admin_dashboard')
    if not adviser_profile:
        return redirect('dashboard')

    document = get_object_or_404(Document, pk=document_id, user=adviser_profile.organization.user)
    response, error = document_docx_response(document)
    if error:
        messages.error(request, error)
        return redirect('adviser_edit_document', document_id=document.id)
    return response


@login_required
@require_POST
def mark_notification_read(request, notification_id):
    notification = get_object_or_404(Notification, pk=notification_id, recipient=request.user)
    notification.is_read = True
    notification.save()
    return JsonResponse({'success': True})


@login_required
@require_POST
def mark_all_notifications_read(request):
    Notification.objects.filter(recipient=request.user, is_read=False).update(is_read=True)
    return JsonResponse({'success': True})


@login_required
@require_POST
def clear_all_notifications(request):
    Notification.objects.filter(recipient=request.user).delete()
    return JsonResponse({'success': True})


@login_required
def add_correction_item(request, document_id):
    """Add a correction item to a document"""
    document = get_object_or_404(Document, pk=document_id)
    
    # Check if user has permission (adviser or admin)
    adviser_profile = adviser_profile_for(request.user)
    admin_profile = admin_profile_for(request.user)
    
    if not (adviser_profile or admin_profile):
        messages.error(request, 'You do not have permission to add corrections.')
        return redirect('dashboard')
    
    if request.method == 'POST':
        form = CorrectionItemForm(request.POST)
        if form.is_valid():
            correction = form.save(commit=False)
            correction.document = document
            correction.created_by = request.user
            correction.save()
            
            # Create notification for organization user
            if correction.assigned_to:
                create_notification(
                    recipient=correction.assigned_to,
                    notification_type='FILE_CORRECTED',
                    title='New Correction Assigned',
                    message=f'A new correction has been assigned to you for document "{document.title}".',
                    document=document
                )
            
            messages.success(request, 'Correction item added successfully.')
            
            # Redirect back to appropriate dashboard
            if request.user.is_staff:
                return redirect('admin_dashboard')
            else:
                return redirect('adviser_dashboard')
    else:
        form = CorrectionItemForm()
    
    return render(request, 'documents/correction_item_form.html', {
        'form': form,
        'document': document,
        'action': 'Add',
    })


@login_required
def edit_correction_item(request, correction_id):
    """Edit an existing correction item"""
    correction = get_object_or_404(CorrectionItem, pk=correction_id)
    
    # Check if user has permission (creator or assigned user)
    if correction.created_by != request.user and correction.assigned_to != request.user:
        messages.error(request, 'You do not have permission to edit this correction.')
        return redirect('dashboard')
    
    if request.method == 'POST':
        form = CorrectionItemForm(request.POST, instance=correction)
        if form.is_valid():
            form.save()
            messages.success(request, 'Correction item updated successfully.')
            
            # Redirect back to appropriate dashboard
            if request.user.is_staff:
                return redirect('admin_dashboard')
            else:
                return redirect('adviser_dashboard')
    else:
        form = CorrectionItemForm(instance=correction)
    
    return render(request, 'documents/correction_item_form.html', {
        'form': form,
        'correction': correction,
        'action': 'Edit',
    })


@login_required
@require_POST
def resolve_correction_item(request, correction_id):
    """Mark a correction item as resolved"""
    correction = get_object_or_404(CorrectionItem, pk=correction_id)
    
    # Only assigned user or creator can resolve
    if correction.assigned_to != request.user and correction.created_by != request.user:
        messages.error(request, 'You do not have permission to resolve this correction.')
        return redirect('dashboard')
    
    correction.status = 'RESOLVED'
    correction.resolved_at = timezone.now()
    correction.resolved_by = request.user
    correction.resolution_notes = request.POST.get('resolution_notes', '')
    correction.save()
    
    # Create notification for the creator
    if correction.created_by != request.user:
        create_notification(
            recipient=correction.created_by,
            notification_type='FILE_CORRECTED',
            title='Correction Resolved',
            message=f'Correction for "{correction.document.title if correction.document else correction.folder.title}" has been resolved.',
            document=correction.document
        )
    
    messages.success(request, 'Correction item marked as resolved.')
    
    # Redirect back to appropriate dashboard
    if request.user.is_staff:
        return redirect('admin_dashboard')
    else:
        return redirect('adviser_dashboard')


@login_required
@require_POST
def delete_correction_item(request, correction_id):
    """Delete a correction item"""
    correction = get_object_or_404(CorrectionItem, pk=correction_id)
    
    # Only creator can delete
    if correction.created_by != request.user:
        messages.error(request, 'You do not have permission to delete this correction.')
        return redirect('dashboard')
    
    correction.delete()
    messages.success(request, 'Correction item deleted successfully.')
    
    # Redirect back to appropriate dashboard
    if request.user.is_staff:
        return redirect('admin_dashboard')
    else:
        return redirect('adviser_dashboard')


