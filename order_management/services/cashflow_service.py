"""
キャッシュフロー管理サービス

今月の出金/入金管理機能を提供するサービス層
SubcontractとProjectモデルから直接計算し、CashFlowTransactionモデルは使用しない
"""

from datetime import datetime, date
from dateutil.relativedelta import relativedelta
from decimal import Decimal
from django.db.models import Sum, Count, Q
from collections import defaultdict

from order_management.models import Project, ClientCompany
from subcontract_management.models import Subcontract, Contractor


def get_month_range(year, month):
    """
    指定された年月の開始日と終了日を返す

    Args:
        year (int): 年
        month (int): 月

    Returns:
        tuple: (start_date, end_date)
    """
    start_date = date(year, month, 1)

    # 月末日を計算
    if month == 12:
        end_date = date(year + 1, 1, 1) - relativedelta(days=1)
    else:
        end_date = date(year, month + 1, 1) - relativedelta(days=1)

    return start_date, end_date


def calculate_payment_due_date(contract_date, closing_day, payment_offset_months, payment_day):
    """
    契約日と支払い条件から出金予定日を計算

    Args:
        contract_date (date): 契約日
        closing_day (int): 締日 (1-31)
        payment_offset_months (int): 支払月オフセット (0=当月, 1=翌月, 2=翌々月)
        payment_day (int): 支払日 (1-31)

    Returns:
        date: 出金予定日
    """
    if not contract_date or closing_day is None or payment_offset_months is None or payment_day is None:
        return None

    # 締日を基準にして、どの月の締めに含まれるかを判定
    if contract_date.day <= closing_day:
        # 当月締め
        closing_month = contract_date
    else:
        # 翌月締め
        closing_month = contract_date + relativedelta(months=1)

    # 支払い月を計算（締め月 + payment_offset_months）
    payment_month = closing_month + relativedelta(months=payment_offset_months)

    # 支払日を設定
    try:
        payment_due_date = date(payment_month.year, payment_month.month, payment_day)
    except ValueError:
        # 31日が存在しない月の場合は月末日にする
        payment_due_date = date(payment_month.year, payment_month.month, 1) + relativedelta(months=1, days=-1)

    return payment_due_date


def get_outgoing_paid_sites(year, month):
    """
    今月の出金済み現場の一覧を取得

    Args:
        year (int): 年
        month (int): 月

    Returns:
        list: 出金済み現場のリスト
            [
                {
                    'subcontract': Subcontract object,
                    'site_name': str,
                    'contractor_name': str,
                    'billed_amount': Decimal,
                    'payment_date': date,
                    'payment_status': str
                },
                ...
            ]
    """
    start_date, end_date = get_month_range(year, month)

    # 今月出金済みの発注を取得
    subcontracts = Subcontract.objects.filter(
        payment_status='paid',
        payment_date__range=[start_date, end_date]
    ).select_related('project', 'contractor', 'internal_worker').order_by('payment_date')

    sites = []
    for subcontract in subcontracts:
        # 業者名の決定
        if subcontract.worker_type == 'external' and subcontract.contractor:
            contractor_name = subcontract.contractor.name
        elif subcontract.worker_type == 'internal' and subcontract.internal_worker:
            contractor_name = f"{subcontract.internal_worker.name}（社内）"
        else:
            contractor_name = "不明"

        # 金額の決定：被請求額 > 契約金額 > 0
        amount = subcontract.billed_amount if subcontract.billed_amount is not None else (subcontract.contract_amount or Decimal('0'))

        sites.append({
            'subcontract': subcontract,
            'site_name': subcontract.site_name or subcontract.project.site_name if subcontract.project else '不明',
            'contractor_name': contractor_name,
            'billed_amount': amount,
            'payment_date': subcontract.payment_date,
            'payment_status': subcontract.get_payment_status_display()
        })

    return sites


def get_outgoing_paid_by_contractor(year, month):
    """
    今月の出金済み金額を業者別に集計（支払日別の詳細を含む）

    Args:
        year (int): 年
        month (int): 月

    Returns:
        list: 業者別集計リスト
            [
                {
                    'contractor': Contractor object,
                    'contractor_name': str,
                    'contractor_id': str,
                    'total_amount': Decimal,
                    'count': int,
                    'sites': list of site names,
                    'payment_dates': list of unique payment dates,
                    'sites_by_date': {
                        'YYYY-MM-DD': [
                            {
                                'subcontract': Subcontract object,
                                'site_name': str,
                                'billed_amount': Decimal,
                                'payment_date': date,
                                'payment_status': str
                            },
                            ...
                        ],
                        ...
                    }
                },
                ...
            ]
    """
    sites = get_outgoing_paid_sites(year, month)

    # 業者別に集計
    contractor_dict = defaultdict(lambda: {
        'contractor': None,
        'contractor_name': '',
        'contractor_id': '',
        'total_amount': Decimal('0'),
        'count': 0,
        'sites': [],
        'payment_dates': set(),
        'sites_by_date': defaultdict(list)
    })

    for site in sites:
        subcontract = site['subcontract']

        # キーの決定（外注の場合はcontractor_id、社内の場合はinternal_worker_id）
        if subcontract.worker_type == 'external' and subcontract.contractor:
            key = f"external_{subcontract.contractor.id}"
            contractor_dict[key]['contractor'] = subcontract.contractor
            contractor_dict[key]['contractor_name'] = subcontract.contractor.name
            contractor_dict[key]['contractor_id'] = f"external_{subcontract.contractor.id}"
        elif subcontract.worker_type == 'internal' and subcontract.internal_worker:
            key = f"internal_{subcontract.internal_worker.id}"
            contractor_dict[key]['contractor'] = subcontract.internal_worker
            contractor_dict[key]['contractor_name'] = f"{subcontract.internal_worker.name}（社内）"
            contractor_dict[key]['contractor_id'] = f"internal_{subcontract.internal_worker.id}"
        else:
            key = "unknown"
            contractor_dict[key]['contractor_name'] = "不明"
            contractor_dict[key]['contractor_id'] = "unknown"

        contractor_dict[key]['total_amount'] += site['billed_amount']
        contractor_dict[key]['count'] += 1
        contractor_dict[key]['sites'].append(site['site_name'])

        # 支払日別にグループ化
        payment_date_str = site['payment_date'].isoformat() if site['payment_date'] else 'null'
        contractor_dict[key]['payment_dates'].add(payment_date_str)
        contractor_dict[key]['sites_by_date'][payment_date_str].append({
            'subcontract': subcontract,
            'site_name': site['site_name'],
            'billed_amount': site['billed_amount'],
            'payment_date': site['payment_date'],
            'payment_status': site['payment_status']
        })

    # リストに変換してソート
    result = []
    for contractor_data in contractor_dict.values():
        # payment_datesをソートされたリストに変換
        contractor_data['payment_dates'] = sorted(list(contractor_data['payment_dates']))
        # sites_by_dateを通常のdictに変換
        contractor_data['sites_by_date'] = dict(contractor_data['sites_by_date'])
        result.append(contractor_data)

    result = sorted(result, key=lambda x: x['total_amount'], reverse=True)

    return result


def get_outgoing_scheduled_sites(year, month):
    """
    今月の出金予定現場の一覧を取得（未払い・処理中）

    Args:
        year (int): 年
        month (int): 月

    Returns:
        list: 出金予定現場のリスト
            [
                {
                    'subcontract': Subcontract object,
                    'site_name': str,
                    'contractor_name': str,
                    'billed_amount': Decimal,
                    'payment_due_date': date,
                    'payment_status': str
                },
                ...
            ]
    """
    start_date, end_date = get_month_range(year, month)

    # 今月出金予定の発注を取得（未払い or 処理中）
    subcontracts = Subcontract.objects.filter(
        Q(payment_status__in=['pending', 'processing']),
        Q(payment_due_date__range=[start_date, end_date]) |
        Q(payment_due_date__isnull=True, billed_amount__gt=0)
    ).select_related('project', 'contractor', 'internal_worker').order_by('payment_due_date')

    sites = []
    for subcontract in subcontracts:
        # 業者名の決定
        if subcontract.worker_type == 'external' and subcontract.contractor:
            contractor_name = subcontract.contractor.name
        elif subcontract.worker_type == 'internal' and subcontract.internal_worker:
            contractor_name = f"{subcontract.internal_worker.name}（社内）"
        else:
            contractor_name = "不明"

        # 金額の決定：被請求額 > 契約金額 > 0
        amount = subcontract.billed_amount if subcontract.billed_amount is not None else (subcontract.contract_amount or Decimal('0'))

        sites.append({
            'subcontract': subcontract,
            'site_name': subcontract.site_name or subcontract.project.site_name if subcontract.project else '不明',
            'contractor_name': contractor_name,
            'billed_amount': amount,
            'payment_due_date': subcontract.payment_due_date,
            'payment_status': subcontract.get_payment_status_display()
        })

    return sites


def get_outgoing_scheduled_by_contractor(year, month):
    """
    今月の出金予定金額を業者別に集計（支払予定日別の詳細を含む）

    Args:
        year (int): 年
        month (int): 月

    Returns:
        list: 業者別集計リスト
            [
                {
                    'contractor': Contractor object,
                    'contractor_name': str,
                    'contractor_id': str,
                    'total_amount': Decimal,
                    'count': int,
                    'sites': list of site names,
                    'payment_due_dates': list of unique payment due dates,
                    'sites_by_date': {
                        'YYYY-MM-DD': [
                            {
                                'subcontract': Subcontract object,
                                'site_name': str,
                                'billed_amount': Decimal,
                                'payment_due_date': date,
                                'payment_status': str
                            },
                            ...
                        ],
                        ...
                    }
                },
                ...
            ]
    """
    sites = get_outgoing_scheduled_sites(year, month)

    # 業者別に集計
    contractor_dict = defaultdict(lambda: {
        'contractor': None,
        'contractor_name': '',
        'contractor_id': '',
        'total_amount': Decimal('0'),
        'count': 0,
        'sites': [],
        'payment_due_dates': set(),
        'sites_by_date': defaultdict(list)
    })

    for site in sites:
        subcontract = site['subcontract']

        # キーの決定
        if subcontract.worker_type == 'external' and subcontract.contractor:
            key = f"external_{subcontract.contractor.id}"
            contractor_dict[key]['contractor'] = subcontract.contractor
            contractor_dict[key]['contractor_name'] = subcontract.contractor.name
            contractor_dict[key]['contractor_id'] = f"external_{subcontract.contractor.id}"
        elif subcontract.worker_type == 'internal' and subcontract.internal_worker:
            key = f"internal_{subcontract.internal_worker.id}"
            contractor_dict[key]['contractor'] = subcontract.internal_worker
            contractor_dict[key]['contractor_name'] = f"{subcontract.internal_worker.name}（社内）"
            contractor_dict[key]['contractor_id'] = f"internal_{subcontract.internal_worker.id}"
        else:
            key = "unknown"
            contractor_dict[key]['contractor_name'] = "不明"
            contractor_dict[key]['contractor_id'] = "unknown"

        contractor_dict[key]['total_amount'] += site['billed_amount']
        contractor_dict[key]['count'] += 1
        contractor_dict[key]['sites'].append(site['site_name'])

        # 支払予定日別にグループ化
        payment_due_date_str = site['payment_due_date'].isoformat() if site['payment_due_date'] else 'null'
        contractor_dict[key]['payment_due_dates'].add(payment_due_date_str)
        contractor_dict[key]['sites_by_date'][payment_due_date_str].append({
            'subcontract': subcontract,
            'site_name': site['site_name'],
            'billed_amount': site['billed_amount'],
            'payment_due_date': site['payment_due_date'],
            'payment_status': site['payment_status']
        })

    # リストに変換してソート
    result = []
    for contractor_data in contractor_dict.values():
        # payment_due_datesをソートされたリストに変換
        contractor_data['payment_due_dates'] = sorted(list(contractor_data['payment_due_dates']))
        # sites_by_dateを通常のdictに変換
        contractor_data['sites_by_date'] = dict(contractor_data['sites_by_date'])
        result.append(contractor_data)

    result = sorted(result, key=lambda x: x['total_amount'], reverse=True)

    return result


def get_outgoing_unfilled(year, month):
    """
    今月分で出金情報が未入力の現場を取得

    Args:
        year (int): 年
        month (int): 月

    Returns:
        list: 未入力現場のリスト
            [
                {
                    'subcontract': Subcontract object,
                    'site_name': str,
                    'contractor_name': str,
                    'contract_amount': Decimal,
                    'missing_fields': list of str
                },
                ...
            ]
    """
    start_date, end_date = get_month_range(year, month)

    # 今月の案件に関連する発注で、出金情報が未入力のものを取得
    # アクティブな案件（受注確定）に関連する下請けを取得
    subcontracts = Subcontract.objects.filter(
        project__project_status='受注確定'
    ).select_related('project', 'contractor', 'internal_worker')

    unfilled_sites = []
    for subcontract in subcontracts:
        missing_fields = []

        # 被請求額が未入力
        if not subcontract.billed_amount or subcontract.billed_amount == 0:
            missing_fields.append('被請求額')

        # 出金予定日が未入力
        if not subcontract.payment_due_date:
            missing_fields.append('出金予定日')

        # 欠落フィールドがある場合のみリストに追加
        if missing_fields:
            # 業者名の決定
            if subcontract.worker_type == 'external' and subcontract.contractor:
                contractor_name = subcontract.contractor.name
            elif subcontract.worker_type == 'internal' and subcontract.internal_worker:
                contractor_name = f"{subcontract.internal_worker.name}（社内）"
            else:
                contractor_name = "不明"

            unfilled_sites.append({
                'subcontract': subcontract,
                'site_name': subcontract.site_name or subcontract.project.site_name if subcontract.project else '不明',
                'contractor_name': contractor_name,
                'contract_amount': subcontract.contract_amount or Decimal('0'),
                'missing_fields': missing_fields
            })

    return unfilled_sites


def get_incoming_received_projects(year, month):
    """
    今月の入金済みプロジェクトの一覧を取得

    Args:
        year (int): 年
        month (int): 月

    Returns:
        list: 入金済みプロジェクトのリスト
            [
                {
                    'project': Project object,
                    'site_name': str,
                    'client_company_name': str,
                    'billing_amount': Decimal,
                    'payment_due_date': date,
                    'payment_status': str
                },
                ...
            ]
    """
    start_date, end_date = get_month_range(year, month)

    # 今月入金済みのプロジェクトを取得
    # incoming_payment_statusが'received'で、payment_due_dateが今月のもの
    projects = Project.objects.filter(
        incoming_payment_status='received',
        payment_due_date__range=[start_date, end_date]
    ).select_related('client_company').order_by('payment_due_date')

    project_list = []
    for project in projects:
        client_company_name = project.client_company.company_name if project.client_company else '不明な元請'

        project_list.append({
            'project': project,
            'site_name': project.site_name,
            'client_company_name': client_company_name,
            'billing_amount': project.billing_amount or project.order_amount or Decimal('0'),
            'payment_due_date': project.payment_due_date,
            'payment_status': project.get_incoming_payment_status_display()
        })

    return project_list


def get_incoming_received_by_client(year, month):
    """
    今月の入金済み金額を元請業者別に集計（入金日別の詳細を含む）

    Args:
        year (int): 年
        month (int): 月

    Returns:
        list: 元請業者別集計リスト
            [
                {
                    'client_company': ClientCompany object,
                    'client_company_name': str,
                    'client_id': str,
                    'total_amount': Decimal,
                    'count': int,
                    'projects': list of project names,
                    'payment_dates': list of unique payment dates,
                    'projects_by_date': {
                        'YYYY-MM-DD': [
                            {
                                'project': Project object,
                                'site_name': str,
                                'billing_amount': Decimal,
                                'payment_due_date': date,
                                'payment_status': str
                            },
                            ...
                        ],
                        ...
                    }
                },
                ...
            ]
    """
    projects = get_incoming_received_projects(year, month)

    # 元請業者別に集計
    client_dict = defaultdict(lambda: {
        'client_company': None,
        'client_company_name': '',
        'client_id': '',
        'total_amount': Decimal('0'),
        'count': 0,
        'projects': [],
        'payment_dates': set(),
        'projects_by_date': defaultdict(list)
    })

    for proj_data in projects:
        project = proj_data['project']

        # キーの決定
        if project.client_company:
            key = f"client_{project.client_company.id}"
            client_dict[key]['client_company'] = project.client_company
            client_dict[key]['client_company_name'] = project.client_company.company_name
            client_dict[key]['client_id'] = f"client_{project.client_company.id}"
        else:
            key = "unknown"
            client_dict[key]['client_company_name'] = "不明な元請"
            client_dict[key]['client_id'] = "unknown"

        client_dict[key]['total_amount'] += proj_data['billing_amount']
        client_dict[key]['count'] += 1
        client_dict[key]['projects'].append(proj_data['site_name'])

        # 入金日別にグループ化
        payment_date_str = proj_data['payment_due_date'].isoformat() if proj_data['payment_due_date'] else 'null'
        client_dict[key]['payment_dates'].add(payment_date_str)
        client_dict[key]['projects_by_date'][payment_date_str].append({
            'project': project,
            'site_name': proj_data['site_name'],
            'billing_amount': proj_data['billing_amount'],
            'payment_due_date': proj_data['payment_due_date'],
            'payment_status': proj_data['payment_status']
        })

    # リストに変換してソート
    result = []
    for client_data in client_dict.values():
        # payment_datesをソートされたリストに変換
        client_data['payment_dates'] = sorted(list(client_data['payment_dates']))
        # projects_by_dateを通常のdictに変換
        client_data['projects_by_date'] = dict(client_data['projects_by_date'])
        result.append(client_data)

    result = sorted(result, key=lambda x: x['total_amount'], reverse=True)

    return result


def get_incoming_scheduled_projects(year, month):
    """
    今月の入金予定プロジェクトの一覧を取得（入金待ち・処理中）

    Args:
        year (int): 年
        month (int): 月

    Returns:
        list: 入金予定プロジェクトのリスト
            [
                {
                    'project': Project object,
                    'site_name': str,
                    'client_company_name': str,
                    'billing_amount': Decimal,
                    'payment_due_date': date,
                    'payment_status': str
                },
                ...
            ]
    """
    start_date, end_date = get_month_range(year, month)

    # 今月入金予定のプロジェクトを取得（入金待ち or 処理中）
    projects = Project.objects.filter(
        Q(incoming_payment_status__in=['pending', 'processing']),
        Q(payment_due_date__range=[start_date, end_date]) |
        Q(payment_due_date__isnull=True, billing_amount__gt=0)
    ).select_related('client_company').order_by('payment_due_date')

    result = []
    for project in projects:
        # 元請会社名の決定
        if project.client_company:
            client_company_name = project.client_company.company_name
        else:
            client_company_name = "不明な元請"

        # 金額の決定：請求額 > 発注額 > 0
        amount = project.billing_amount if project.billing_amount is not None else (project.order_amount or Decimal('0'))

        result.append({
            'project': project,
            'site_name': project.site_name or '不明',
            'client_company_name': client_company_name,
            'billing_amount': amount,
            'payment_due_date': project.payment_due_date,
            'payment_status': project.get_incoming_payment_status_display()
        })

    return result


def get_incoming_scheduled_by_client(year, month):
    """
    今月の入金予定金額を元請業者別に集計（入金予定日別の詳細を含む）

    Args:
        year (int): 年
        month (int): 月

    Returns:
        list: 元請業者別集計リスト
            [
                {
                    'client_company': ClientCompany object,
                    'client_company_name': str,
                    'client_id': str,
                    'total_amount': Decimal,
                    'count': int,
                    'projects': list of project names,
                    'payment_due_dates': list of unique payment due dates,
                    'projects_by_date': {
                        'YYYY-MM-DD': [
                            {
                                'project': Project object,
                                'site_name': str,
                                'billing_amount': Decimal,
                                'payment_due_date': date,
                                'payment_status': str
                            },
                            ...
                        ],
                        ...
                    }
                },
                ...
            ]
    """
    projects = get_incoming_scheduled_projects(year, month)

    # 元請業者別に集計
    client_dict = defaultdict(lambda: {
        'client_company': None,
        'client_company_name': '',
        'client_id': '',
        'total_amount': Decimal('0'),
        'count': 0,
        'projects': [],
        'payment_due_dates': set(),
        'projects_by_date': defaultdict(list)
    })

    for proj_data in projects:
        project = proj_data['project']

        # キーの決定
        if project.client_company:
            key = f"client_{project.client_company.id}"
            client_dict[key]['client_company'] = project.client_company
            client_dict[key]['client_company_name'] = project.client_company.company_name
            client_dict[key]['client_id'] = f"client_{project.client_company.id}"
        else:
            key = "unknown"
            client_dict[key]['client_company_name'] = "不明な元請"
            client_dict[key]['client_id'] = "unknown"

        client_dict[key]['total_amount'] += proj_data['billing_amount']
        client_dict[key]['count'] += 1
        client_dict[key]['projects'].append(proj_data['site_name'])

        # 入金予定日別にグループ化
        payment_due_date_str = proj_data['payment_due_date'].isoformat() if proj_data['payment_due_date'] else 'null'
        client_dict[key]['payment_due_dates'].add(payment_due_date_str)
        client_dict[key]['projects_by_date'][payment_due_date_str].append({
            'project': project,
            'site_name': proj_data['site_name'],
            'billing_amount': proj_data['billing_amount'],
            'payment_due_date': proj_data['payment_due_date'],
            'payment_status': proj_data['payment_status']
        })

    # リストに変換してソート
    result = []
    for client_data in client_dict.values():
        # payment_due_datesをソートされたリストに変換
        client_data['payment_due_dates'] = sorted(list(client_data['payment_due_dates']))
        # projects_by_dateを通常のdictに変換
        client_data['projects_by_date'] = dict(client_data['projects_by_date'])
        result.append(client_data)

    result = sorted(result, key=lambda x: x['total_amount'], reverse=True)

    return result
