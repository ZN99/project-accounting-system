from django.shortcuts import render, get_object_or_404, redirect
from django.views.generic import ListView, CreateView, UpdateView, DeleteView, DetailView
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.urls import reverse_lazy
from django.db.models import Q, Count, Max
from django.db import models
from django.http import JsonResponse
from .models import ClientCompany, Project, ContactPerson
from .forms import ClientCompanyForm, ClientCompanyFilterForm
from .user_roles import has_role, UserRole


class ClientCompanyListView(LoginRequiredMixin, ListView):
    """元請会社一覧表示 - Phase 8"""
    model = ClientCompany
    template_name = 'order_management/client_company/client_company_list.html'
    context_object_name = 'client_companies'
    paginate_by = 20

    def dispatch(self, request, *args, **kwargs):
        # 管理部・役員のみアクセス可能
        if not (has_role(request.user, UserRole.EXECUTIVE) or has_role(request.user, UserRole.COORDINATION_DEPT)):
            raise PermissionDenied("元請会社情報へのアクセス権限がありません。")
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        queryset = ClientCompany.objects.prefetch_related('contact_persons').annotate(
            project_count=Count('projects')
        ).order_by('-created_at')

        # フィルタリング
        is_active = self.request.GET.get('is_active')
        search = self.request.GET.get('search')

        if is_active == 'true':
            queryset = queryset.filter(is_active=True)
        elif is_active == 'false':
            queryset = queryset.filter(is_active=False)

        if search:
            queryset = queryset.filter(
                Q(company_name__icontains=search) |
                Q(contact_persons__name__icontains=search)
            ).distinct()

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['filter_form'] = ClientCompanyFilterForm(self.request.GET)

        # 統計情報
        context['total_companies'] = ClientCompany.objects.count()
        context['active_companies'] = ClientCompany.objects.filter(is_active=True).count()

        return context


class ClientCompanyDetailView(LoginRequiredMixin, DetailView):
    """元請会社詳細表示 - Phase 8"""
    model = ClientCompany
    template_name = 'order_management/client_company/client_company_detail.html'
    context_object_name = 'company'

    def dispatch(self, request, *args, **kwargs):
        # 管理部・役員のみアクセス可能
        if not (has_role(request.user, UserRole.EXECUTIVE) or has_role(request.user, UserRole.COORDINATION_DEPT)):
            raise PermissionDenied("元請会社情報へのアクセス権限がありません。")
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        from datetime import datetime, timedelta
        from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
        import json

        context = super().get_context_data(**kwargs)

        # 関連案件
        company = self.get_object()

        # ページネーション設定
        page = self.request.GET.get('page', 1)
        per_page = self.request.GET.get('per_page', 10)

        # per_pageのバリデーション
        try:
            per_page = int(per_page)
            if per_page not in [10, 25, 50, 100]:
                per_page = 10
        except (ValueError, TypeError):
            per_page = 10

        # 案件一覧を取得
        all_projects = company.projects.all().order_by('-created_at')

        # ページネーター作成
        paginator = Paginator(all_projects, per_page)

        try:
            projects_page = paginator.page(page)
        except PageNotAnInteger:
            projects_page = paginator.page(1)
        except EmptyPage:
            projects_page = paginator.page(paginator.num_pages)

        context['projects_page'] = projects_page
        context['per_page'] = per_page
        context['total_projects'] = company.projects.count()
        context['active_projects'] = company.projects.exclude(project_status='完工').count()

        # 担当者一覧
        context['contact_persons'] = company.contact_persons.all()

        # 期間フィルタ（GETパラメータから取得）
        start_date = self.request.GET.get('start_date')
        end_date = self.request.GET.get('end_date')

        # デフォルトは全期間
        start_date_obj = None
        end_date_obj = None

        if start_date:
            try:
                start_date_obj = datetime.strptime(start_date, '%Y-%m-%d')
            except ValueError:
                pass

        if end_date:
            try:
                end_date_obj = datetime.strptime(end_date, '%Y-%m-%d')
            except ValueError:
                pass

        # 統計計算
        stats = company.get_statistics(start_date=start_date_obj, end_date=end_date_obj)
        context['statistics'] = stats

        # レーダーチャート用データ（JSON形式）
        radar_data = {
            'labels': ['累計売上', '平均売上', '平均利益率', '対応しやすさ', '作業しやすさ'],
            'data': [
                stats['total_sales_score'],
                stats['avg_sales_score'],
                stats['profit_margin_score'],
                stats['response_ease_score'],
                stats['work_ease_score'],
            ]
        }
        context['radar_data_json'] = json.dumps(radar_data)

        # フィルタ値を保持
        context['start_date'] = start_date or ''
        context['end_date'] = end_date or ''

        # 評価基準を追加
        from .models import RatingCriteria
        context['rating_criteria'] = RatingCriteria.get_criteria()

        return context


class ClientCompanyCreateView(LoginRequiredMixin, CreateView):
    """元請会社新規登録 - Phase 8"""
    model = ClientCompany
    form_class = ClientCompanyForm
    template_name = 'order_management/client_company/client_company_form.html'
    success_url = reverse_lazy('order_management:client_company_list')

    def dispatch(self, request, *args, **kwargs):
        # 管理部・役員のみアクセス可能
        if not (has_role(request.user, UserRole.EXECUTIVE) or has_role(request.user, UserRole.COORDINATION_DEPT)):
            raise PermissionDenied("元請会社情報へのアクセス権限がありません。")
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        messages.success(self.request, f'元請会社「{form.instance.company_name}」を登録しました。')
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = '元請会社新規登録'
        context['submit_text'] = '登録する'
        return context


class ClientCompanyUpdateView(LoginRequiredMixin, UpdateView):
    """元請会社編集 - Phase 8"""
    model = ClientCompany
    form_class = ClientCompanyForm
    template_name = 'order_management/client_company/client_company_form.html'
    success_url = reverse_lazy('order_management:client_company_list')

    def dispatch(self, request, *args, **kwargs):
        # 管理部・役員のみアクセス可能
        if not (has_role(request.user, UserRole.EXECUTIVE) or has_role(request.user, UserRole.COORDINATION_DEPT)):
            raise PermissionDenied("元請会社情報へのアクセス権限がありません。")
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        messages.success(self.request, f'元請会社「{form.instance.company_name}」を更新しました。')
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = '元請会社編集'
        context['submit_text'] = '更新する'
        return context


class ClientCompanyDeleteView(LoginRequiredMixin, DeleteView):
    """元請会社削除 - Phase 8"""
    model = ClientCompany
    template_name = 'order_management/client_company/client_company_confirm_delete.html'
    success_url = reverse_lazy('order_management:client_company_list')

    def dispatch(self, request, *args, **kwargs):
        # 役員のみアクセス可能（削除は慎重に）
        if not has_role(request.user, UserRole.EXECUTIVE):
            raise PermissionDenied("元請会社の削除権限がありません。")
        return super().dispatch(request, *args, **kwargs)

    def delete(self, request, *args, **kwargs):
        obj = self.get_object()
        messages.success(request, f'元請会社「{obj.company_name}」を削除しました。')
        return super().delete(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        company = self.get_object()
        context['related_projects_count'] = company.projects.count()
        return context


@login_required
def client_company_api(request, company_id):
    """元請会社詳細API - Phase 8

    案件登録フォームで元請会社選択時に、
    鍵受け渡し場所などの情報を取得するためのAPI
    """
    try:
        company = ClientCompany.objects.prefetch_related('contact_persons').get(pk=company_id, is_active=True)

        # 主担当者を取得
        primary_contact = company.contact_persons.filter(is_primary=True).first()
        if not primary_contact:
            primary_contact = company.contact_persons.first()

        return JsonResponse({
            'success': True,
            'data': {
                'id': company.id,
                'company_name': company.company_name,
                'contact_person': primary_contact.name if primary_contact else '',
                'email': primary_contact.email if primary_contact else '',
                'phone': primary_contact.phone if primary_contact else '',
                'default_key_handover_location': company.default_key_handover_location,
                'key_handover_notes': company.key_handover_notes,
                'approval_threshold': float(company.approval_threshold),
                'special_notes': company.special_notes,
            }
        })
    except ClientCompany.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': '元請会社が見つかりません'
        }, status=404)


@login_required
def client_company_list_ajax(request):
    """元請会社一覧取得API - AJAX用

    元請管理パネルで最新の元請会社一覧を取得する
    """
    try:
        companies = ClientCompany.objects.prefetch_related('contact_persons').all().order_by('-created_at')

        companies_data = []
        for company in companies:
            # 主担当者を取得
            primary_contact = company.contact_persons.filter(is_primary=True).first()
            if not primary_contact:
                primary_contact = company.contact_persons.first()

            companies_data.append({
                'id': company.id,
                'company_name': company.company_name,
                'contact_person': primary_contact.name if primary_contact else '',
                'email': primary_contact.email if primary_contact else '',
                'phone': primary_contact.phone if primary_contact else '',
                'address': company.address or '',
                'website': '',  # websiteフィールドは削除されました
                'payment_cycle': company.payment_cycle or '',
                'payment_cycle_label': company.get_payment_cycle_display() if company.payment_cycle else '',
                'closing_day': company.closing_day,
                'payment_day': company.payment_day,
                'default_key_handover_location': company.default_key_handover_location or '',
                'key_handover_notes': company.key_handover_notes or '',
                'special_notes': company.special_notes or '',
                'is_active': company.is_active,
                'created_at': company.created_at.strftime('%Y-%m-%d %H:%M:%S') if hasattr(company, 'created_at') else '',
            })

        return JsonResponse({
            'success': True,
            'companies': companies_data
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@login_required
def client_company_create_ajax(request):
    """元請会社AJAX作成 - モーダルから作成

    案件登録中に元請会社を作成するためのAJAXエンドポイント
    """
    if request.method != 'POST':
        return JsonResponse({
            'success': False,
            'error': 'POSTリクエストのみ対応しています'
        }, status=405)

    # 権限チェック
    if not (has_role(request.user, UserRole.EXECUTIVE) or has_role(request.user, UserRole.COORDINATION_DEPT)):
        return JsonResponse({
            'success': False,
            'error': '元請会社の作成権限がありません'
        }, status=403)

    form = ClientCompanyForm(request.POST, request.FILES)

    if form.is_valid():
        company = form.save()

        # 主担当者を取得
        primary_contact = company.contact_persons.filter(is_primary=True).first()
        if not primary_contact:
            primary_contact = company.contact_persons.first()

        # ファイルURLを取得
        completion_template_url = ''
        if company.completion_report_template:
            try:
                completion_template_url = company.completion_report_template.url
            except:
                completion_template_url = ''

        # 成功時のレスポンス
        return JsonResponse({
            'success': True,
            'company': {
                'id': company.id,
                'company_name': company.company_name,
                'contact_person': primary_contact.name if primary_contact else '',
                'email': primary_contact.email if primary_contact else '',
                'phone': primary_contact.phone if primary_contact else '',
                'address': company.address or '',
                'website': '',  # websiteフィールドは削除されました
                'payment_cycle': company.payment_cycle or '',
                'payment_cycle_display': company.get_payment_cycle_display() if company.payment_cycle else '',
                'closing_day': company.closing_day,
                'payment_day': company.payment_day,
                'default_key_handover_location': company.default_key_handover_location or '',
                'key_handover_notes': company.key_handover_notes or '',
                'completion_report_template_url': completion_template_url,
                'completion_report_notes': company.completion_report_notes or '',
                'special_notes': company.special_notes or '',
                'is_active': company.is_active,
            }
        })
    else:
        # バリデーションエラー
        errors = {}
        for field, error_list in form.errors.items():
            errors[field] = [str(error) for error in error_list]

        return JsonResponse({
            'success': False,
            'errors': errors
        }, status=400)


@login_required
def contact_person_create_ajax(request):
    """担当者AJAX作成

    元請会社詳細ページから担当者を作成するためのAJAXエンドポイント
    """
    if request.method != 'POST':
        return JsonResponse({
            'success': False,
            'error': 'POSTリクエストのみ対応しています'
        }, status=405)

    # 権限チェック
    if not (has_role(request.user, UserRole.EXECUTIVE) or has_role(request.user, UserRole.COORDINATION_DEPT)):
        return JsonResponse({
            'success': False,
            'error': '担当者の作成権限がありません'
        }, status=403)

    try:
        company_id = request.POST.get('client_company_id')
        name = request.POST.get('name', '').strip()
        position = request.POST.get('position', '').strip()
        email = request.POST.get('email', '').strip()
        phone = request.POST.get('phone', '').strip()
        personality_notes = request.POST.get('personality_notes', '').strip()
        is_primary = request.POST.get('is_primary') == 'true'

        # バリデーション
        if not company_id:
            return JsonResponse({
                'success': False,
                'error': '元請会社IDが指定されていません'
            }, status=400)

        if not name:
            return JsonResponse({
                'success': False,
                'error': '担当者名は必須です'
            }, status=400)

        company = get_object_or_404(ClientCompany, pk=company_id)

        # 主担当に設定する場合、他の主担当を解除
        if is_primary:
            ContactPerson.objects.filter(
                client_company=company,
                is_primary=True
            ).update(is_primary=False)

        # 表示順を最後に設定
        max_order = ContactPerson.objects.filter(
            client_company=company
        ).aggregate(models.Max('display_order'))['display_order__max'] or 0

        # 作成
        contact_person = ContactPerson.objects.create(
            client_company=company,
            name=name,
            position=position,
            email=email,
            phone=phone,
            personality_notes=personality_notes,
            is_primary=is_primary,
            display_order=max_order + 1
        )

        return JsonResponse({
            'success': True,
            'contact_person': {
                'id': contact_person.id,
                'name': contact_person.name,
                'position': contact_person.position or '',
                'email': contact_person.email or '',
                'phone': contact_person.phone or '',
                'personality_notes': contact_person.personality_notes or '',
                'is_primary': contact_person.is_primary,
            }
        })

    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'エラーが発生しました: {str(e)}'
        }, status=500)


@login_required
def contact_person_update_ajax(request):
    """担当者AJAX更新

    担当者情報を更新するためのAJAXエンドポイント
    """
    if request.method != 'POST':
        return JsonResponse({
            'success': False,
            'error': 'POSTリクエストのみ対応しています'
        }, status=405)

    # 権限チェック
    if not (has_role(request.user, UserRole.EXECUTIVE) or has_role(request.user, UserRole.COORDINATION_DEPT)):
        return JsonResponse({
            'success': False,
            'error': '担当者の更新権限がありません'
        }, status=403)

    try:
        contact_person_id = request.POST.get('id')
        name = request.POST.get('name', '').strip()
        position = request.POST.get('position', '').strip()
        email = request.POST.get('email', '').strip()
        phone = request.POST.get('phone', '').strip()
        personality_notes = request.POST.get('personality_notes', '').strip()
        is_primary = request.POST.get('is_primary') == 'true'

        # バリデーション
        if not contact_person_id:
            return JsonResponse({
                'success': False,
                'error': 'IDが指定されていません'
            }, status=400)

        if not name:
            return JsonResponse({
                'success': False,
                'error': '担当者名は必須です'
            }, status=400)

        contact_person = get_object_or_404(ContactPerson, pk=contact_person_id)

        # 主担当に設定する場合、他の主担当を解除
        if is_primary and not contact_person.is_primary:
            ContactPerson.objects.filter(
                client_company=contact_person.client_company,
                is_primary=True
            ).update(is_primary=False)

        # 更新
        contact_person.name = name
        contact_person.position = position
        contact_person.email = email
        contact_person.phone = phone
        contact_person.personality_notes = personality_notes
        contact_person.is_primary = is_primary
        contact_person.save()

        return JsonResponse({
            'success': True,
            'contact_person': {
                'id': contact_person.id,
                'name': contact_person.name,
                'position': contact_person.position or '',
                'email': contact_person.email or '',
                'phone': contact_person.phone or '',
                'personality_notes': contact_person.personality_notes or '',
                'is_primary': contact_person.is_primary,
            }
        })

    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'エラーが発生しました: {str(e)}'
        }, status=500)


@login_required
def contact_person_delete_ajax(request):
    """担当者AJAX削除

    担当者を削除するためのAJAXエンドポイント
    """
    if request.method != 'POST':
        return JsonResponse({
            'success': False,
            'error': 'POSTリクエストのみ対応しています'
        }, status=405)

    # 権限チェック
    if not (has_role(request.user, UserRole.EXECUTIVE) or has_role(request.user, UserRole.COORDINATION_DEPT)):
        return JsonResponse({
            'success': False,
            'error': '担当者の削除権限がありません'
        }, status=403)

    try:
        contact_person_id = request.POST.get('id')

        if not contact_person_id:
            return JsonResponse({
                'success': False,
                'error': 'IDが指定されていません'
            }, status=400)

        contact_person = get_object_or_404(ContactPerson, pk=contact_person_id)
        contact_person_name = contact_person.name
        contact_person.delete()

        return JsonResponse({
            'success': True,
            'message': f'担当者「{contact_person_name}」を削除しました'
        })

    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'エラーが発生しました: {str(e)}'
        }, status=500)
