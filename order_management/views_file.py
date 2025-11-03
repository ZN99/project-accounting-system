from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import FileResponse, Http404
from django.views.decorators.http import require_POST
import os

from .models import Project, ProjectFile
from .forms import ProjectFileUploadForm


@login_required
def project_file_upload(request, project_pk):
    """案件ファイルアップロード - Phase 5"""
    project = get_object_or_404(Project, pk=project_pk)

    if request.method == 'POST':
        form = ProjectFileUploadForm(request.POST, request.FILES)
        if form.is_valid():
            project_file = form.save(commit=False)
            project_file.project = project
            project_file.uploaded_by = request.user

            # ファイル情報を自動取得
            uploaded_file = request.FILES['file']
            project_file.file_name = uploaded_file.name
            project_file.file_size = uploaded_file.size
            project_file.file_type = uploaded_file.content_type

            project_file.save()
            messages.success(request, f'ファイル「{uploaded_file.name}」をアップロードしました。')
            return redirect('order_management:project_detail', pk=project_pk)
    else:
        form = ProjectFileUploadForm()

    return render(request, 'order_management/file/file_upload.html', {
        'form': form,
        'project': project
    })


@login_required
def project_file_download(request, project_pk, file_pk):
    """案件ファイルダウンロード - Phase 5"""
    project_file = get_object_or_404(
        ProjectFile,
        pk=file_pk,
        project_id=project_pk
    )

    try:
        return FileResponse(
            project_file.file.open('rb'),
            as_attachment=True,
            filename=project_file.file_name
        )
    except FileNotFoundError:
        raise Http404("ファイルが見つかりません")


@login_required
@require_POST
def project_file_delete(request, project_pk, file_pk):
    """案件ファイル削除 - Phase 5"""
    project_file = get_object_or_404(
        ProjectFile,
        pk=file_pk,
        project_id=project_pk
    )

    file_name = project_file.file_name

    # ファイルを物理削除
    if project_file.file:
        if os.path.isfile(project_file.file.path):
            os.remove(project_file.file.path)

    # データベースから削除
    project_file.delete()

    messages.success(request, f'ファイル「{file_name}」を削除しました。')
    return redirect('order_management:project_detail', pk=project_pk)
