"""業者管理ビュー"""
from django.views.generic import TemplateView, UpdateView, DetailView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.shortcuts import get_object_or_404
from django.db.models import Sum, Count, Q, Max
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
import json

from .models import Project
from subcontract_management.models import Contractor, ContractorFieldCategory, ContractorFieldDefinition, Subcontract


class ContractorDashboardView(LoginRequiredMixin, TemplateView):
    """元請け検索ダッシュボード（開発中）"""
    template_name = 'order_management/contractor_dashboard.html'

    def get_context_data(self, **kwargs):
        from django.db.models import Count, Sum, Q, F
        from .models import ClientCompany
        from datetime import datetime, timedelta
        import json

        context = super().get_context_data(**kwargs)

        # すべての元請け業者を取得
        contractors = ClientCompany.objects.all().order_by('company_name')

        # 各業者に集計データを追加
        contractors_data = []
        total_contractors = 0
        total_projects_count = 0
        total_revenue = 0
        total_cost = 0

        for client_company in contractors:
            # この元請けからの案件を取得
            projects = Project.objects.filter(client_company=client_company)

            # 案件数
            project_count = projects.count()

            # 売上合計（受注額）
            contractor_revenue = projects.aggregate(total=Sum('billing_amount'))['total'] or 0
            contractor_revenue = float(contractor_revenue)

            # 原価合計（発注額）
            contractor_cost = projects.aggregate(total=Sum('order_amount'))['total'] or 0
            contractor_cost = float(contractor_cost)

            # 利益
            profit = contractor_revenue - contractor_cost

            # 利益率
            profit_rate = (profit / contractor_revenue * 100) if contractor_revenue > 0 else 0

            # 業者タグ
            contractor_tags = ['元請け業者']
            if client_company.payment_cycle:
                contractor_tags.append(f'支払い: {client_company.get_payment_cycle_display()}')

            # 月次トレンドデータ（過去12ヶ月）
            monthly_trends = []
            today = datetime.now()
            for i in range(12):
                month_start = (today.replace(day=1) - timedelta(days=i*30)).replace(day=1)
                month_label = month_start.strftime('%Y/%m')

                # その月の案件
                month_projects = projects.filter(
                    created_at__year=month_start.year,
                    created_at__month=month_start.month
                )

                month_revenue = month_projects.aggregate(total=Sum('billing_amount'))['total'] or 0
                month_revenue = float(month_revenue)
                month_cost = month_projects.aggregate(total=Sum('order_amount'))['total'] or 0
                month_cost = float(month_cost)
                month_profit = month_revenue - month_cost
                month_profit_rate = (month_profit / month_revenue * 100) if month_revenue > 0 else 0

                monthly_trends.insert(0, {
                    'month': month_label,
                    'revenue': month_revenue,
                    'profit': month_profit,
                    'profit_rate': month_profit_rate
                })

            contractor_obj = {
                'id': client_company.id,
                'name': client_company.company_name,
                'contractor_type': 'client',
                'specialties': client_company.address or '',
                'status': 'active' if client_company.is_active else 'inactive',
                'contractor_tags': contractor_tags,
                'project_count': project_count,
                'total_revenue': contractor_revenue,
                'total_cost': contractor_cost,
                'profit': profit,
                'profit_rate': profit_rate,
                'monthly_trends': monthly_trends
            }

            contractors_data.append(contractor_obj)

            # 全体集計
            total_contractors += 1
            total_projects_count += project_count
            total_revenue += contractor_revenue
            total_cost += contractor_cost

        # サマリーデータ
        avg_profit_rate = ((total_revenue - total_cost) / total_revenue * 100) if total_revenue > 0 else 0

        summary = {
            'total_contractors': total_contractors,
            'total_projects': total_projects_count,
            'total_revenue': total_revenue,
            'total_cost': total_cost,
            'avg_profit_rate': avg_profit_rate
        }

        # 月次データ（全体）
        monthly_data = []
        chart_labels = []
        today = datetime.now()
        for i in range(12):
            month_start = (today.replace(day=1) - timedelta(days=i*30)).replace(day=1)
            month_label = month_start.strftime('%Y/%m')

            month_projects = Project.objects.filter(
                created_at__year=month_start.year,
                created_at__month=month_start.month
            )

            month_revenue = month_projects.aggregate(total=Sum('billing_amount'))['total'] or 0
            month_revenue = float(month_revenue)
            month_cost = month_projects.aggregate(total=Sum('order_amount'))['total'] or 0
            month_cost = float(month_cost)
            month_profit = month_revenue - month_cost
            month_profit_rate = (month_profit / month_revenue * 100) if month_revenue > 0 else 0

            monthly_data.insert(0, {
                'revenue': month_revenue,
                'profit': month_profit,
                'profit_rate': month_profit_rate
            })
            chart_labels.insert(0, month_label)

        context['contractors'] = contractors_data
        context['contractors_json'] = json.dumps(contractors_data)
        context['summary'] = summary
        context['monthly_data_json'] = json.dumps(monthly_data)
        context['chart_labels_json'] = json.dumps(chart_labels)

        return context


class ContractorProjectsView(LoginRequiredMixin, TemplateView):
    """業者別案件一覧"""
    template_name = 'order_management/contractor_projects.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        contractor_id = self.kwargs.get('contractor_id')
        contractor = get_object_or_404(Contractor, id=contractor_id)

        # この業者が担当している案件を取得
        projects = Project.objects.filter(
            subcontract__contractor=contractor
        ).distinct().order_by('-created_at')

        context['contractor'] = contractor
        context['projects'] = projects
        return context


class ContractorDetailView(LoginRequiredMixin, DetailView):
    """業者詳細表示"""
    model = Contractor
    template_name = 'order_management/contractor_detail.html'
    context_object_name = 'contractor'

    def get_context_data(self, **kwargs):
        from datetime import datetime
        context = super().get_context_data(**kwargs)
        contractor = self.get_object()

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

        # 外注案件を取得
        all_subcontracts = Subcontract.objects.filter(
            contractor=contractor,
            worker_type='external'
        ).select_related('project').order_by('-created_at')

        # ページネーター作成
        paginator = Paginator(all_subcontracts, per_page)

        try:
            subcontracts_page = paginator.page(page)
        except PageNotAnInteger:
            subcontracts_page = paginator.page(1)
        except EmptyPage:
            subcontracts_page = paginator.page(paginator.num_pages)

        context['subcontracts_page'] = subcontracts_page
        context['per_page'] = per_page

        # 統計情報
        subcontracts_all = Subcontract.objects.filter(
            contractor=contractor,
            worker_type='external'
        )

        context['total_subcontracts'] = subcontracts_all.count()
        context['total_amount'] = subcontracts_all.aggregate(
            total=Sum('contract_amount')
        )['total'] or 0
        context['total_billed'] = subcontracts_all.aggregate(
            total=Sum('billed_amount')
        )['total'] or 0
        context['unpaid_amount'] = subcontracts_all.filter(
            payment_status='pending'
        ).aggregate(
            total=Sum('billed_amount')
        )['total'] or 0

        # カスタムフィールドをカテゴリごとに整理
        categories = ContractorFieldCategory.objects.filter(
            is_active=True
        ).prefetch_related('field_definitions').order_by('order')

        custom_fields_by_category = []
        for category in categories:
            fields_data = []
            for field_def in category.field_definitions.filter(is_active=True).order_by('order'):
                # custom_fieldsから値を取得
                value = contractor.custom_fields.get(field_def.slug, '')

                # フィールドタイプに応じて表示用の値を整形
                display_value = value
                if field_def.field_type == 'checkbox':
                    display_value = '○' if value else '×'
                elif field_def.field_type == 'multiselect' and isinstance(value, list):
                    display_value = ', '.join(value)
                elif field_def.field_type == 'select':
                    display_value = value

                fields_data.append({
                    'definition': field_def,
                    'value': value,
                    'display_value': display_value
                })

            if fields_data:  # フィールドがある場合のみ追加
                custom_fields_by_category.append({
                    'category': category,
                    'fields': fields_data
                })

        context['custom_fields_by_category'] = custom_fields_by_category

        return context


class ContractorEditView(LoginRequiredMixin, UpdateView):
    """業者編集"""
    model = Contractor
    template_name = 'order_management/contractor_form.html'
    fields = [
        'name', 'contractor_type', 'address', 'phone', 'email', 'contact_person',
        'hourly_rate', 'specialties', 'is_active',
        # 支払い情報
        'payment_cycle', 'closing_day', 'payment_offset_months', 'payment_day',
        # 銀行口座情報
        'bank_name', 'branch_name', 'account_type', 'account_number', 'account_holder'
    ]

    def get_success_url(self):
        """保存後のリダイレクト先を取得（元のページに戻る）"""
        # リファラーがあればそこに戻る
        referer = self.request.META.get('HTTP_REFERER')
        if referer:
            # 編集ページ自体のURLは除外（無限ループ防止）
            if f'/contractors/{self.object.pk}/edit/' not in referer:
                return referer

        # デフォルトは外注先管理ページ
        return reverse_lazy('order_management:external_contractor_management')

    def get_form(self, form_class=None):
        form = super().get_form(form_class)

        # フォームフィールドにBootstrapクラスを追加
        form.fields['name'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': '例: ○○建設株式会社'
        })
        form.fields['contractor_type'].widget.attrs.update({
            'class': 'form-select'
        })
        form.fields['address'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': '例: 東京都渋谷区...'
        })
        form.fields['phone'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': '例: 03-1234-5678'
        })
        form.fields['email'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': '例: info@example.com'
        })
        form.fields['contact_person'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': '例: 山田 太郎'
        })
        form.fields['hourly_rate'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': '3000',
            'min': '0',
            'step': '100'
        })
        form.fields['specialties'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': '例: 建築工事、内装工事'
        })
        form.fields['is_active'].widget.attrs.update({
            'class': 'form-check-input'
        })

        # 支払い情報フィールド
        form.fields['payment_cycle'].widget.attrs.update({
            'class': 'form-select'
        })
        form.fields['closing_day'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': '1-31',
            'min': '1',
            'max': '31'
        })
        form.fields['payment_day'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': '1-31',
            'min': '1',
            'max': '31'
        })

        # 銀行口座情報フィールド
        form.fields['bank_name'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': '例: みずほ銀行'
        })
        form.fields['branch_name'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': '例: 渋谷支店'
        })
        form.fields['account_type'].widget.attrs.update({
            'class': 'form-select'
        })
        form.fields['account_number'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': '1234567'
        })
        form.fields['account_holder'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': '例: カ）マルマルケンセツ'
        })

        return form

    def form_valid(self, form):
        """フォームが有効な場合、カスタムフィールドも保存"""
        contractor = form.save(commit=False)

        # カスタムフィールドの値を取得して保存
        custom_fields_data = {}
        field_definitions = ContractorFieldDefinition.objects.filter(is_active=True)

        for field_def in field_definitions:
            field_name = f'custom_{field_def.slug}'

            if field_def.field_type == 'checkbox':
                # チェックボックスは on/off で送信される
                value = field_name in self.request.POST
                custom_fields_data[field_def.slug] = value
            elif field_def.field_type == 'multiselect':
                # 複数選択はリストで取得
                values = self.request.POST.getlist(field_name)
                custom_fields_data[field_def.slug] = values
            else:
                # その他のフィールドタイプ
                value = self.request.POST.get(field_name, '')
                if value:
                    custom_fields_data[field_def.slug] = value

        # custom_fieldsフィールドに保存
        if not contractor.custom_fields:
            contractor.custom_fields = {}
        contractor.custom_fields.update(custom_fields_data)

        contractor.save()
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # カスタムフィールド定義をカテゴリごとに取得
        categories = ContractorFieldCategory.objects.filter(
            is_active=True
        ).prefetch_related('field_definitions').order_by('order')

        custom_fields_by_category = []
        for category in categories:
            fields_data = []
            for field_def in category.field_definitions.filter(is_active=True).order_by('order'):
                # 現在の値を取得
                current_value = self.object.custom_fields.get(field_def.slug, '')

                fields_data.append({
                    'definition': field_def,
                    'current_value': current_value
                })

            if fields_data:  # フィールドがある場合のみ追加
                custom_fields_by_category.append({
                    'category': category,
                    'fields': fields_data
                })

        context['custom_fields_by_category'] = custom_fields_by_category

        # 地方ごとの都道府県マッピング
        context['regions_mapping'] = {
            '北海道': ['北海道'],
            '東北': ['青森県', '岩手県', '宮城県', '秋田県', '山形県', '福島県'],
            '関東': ['茨城県', '栃木県', '群馬県', '埼玉県', '千葉県', '東京都', '神奈川県'],
            '中部': ['新潟県', '富山県', '石川県', '福井県', '山梨県', '長野県', '岐阜県', '静岡県', '愛知県'],
            '近畿': ['三重県', '滋賀県', '京都府', '大阪府', '兵庫県', '奈良県', '和歌山県'],
            '中国': ['鳥取県', '島根県', '岡山県', '広島県', '山口県'],
            '四国': ['徳島県', '香川県', '愛媛県', '高知県'],
            '九州・沖縄': ['福岡県', '佐賀県', '長崎県', '熊本県', '大分県', '宮崎県', '鹿児島県', '沖縄県']
        }

        return context


# ============================================================================
# カスタムフィールド管理 AJAX API
# ============================================================================

@login_required
@require_http_methods(["GET"])
def contractor_field_categories_list(request):
    """カテゴリ一覧取得API"""
    try:
        categories = ContractorFieldCategory.objects.all().order_by('order')
        categories_data = []

        for category in categories:
            fields_count = category.field_definitions.filter(is_active=True).count()
            categories_data.append({
                'id': category.id,
                'name': category.name,
                'slug': category.slug,
                'description': category.description,
                'order': category.order,
                'is_active': category.is_active,
                'fields_count': fields_count,
            })

        return JsonResponse({
            'success': True,
            'categories': categories_data
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@login_required
@require_http_methods(["POST"])
def contractor_field_category_create(request):
    """カテゴリ作成API"""
    try:
        data = json.loads(request.body)
        name = data.get('name', '').strip()
        slug = data.get('slug', '').strip()
        description = data.get('description', '').strip()

        if not name or not slug:
            return JsonResponse({
                'success': False,
                'error': 'カテゴリ名とスラッグは必須です'
            }, status=400)

        max_order = ContractorFieldCategory.objects.aggregate(Max('order'))['order__max'] or 0

        category = ContractorFieldCategory.objects.create(
            name=name,
            slug=slug,
            description=description,
            order=max_order + 1,
            is_active=True
        )

        return JsonResponse({
            'success': True,
            'category': {
                'id': category.id,
                'name': category.name,
                'slug': category.slug,
                'description': category.description,
                'order': category.order,
                'is_active': category.is_active,
                'fields_count': 0,
            }
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@login_required
@require_http_methods(["POST"])
def contractor_field_category_update(request, category_id):
    """カテゴリ更新API"""
    try:
        category = get_object_or_404(ContractorFieldCategory, id=category_id)
        data = json.loads(request.body)

        category.name = data.get('name', category.name).strip()
        category.slug = data.get('slug', category.slug).strip()
        category.description = data.get('description', category.description).strip()
        category.is_active = data.get('is_active', category.is_active)
        category.save()

        return JsonResponse({
            'success': True,
            'category': {
                'id': category.id,
                'name': category.name,
                'slug': category.slug,
                'description': category.description,
                'order': category.order,
                'is_active': category.is_active,
            }
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@login_required
@require_http_methods(["POST"])
def contractor_field_category_delete(request, category_id):
    """カテゴリ削除API"""
    try:
        category = get_object_or_404(ContractorFieldCategory, id=category_id)
        category_name = category.name
        category.delete()

        return JsonResponse({
            'success': True,
            'message': f'カテゴリ「{category_name}」を削除しました'
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@login_required
@require_http_methods(["GET"])
def contractor_field_definitions_list(request):
    """フィールド定義一覧取得API"""
    try:
        category_id = request.GET.get('category_id')

        if category_id:
            fields = ContractorFieldDefinition.objects.filter(category_id=category_id).order_by('order')
        else:
            fields = ContractorFieldDefinition.objects.all().order_by('category__order', 'order')

        fields_data = []
        for field in fields:
            fields_data.append({
                'id': field.id,
                'category_id': field.category.id,
                'category_name': field.category.name,
                'name': field.name,
                'slug': field.slug,
                'field_type': field.field_type,
                'field_type_display': field.get_field_type_display(),
                'help_text': field.help_text,
                'placeholder': field.placeholder,
                'choices': field.choices,
                'is_required': field.is_required,
                'min_value': field.min_value,
                'max_value': field.max_value,
                'order': field.order,
                'is_active': field.is_active,
            })

        return JsonResponse({
            'success': True,
            'fields': fields_data
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@login_required
@require_http_methods(["POST"])
def contractor_field_definition_create(request):
    """フィールド定義作成API"""
    try:
        data = json.loads(request.body)
        category_id = data.get('category_id')
        name = data.get('name', '').strip()
        slug = data.get('slug', '').strip()
        field_type = data.get('field_type', 'text')

        if not category_id or not name or not slug:
            return JsonResponse({
                'success': False,
                'error': 'カテゴリ、フィールド名、スラッグは必須です'
            }, status=400)

        category = get_object_or_404(ContractorFieldCategory, id=category_id)
        max_order = ContractorFieldDefinition.objects.filter(category=category).aggregate(Max('order'))['order__max'] or 0

        choices_str = data.get('choices', '')
        if choices_str and field_type in ['select', 'multiselect']:
            choices = [c.strip() for c in choices_str.split(',') if c.strip()]
        else:
            choices = []

        field = ContractorFieldDefinition.objects.create(
            category=category,
            name=name,
            slug=slug,
            field_type=field_type,
            help_text=data.get('help_text', '').strip(),
            placeholder=data.get('placeholder', '').strip(),
            choices=choices,
            is_required=data.get('is_required', False),
            min_value=data.get('min_value'),
            max_value=data.get('max_value'),
            order=max_order + 1,
            is_active=True
        )

        return JsonResponse({
            'success': True,
            'field': {
                'id': field.id,
                'category_id': field.category.id,
                'category_name': field.category.name,
                'name': field.name,
                'slug': field.slug,
                'field_type': field.field_type,
                'field_type_display': field.get_field_type_display(),
                'help_text': field.help_text,
                'placeholder': field.placeholder,
                'choices': field.choices,
                'is_required': field.is_required,
                'min_value': field.min_value,
                'max_value': field.max_value,
                'order': field.order,
                'is_active': field.is_active,
            }
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@login_required
@require_http_methods(["POST"])
def contractor_field_definition_update(request, field_id):
    """フィールド定義更新API"""
    try:
        field = get_object_or_404(ContractorFieldDefinition, id=field_id)
        data = json.loads(request.body)

        field.name = data.get('name', field.name).strip()
        field.slug = data.get('slug', field.slug).strip()
        field.field_type = data.get('field_type', field.field_type)
        field.help_text = data.get('help_text', field.help_text).strip()
        field.placeholder = data.get('placeholder', field.placeholder).strip()
        field.is_required = data.get('is_required', field.is_required)
        field.is_active = data.get('is_active', field.is_active)
        field.min_value = data.get('min_value', field.min_value)
        field.max_value = data.get('max_value', field.max_value)

        if 'choices' in data:
            choices_str = data['choices']
            if choices_str and field.field_type in ['select', 'multiselect']:
                field.choices = [c.strip() for c in choices_str.split(',') if c.strip()]
            else:
                field.choices = []

        field.save()

        return JsonResponse({
            'success': True,
            'field': {
                'id': field.id,
                'name': field.name,
                'slug': field.slug,
                'field_type': field.field_type,
                'field_type_display': field.get_field_type_display(),
                'help_text': field.help_text,
                'placeholder': field.placeholder,
                'choices': field.choices,
                'is_required': field.is_required,
                'min_value': field.min_value,
                'max_value': field.max_value,
                'is_active': field.is_active,
            }
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@login_required
@require_http_methods(["POST"])
def contractor_field_definition_delete(request, field_id):
    """フィールド定義削除API"""
    try:
        field = get_object_or_404(ContractorFieldDefinition, id=field_id)
        field_name = field.name
        field.delete()

        return JsonResponse({
            'success': True,
            'message': f'フィールド「{field_name}」を削除しました'
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@login_required
@require_http_methods(["POST"])
def contractor_field_reorder(request):
    """カテゴリ・フィールドの並び替えAPI"""
    try:
        data = json.loads(request.body)
        reorder_type = data.get('type')
        items = data.get('items', [])

        if reorder_type == 'category':
            for item in items:
                ContractorFieldCategory.objects.filter(id=item['id']).update(order=item['order'])
        elif reorder_type == 'field':
            for item in items:
                ContractorFieldDefinition.objects.filter(id=item['id']).update(order=item['order'])
        else:
            return JsonResponse({
                'success': False,
                'error': '無効な並び替えタイプです'
            }, status=400)

        return JsonResponse({
            'success': True,
            'message': '並び替えを保存しました'
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)
