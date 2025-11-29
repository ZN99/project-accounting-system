from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import FileResponse, Http404, JsonResponse
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
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


@login_required
@require_POST
def step_file_upload_ajax(request, project_pk):
    """ステップ固有のファイルアップロード（AJAX）"""
    try:
        project = get_object_or_404(Project, pk=project_pk)

        if 'file' not in request.FILES:
            return JsonResponse({'success': False, 'error': 'ファイルが選択されていません'}, status=400)

        uploaded_file = request.FILES['file']
        related_step = request.POST.get('related_step', '')
        description = request.POST.get('description', '')

        # ファイルタイプを検証
        allowed_types = [
            'application/pdf',
            'application/vnd.ms-excel',
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            'application/msword',
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            'image/jpeg',
            'image/png',
            'image/jpg'
        ]

        if uploaded_file.content_type not in allowed_types:
            return JsonResponse({
                'success': False,
                'error': f'サポートされていないファイル形式です。PDF, Excel, Word, 画像ファイルのみアップロード可能です。'
            }, status=400)

        # ファイルサイズを検証（10MB以下）
        max_size = 10 * 1024 * 1024  # 10MB
        if uploaded_file.size > max_size:
            return JsonResponse({
                'success': False,
                'error': 'ファイルサイズは10MB以下にしてください'
            }, status=400)

        # ProjectFileを作成
        project_file = ProjectFile(
            project=project,
            file=uploaded_file,
            file_name=uploaded_file.name,
            file_size=uploaded_file.size,
            file_type=uploaded_file.content_type,
            description=description,
            related_step=related_step,
            uploaded_by=request.user
        )
        project_file.save()

        return JsonResponse({
            'success': True,
            'file': {
                'id': project_file.id,
                'file_name': project_file.file_name,
                'file_size': project_file.get_file_size_display(),
                'file_type': project_file.file_type,
                'uploaded_at': project_file.uploaded_at.strftime('%Y-%m-%d %H:%M'),
                'uploaded_by': project_file.uploaded_by.username if project_file.uploaded_by else '不明'
            }
        })

    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@login_required
@require_POST
def step_file_delete_ajax(request, project_pk, file_pk):
    """ステップファイル削除（AJAX）"""
    try:
        project_file = get_object_or_404(
            ProjectFile,
            pk=file_pk,
            project_id=project_pk
        )

        file_name = project_file.file_name

        # ファイルを物理削除
        if project_file.file and os.path.isfile(project_file.file.path):
            os.remove(project_file.file.path)

        # データベースから削除
        project_file.delete()

        return JsonResponse({
            'success': True,
            'message': f'ファイル「{file_name}」を削除しました'
        })

    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)
