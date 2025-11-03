from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.views.generic import ListView, CreateView, UpdateView, DeleteView, DetailView
from django.urls import reverse_lazy, reverse
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.utils import timezone
import json

from .models import ChecklistTemplate, ProjectChecklist, Project, Notification
from .forms import ChecklistTemplateForm, ProjectChecklistSelectForm
from .user_roles import has_role, UserRole


class ChecklistTemplateListView(LoginRequiredMixin, ListView):
    """チェックリストテンプレート一覧 - Phase 8"""
    model = ChecklistTemplate
    template_name = 'order_management/checklist/template_list.html'
    context_object_name = 'templates'
    paginate_by = 20

    def get_queryset(self):
        queryset = ChecklistTemplate.objects.all().order_by('work_type', 'name')

        # 施工種別フィルタ
        work_type = self.request.GET.get('work_type')
        if work_type:
            queryset = queryset.filter(work_type__icontains=work_type)

        # アクティブフィルタ
        is_active = self.request.GET.get('is_active')
        if is_active == 'true':
            queryset = queryset.filter(is_active=True)
        elif is_active == 'false':
            queryset = queryset.filter(is_active=False)

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['work_type_filter'] = self.request.GET.get('work_type', '')
        context['is_active_filter'] = self.request.GET.get('is_active', '')
        return context


class ChecklistTemplateCreateView(LoginRequiredMixin, CreateView):
    """チェックリストテンプレート作成 - Phase 8"""
    model = ChecklistTemplate
    form_class = ChecklistTemplateForm
    template_name = 'order_management/checklist/template_form.html'
    success_url = reverse_lazy('order_management:checklist_template_list')

    def form_valid(self, form):
        # JSONからチェック項目を取得
        items_json = self.request.POST.get('items_json', '[]')
        try:
            items = json.loads(items_json)
            form.instance.items = items
        except json.JSONDecodeError:
            messages.error(self.request, 'チェック項目の形式が正しくありません。')
            return self.form_invalid(form)

        messages.success(self.request, 'チェックリストテンプレートを作成しました。')
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['is_create'] = True
        return context


class ChecklistTemplateUpdateView(LoginRequiredMixin, UpdateView):
    """チェックリストテンプレート編集 - Phase 8"""
    model = ChecklistTemplate
    form_class = ChecklistTemplateForm
    template_name = 'order_management/checklist/template_form.html'
    success_url = reverse_lazy('order_management:checklist_template_list')

    def form_valid(self, form):
        # JSONからチェック項目を取得
        items_json = self.request.POST.get('items_json', '[]')
        try:
            items = json.loads(items_json)
            form.instance.items = items
        except json.JSONDecodeError:
            messages.error(self.request, 'チェック項目の形式が正しくありません。')
            return self.form_invalid(form)

        messages.success(self.request, 'チェックリストテンプレートを更新しました。')
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['is_create'] = False
        context['items'] = self.object.items
        return context


class ChecklistTemplateDeleteView(LoginRequiredMixin, DeleteView):
    """チェックリストテンプレート削除 - Phase 8"""
    model = ChecklistTemplate
    template_name = 'order_management/checklist/template_confirm_delete.html'
    success_url = reverse_lazy('order_management:checklist_template_list')

    def delete(self, request, *args, **kwargs):
        messages.success(request, 'チェックリストテンプレートを削除しました。')
        return super().delete(request, *args, **kwargs)


class ProjectChecklistCreateView(LoginRequiredMixin, CreateView):
    """案件チェックリスト作成（テンプレートからインスタンス化）- Phase 8"""
    model = ProjectChecklist
    template_name = 'order_management/checklist/project_checklist_select.html'
    form_class = ProjectChecklistSelectForm

    def dispatch(self, request, *args, **kwargs):
        self.project = get_object_or_404(Project, pk=self.kwargs['project_pk'])
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['work_type'] = self.project.work_type
        return kwargs

    def form_valid(self, form):
        template = form.cleaned_data['template']

        # テンプレートからチェックリストをインスタンス化
        checklist = ProjectChecklist.objects.create(
            project=self.project,
            template=template,
            items=[
                {
                    'name': item['name'],
                    'description': item.get('description', ''),
                    'order': item.get('order', idx),
                    'completed': False,
                    'notes': '',
                    'completed_by': None,
                    'completed_at': None
                }
                for idx, item in enumerate(template.items, 1)
            ]
        )

        messages.success(self.request, f'チェックリスト「{template.name}」を案件に追加しました。')
        return redirect('order_management:project_checklist_detail',
                       project_pk=self.project.pk,
                       checklist_pk=checklist.pk)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['project'] = self.project
        return context


class ProjectChecklistDetailView(LoginRequiredMixin, DetailView):
    """案件チェックリスト詳細・編集 - Phase 8"""
    model = ProjectChecklist
    template_name = 'order_management/checklist/project_checklist_detail.html'
    context_object_name = 'checklist'
    pk_url_kwarg = 'checklist_pk'

    def get_queryset(self):
        return ProjectChecklist.objects.filter(
            project_id=self.kwargs['project_pk']
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['project'] = self.object.project
        context['completion_rate'] = self.object.get_completion_rate()
        return context


@login_required
@require_POST
def project_checklist_update_item(request, project_pk, checklist_pk):
    """チェックリスト項目の更新（API）- Phase 8"""
    checklist = get_object_or_404(
        ProjectChecklist,
        pk=checklist_pk,
        project_id=project_pk
    )

    try:
        data = json.loads(request.body)
        item_index = data.get('item_index')
        completed = data.get('completed', False)
        notes = data.get('notes', '')

        if item_index is None or item_index >= len(checklist.items):
            return JsonResponse({'success': False, 'error': '無効な項目です'}, status=400)

        # 項目を更新
        item = checklist.items[item_index]
        item['completed'] = completed
        item['notes'] = notes

        if completed:
            item['completed_by'] = request.user.id
            item['completed_at'] = timezone.now().isoformat()
        else:
            item['completed_by'] = None
            item['completed_at'] = None

        checklist.save()

        # 全項目完了チェック
        all_completed = all(item.get('completed', False) for item in checklist.items)
        if all_completed and not checklist.completed_at:
            checklist.completed_at = timezone.now()
            checklist.save()

            # プロジェクトマネージャーに通知
            if checklist.project.project_manager:
                Notification.objects.create(
                    user=checklist.project.project_manager,
                    notification_type='checklist_completed',
                    title='チェックリスト完了',
                    message=f'案件「{checklist.project.site_name}」のチェックリストが完了しました。',
                    related_project=checklist.project
                )

        return JsonResponse({
            'success': True,
            'completion_rate': checklist.get_completion_rate(),
            'all_completed': all_completed
        })

    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@login_required
def project_checklist_delete(request, project_pk, checklist_pk):
    """案件チェックリスト削除 - Phase 8"""
    checklist = get_object_or_404(
        ProjectChecklist,
        pk=checklist_pk,
        project_id=project_pk
    )

    if request.method == 'POST':
        checklist.delete()
        messages.success(request, 'チェックリストを削除しました。')
        return redirect('order_management:project_detail', pk=project_pk)

    return render(request, 'order_management/checklist/project_checklist_confirm_delete.html', {
        'checklist': checklist,
        'project': checklist.project
    })
