"""
PDF生成ユーティリティ - Phase 3

ReportLabを使用してレポートPDFを生成します。
"""

import os
from io import BytesIO
from decimal import Decimal
from datetime import datetime

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    PageBreak, Image
)
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT

from django.conf import settings


def setup_japanese_fonts():
    """日本語フォントをセットアップ - クロスプラットフォーム対応"""
    try:
        # reportlabの組み込みCJKフォントを使用（日本語対応）
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.cidfonts import UnicodeCIDFont

        # HeiseiMin-W3（平成明朝）またはHeiseiKakuGo-W5（平成角ゴシック）を登録
        # これらはreportlabに組み込まれており、追加のフォントファイル不要
        pdfmetrics.registerFont(UnicodeCIDFont('HeiseiKakuGo-W5'))
        return 'HeiseiKakuGo-W5'
    except Exception as e:
        # フォールバック: システムフォントを試す
        try:
            font_paths = [
                'C:\\Windows\\Fonts\\msgothic.ttc',  # Windows
                '/System/Library/Fonts/ヒラギノ角ゴシック W3.ttc',  # macOS
                '/usr/share/fonts/opentype/ipaexfont-gothic/ipaexg.ttf',  # Ubuntu
            ]

            for font_path in font_paths:
                if os.path.exists(font_path):
                    try:
                        pdfmetrics.registerFont(TTFont('Japanese', font_path))
                        return 'Japanese'
                    except:
                        pass

            # 最終フォールバック
            return 'Helvetica'
        except:
            return 'Helvetica'


def generate_pdf_report(report_data, report_type, title):
    """
    レポートデータからPDFを生成

    Args:
        report_data: レポートデータ（dict）
        report_type: レポートタイプ ('monthly', 'project', 'cashflow', 'forecast')
        title: レポートタイトル

    Returns:
        str: 生成されたPDFファイルのパス（相対パス）
    """
    # 出力先ディレクトリ
    output_dir = os.path.join(settings.MEDIA_ROOT, 'reports', str(datetime.now().year), f"{datetime.now().month:02d}")
    os.makedirs(output_dir, exist_ok=True)

    # ファイル名
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f"{report_type}_{timestamp}.pdf"
    filepath = os.path.join(output_dir, filename)

    # PDFドキュメント作成
    doc = SimpleDocTemplate(
        filepath,
        pagesize=A4,
        rightMargin=20*mm,
        leftMargin=20*mm,
        topMargin=20*mm,
        bottomMargin=20*mm
    )

    # 日本語フォント設定
    font_name = setup_japanese_fonts()

    # スタイル設定
    styles = getSampleStyleSheet()

    # カスタムスタイル
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontName=font_name,
        fontSize=20,
        textColor=colors.HexColor('#1e3a8a'),
        spaceAfter=12,
        alignment=TA_CENTER
    )

    heading_style = ParagraphStyle(
        'CustomHeading',
        parent=styles['Heading2'],
        fontName=font_name,
        fontSize=14,
        textColor=colors.HexColor('#2563eb'),
        spaceAfter=6,
        spaceBefore=12
    )

    body_style = ParagraphStyle(
        'CustomBody',
        parent=styles['Normal'],
        fontName=font_name,
        fontSize=10,
        leading=14
    )

    # ストーリー（PDFの内容）
    story = []

    # タイトル
    story.append(Paragraph(title, title_style))
    story.append(Spacer(1, 10*mm))

    # レポートタイプ別に内容を生成
    if report_type == 'monthly':
        story.extend(_generate_monthly_pdf_content(report_data, heading_style, body_style, font_name))

    elif report_type == 'project':
        story.extend(_generate_project_pdf_content(report_data, heading_style, body_style, font_name))

    elif report_type == 'cashflow':
        story.extend(_generate_cashflow_pdf_content(report_data, heading_style, body_style, font_name))

    elif report_type == 'forecast':
        story.extend(_generate_forecast_pdf_content(report_data, heading_style, body_style, font_name))

    # フッター（生成日時）
    story.append(Spacer(1, 10*mm))
    footer_text = f"Generated at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    footer_style = ParagraphStyle('Footer', parent=body_style, fontSize=8, textColor=colors.grey, alignment=TA_RIGHT)
    story.append(Paragraph(footer_text, footer_style))

    # PDFビルド
    doc.build(story)

    # 相対パスを返す
    relative_path = os.path.relpath(filepath, settings.MEDIA_ROOT)
    return relative_path


def _generate_monthly_pdf_content(data, heading_style, body_style, font_name):
    """月次経営レポートのPDF内容を生成"""
    content = []

    # 期間情報
    period = data.get('period', {})
    content.append(Paragraph(f"対象期間: {period.get('year')}年{period.get('month')}月", body_style))
    content.append(Spacer(1, 5*mm))

    # 1. 売上・利益サマリー
    content.append(Paragraph("1. 売上・利益サマリー", heading_style))

    revenue_summary = data.get('revenue_summary', {})
    summary_data = [
        ['項目', '金額'],
        ['売上高', f"¥{revenue_summary.get('total_revenue', 0):,.0f}"],
        ['原価', f"¥{revenue_summary.get('total_cost', 0):,.0f}"],
        ['営業利益', f"¥{revenue_summary.get('total_profit', 0):,.0f}"],
        ['利益率', f"{revenue_summary.get('profit_margin', 0):.1f}%"],
        ['完工案件数', f"{revenue_summary.get('project_count', 0)}件"],
        ['平均受注金額', f"¥{revenue_summary.get('avg_order_amount', 0):,.0f}"],
    ]

    summary_table = Table(summary_data, colWidths=[80*mm, 80*mm])
    summary_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#3b82f6')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
        ('FONTNAME', (0, 0), (-1, -1), font_name),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('GRID', (0, 0), (-1, -1), 1, colors.grey),
    ]))

    content.append(summary_table)
    content.append(Spacer(1, 5*mm))

    # 2. プロジェクト進捗状況
    content.append(Paragraph("2. プロジェクト進捗状況", heading_style))

    progress_summary = data.get('progress_summary', {})
    progress_data = [
        ['ステータス', '件数'],
        ['完工', f"{progress_summary.get('完工', 0)}件"],
        ['進行中', f"{progress_summary.get('進行中', 0)}件"],
        ['施工日待ち', f"{progress_summary.get('施工日待ち', 0)}件"],
        ['ネタ', f"{progress_summary.get('ネタ', 0)}件"],
        ['NG', f"{progress_summary.get('NG', 0)}件"],
    ]

    progress_table = Table(progress_data, colWidths=[80*mm, 80*mm])
    progress_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#10b981')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
        ('FONTNAME', (0, 0), (-1, -1), font_name),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('GRID', (0, 0), (-1, -1), 1, colors.grey),
    ]))

    content.append(progress_table)
    content.append(Spacer(1, 5*mm))

    # 3. キャッシュフロー状況
    content.append(Paragraph("3. キャッシュフロー状況", heading_style))

    cashflow_summary = data.get('cashflow_summary', {})
    cashflow_data = [
        ['項目', '金額'],
        ['入金', f"¥{cashflow_summary.get('total_cash_in', 0):,.0f}"],
        ['出金', f"¥{cashflow_summary.get('total_cash_out', 0):,.0f}"],
        ['純キャッシュフロー', f"¥{cashflow_summary.get('net_cash_flow', 0):,.0f}"],
    ]

    cashflow_table = Table(cashflow_data, colWidths=[80*mm, 80*mm])
    cashflow_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#f59e0b')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
        ('FONTNAME', (0, 0), (-1, -1), font_name),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('GRID', (0, 0), (-1, -1), 1, colors.grey),
    ]))

    content.append(cashflow_table)
    content.append(Spacer(1, 5*mm))

    # 4. 前月比較
    content.append(Paragraph("4. 前月比較", heading_style))

    comparison = data.get('comparison', {})
    comparison_text = f"前月売上: ¥{comparison.get('prev_revenue', 0):,.0f}　成長率: {comparison.get('revenue_growth', 0):.1f}%"
    content.append(Paragraph(comparison_text, body_style))

    return content


def _generate_project_pdf_content(data, heading_style, body_style, font_name):
    """プロジェクト別レポートのPDF内容を生成"""
    content = []

    # プロジェクト詳細
    project_detail = data.get('project_detail', {})
    content.append(Paragraph(f"案件No: {project_detail.get('management_no', 'N/A')}", body_style))
    content.append(Paragraph(f"現場名: {project_detail.get('site_name', 'N/A')}", body_style))
    content.append(Spacer(1, 5*mm))

    # 原価・利益分析
    content.append(Paragraph("原価・利益分析", heading_style))

    cost_analysis = data.get('cost_analysis', {})
    cost_data = [
        ['項目', '金額'],
        ['受注金額', f"¥{project_detail.get('order_amount', 0):,.0f}"],
        ['総原価', f"¥{cost_analysis.get('total_cost', 0):,.0f}"],
        ['　外注費', f"¥{cost_analysis.get('subcontract_cost', 0):,.0f}"],
        ['　材料費', f"¥{cost_analysis.get('material_cost', 0):,.0f}"],
        ['粗利益', f"¥{cost_analysis.get('gross_profit', 0):,.0f}"],
        ['粗利率', f"{cost_analysis.get('profit_margin', 0):.1f}%"],
    ]

    cost_table = Table(cost_data, colWidths=[80*mm, 80*mm])
    cost_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#3b82f6')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
        ('FONTNAME', (0, 0), (-1, -1), font_name),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('GRID', (0, 0), (-1, -1), 1, colors.grey),
    ]))

    content.append(cost_table)
    content.append(Spacer(1, 5*mm))

    # 進捗状況
    progress_info = data.get('progress_info', {})
    if progress_info.get('has_progress'):
        content.append(Paragraph("進捗状況", heading_style))
        progress_text = f"進捗率: {progress_info.get('progress_rate', 0):.1f}%　ステータス: {progress_info.get('status', 'N/A')}"
        content.append(Paragraph(progress_text, body_style))

        if progress_info.get('has_risk'):
            risk_text = f"リスク: {progress_info.get('risk_level', 'N/A')} - {progress_info.get('risk_description', 'N/A')}"
            content.append(Paragraph(risk_text, body_style))

    return content


def _generate_cashflow_pdf_content(data, heading_style, body_style, font_name):
    """キャッシュフローレポートのPDF内容を生成"""
    content = []

    # 期間情報
    period = data.get('period', {})
    content.append(Paragraph(f"対象期間: {period.get('year')}年{period.get('month')}月", body_style))
    content.append(Spacer(1, 5*mm))

    # 入出金予定
    content.append(Paragraph("入出金予定", heading_style))

    scheduled = data.get('scheduled', {})
    scheduled_data = [
        ['項目', '金額'],
        ['入金予定', f"¥{scheduled.get('total_in', 0):,.0f}"],
        ['出金予定', f"¥{scheduled.get('total_out', 0):,.0f}"],
        ['収支', f"¥{scheduled.get('net', 0):,.0f}"],
    ]

    scheduled_table = Table(scheduled_data, colWidths=[80*mm, 80*mm])
    scheduled_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#10b981')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
        ('FONTNAME', (0, 0), (-1, -1), font_name),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('GRID', (0, 0), (-1, -1), 1, colors.grey),
    ]))

    content.append(scheduled_table)
    content.append(Spacer(1, 5*mm))

    # 資金繰り表
    content.append(Paragraph("資金繰り表（3ヶ月予測）", heading_style))

    forecast = data.get('forecast', [])
    forecast_data = [['年月', '入金', '出金', '収支']]
    for item in forecast:
        forecast_data.append([
            f"{item['year']}/{item['month']:02d}",
            f"¥{item['inflow']:,.0f}",
            f"¥{item['outflow']:,.0f}",
            f"¥{item['net']:,.0f}"
        ])

    forecast_table = Table(forecast_data, colWidths=[40*mm, 40*mm, 40*mm, 40*mm])
    forecast_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#f59e0b')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('ALIGN', (1, 1), (-1, -1), 'RIGHT'),
        ('FONTNAME', (0, 0), (-1, -1), font_name),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('GRID', (0, 0), (-1, -1), 1, colors.grey),
    ]))

    content.append(forecast_table)

    return content


def _generate_forecast_pdf_content(data, heading_style, body_style, font_name):
    """予測レポートのPDF内容を生成"""
    content = []

    # シナリオ詳細
    scenario_detail = data.get('scenario_detail', {})
    content.append(Paragraph(f"シナリオ: {scenario_detail.get('name', 'N/A')}", body_style))
    content.append(Paragraph(f"タイプ: {scenario_detail.get('scenario_type', 'N/A')}", body_style))
    content.append(Spacer(1, 5*mm))

    # サマリー
    content.append(Paragraph("予測サマリー", heading_style))

    summary = data.get('summary', {})
    summary_data = [
        ['項目', '金額'],
        ['予測売上', f"¥{summary.get('total_revenue', 0):,.0f}"],
        ['予測利益', f"¥{summary.get('total_profit', 0):,.0f}"],
        ['利益率', f"{summary.get('profit_margin', 0):.1f}%"],
        ['予測月数', f"{summary.get('months', 0)}ヶ月"],
    ]

    summary_table = Table(summary_data, colWidths=[80*mm, 80*mm])
    summary_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#8b5cf6')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
        ('FONTNAME', (0, 0), (-1, -1), font_name),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('GRID', (0, 0), (-1, -1), 1, colors.grey),
    ]))

    content.append(summary_table)
    content.append(Spacer(1, 5*mm))

    # 前提条件
    content.append(Paragraph("前提条件", heading_style))

    assumptions = data.get('assumptions', {})
    for key, value in assumptions.items():
        content.append(Paragraph(f"・{value}", body_style))

    return content


def generate_purchase_order_pdf(contractor_name, payment_date, sites_data, contractor_info=None, custom_remarks=None):
    """
    業者別・支払日別の発注書PDFを生成

    Args:
        contractor_name (str): 業者名
        payment_date (date or str): 支払日
        sites_data (list): 現場データのリスト containing site_name, billed_amount, etc.
        contractor_info (dict): Optional contractor details (phone, email, payment_terms)
        custom_remarks (str): カスタム備考欄のテキスト（指定されていればデフォルトの代わりに使用）

    Returns:
        str: 生成されたPDFファイルのパス（相対パス）
    """
    from datetime import date
    from order_management.models import CompanySettings

    # 会社設定を取得
    company_settings = CompanySettings.get_settings()

    # payment_dateを日付オブジェクトに変換
    if isinstance(payment_date, str):
        if payment_date and payment_date != 'null':
            payment_date = datetime.strptime(payment_date, '%Y-%m-%d').date()
        else:
            payment_date = date.today()

    # 出力先ディレクトリ
    year = payment_date.year if payment_date else datetime.now().year
    month = payment_date.month if payment_date else datetime.now().month
    output_dir = os.path.join(settings.MEDIA_ROOT, 'purchase_orders', str(year), f"{month:02d}")
    os.makedirs(output_dir, exist_ok=True)

    # ファイル名
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    safe_contractor_name = contractor_name.replace('/', '_').replace('\\', '_')[:30]
    filename = f"発注書_{safe_contractor_name}_{timestamp}.pdf"
    filepath = os.path.join(output_dir, filename)

    # PDFドキュメント作成
    doc = SimpleDocTemplate(
        filepath,
        pagesize=A4,
        rightMargin=20*mm,
        leftMargin=20*mm,
        topMargin=15*mm,
        bottomMargin=15*mm
    )

    # 日本語フォント設定
    font_name = setup_japanese_fonts()

    # スタイル設定
    styles = getSampleStyleSheet()

    # カスタムスタイル
    title_style = ParagraphStyle(
        'POTitle',
        parent=styles['Heading1'],
        fontName=font_name,
        fontSize=24,
        textColor=colors.HexColor('#1e3a8a'),
        spaceAfter=8,
        alignment=TA_CENTER
    )

    heading_style = ParagraphStyle(
        'POHeading',
        parent=styles['Heading2'],
        fontName=font_name,
        fontSize=12,
        textColor=colors.HexColor('#374151'),
        spaceAfter=4,
        spaceBefore=8
    )

    body_style = ParagraphStyle(
        'POBody',
        parent=styles['Normal'],
        fontName=font_name,
        fontSize=10,
        leading=14
    )

    # ストーリー（PDFの内容）
    story = []

    # タイトル
    story.append(Paragraph("発注書", title_style))
    story.append(Spacer(1, 5*mm))

    # 発注先情報（左側）と発注元情報（右側）を2カラムレイアウトで配置
    left_content = []
    right_content = []

    # 左側：発注先情報
    left_content.append(Paragraph(f"発注先: {contractor_name} 御中", heading_style))

    if contractor_info:
        if contractor_info.get('phone'):
            left_content.append(Paragraph(f"TEL: {contractor_info['phone']}", body_style))
        if contractor_info.get('email'):
            left_content.append(Paragraph(f"Email: {contractor_info['email']}", body_style))

    left_content.append(Spacer(1, 3*mm))

    # 支払情報
    payment_date_str = payment_date.strftime('%Y年%m月%d日') if payment_date else '未定'
    left_content.append(Paragraph(f"支払予定日: {payment_date_str}", body_style))

    if contractor_info and contractor_info.get('payment_terms'):
        left_content.append(Paragraph(f"支払条件: {contractor_info['payment_terms']}", body_style))

    # 右側：発注元（自社）情報（上部に10mmのスペースを追加）
    right_content.append(Spacer(1, 10*mm))

    if company_settings.company_name:
        right_content.append(Paragraph(f"発注元: {company_settings.company_name}", heading_style))

        if company_settings.company_address:
            right_content.append(Paragraph(f"住所: {company_settings.company_address}", body_style))
        if company_settings.company_phone:
            right_content.append(Paragraph(f"TEL: {company_settings.company_phone}", body_style))
        if company_settings.company_fax:
            right_content.append(Paragraph(f"FAX: {company_settings.company_fax}", body_style))
        if company_settings.company_email:
            right_content.append(Paragraph(f"Email: {company_settings.company_email}", body_style))
        if company_settings.company_representative:
            right_content.append(Paragraph(f"担当: {company_settings.company_representative}", body_style))

    # 3カラムテーブルを作成（真ん中を空白にして右側に発注元情報を配置）
    header_table_data = [[left_content, '', right_content]]
    header_table = Table(header_table_data, colWidths=[40*mm, 70*mm, 60*mm])
    header_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING', (0, 0), (-1, -1), 0),
        ('RIGHTPADDING', (0, 0), (-1, -1), 0),
        ('ALIGN', (2, 0), (2, 0), 'RIGHT'),  # 右側を右寄せ
    ]))
    story.append(header_table)
    story.append(Spacer(1, 8*mm))

    # 案件一覧テーブル
    story.append(Paragraph("発注明細", heading_style))
    story.append(Spacer(1, 3*mm))

    # テーブルデータ
    table_data = [['No.', '現場名', '期間', '契約金額', '請求金額']]

    total_amount = Decimal('0')
    for idx, site in enumerate(sites_data, 1):
        site_name = site.get('site_name', 'N/A')

        # 期間（改行を入れて表示）
        start_date = site.get('start_date', '')
        end_date = site.get('end_date', '')
        if start_date and end_date:
            work_period = f"{start_date}\n ~ \n{end_date}"
        else:
            work_period = 'N/A'

        # 金額
        contract_amount = site.get('contract_amount', 0)
        billed_amount = site.get('billed_amount', 0)

        if billed_amount:
            total_amount += Decimal(str(billed_amount))

        # 現場名をParagraphで包んで折り返しを有効にする
        site_name_paragraph = Paragraph(site_name, body_style)

        table_data.append([
            str(idx),
            site_name_paragraph,
            work_period,
            f"¥{contract_amount:,.0f}" if contract_amount else '-',
            f"¥{billed_amount:,.0f}" if billed_amount else '-'
        ])

    # 合計行
    table_data.append(['', '', '', '合計', f"¥{total_amount:,.0f}"])

    # テーブル作成
    sites_table = Table(table_data, colWidths=[15*mm, 60*mm, 40*mm, 30*mm, 30*mm])
    sites_table.setStyle(TableStyle([
        # ヘッダー
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#3b82f6')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('FONTNAME', (0, 0), (-1, 0), font_name),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('FONTNAME', (0, 1), (-1, -1), font_name),
        ('FONTSIZE', (0, 1), (-1, -1), 9),

        # 合計行
        ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#f3f4f6')),
        ('FONTNAME', (0, -1), (-1, -1), font_name),
        ('FONTSIZE', (0, -1), (-1, -1), 10),

        # アライメント
        ('ALIGN', (0, 0), (0, -1), 'CENTER'),  # No.列
        ('ALIGN', (3, 0), (-1, -1), 'RIGHT'),  # 金額列
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),

        # パディング
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('LEFTPADDING', (0, 0), (-1, -1), 4),
        ('RIGHTPADDING', (0, 0), (-1, -1), 4),

        # グリッド
        ('GRID', (0, 0), (-1, -1), 1, colors.grey),
    ]))

    story.append(sites_table)
    story.append(Spacer(1, 10*mm))

    # 備考欄
    story.append(Paragraph("備考", heading_style))
    story.append(Spacer(1, 2*mm))

    # カスタム備考があればそれを使用、なければ設定から備考を取得
    if custom_remarks:
        remarks_text = custom_remarks
    else:
        remarks_text = company_settings.purchase_order_remarks or '上記の通り発注いたします。\nご査収の程よろしくお願い申し上げます。'
    remarks_data = [[remarks_text]]
    remarks_table = Table(remarks_data, colWidths=[170*mm])
    remarks_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, -1), font_name),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('BOX', (0, 0), (-1, -1), 1, colors.grey),
    ]))
    story.append(remarks_table)

    # フッター（発行日時）
    story.append(Spacer(1, 10*mm))
    footer_text = f"発行日: {datetime.now().strftime('%Y年%m月%d日')}"
    footer_style = ParagraphStyle('Footer', parent=body_style, fontSize=8, textColor=colors.grey, alignment=TA_RIGHT)
    story.append(Paragraph(footer_text, footer_style))

    # PDFビルド
    doc.build(story)

    # 相対パスを返す
    relative_path = os.path.relpath(filepath, settings.MEDIA_ROOT)
    return relative_path


def generate_invoice_pdf(client_name, payment_date, projects_data, client_info=None, custom_remarks=None):
    """
    クライアント別・入金日別の請求書PDFを生成

    Args:
        client_name (str): クライアント名
        payment_date (date or str): 入金予定日
        projects_data (list): 案件データのリスト containing project_no, site_name, order_amount, etc.
        client_info (dict): Optional client details (company_name, address, phone)
        custom_remarks (str): カスタム備考欄のテキスト（指定されていればデフォルトの代わりに使用）

    Returns:
        str: 生成されたPDFファイルのパス（相対パス）
    """
    from datetime import date
    from order_management.models import CompanySettings

    # 会社設定を取得
    company_settings = CompanySettings.get_settings()

    # payment_dateを日付オブジェクトに変換
    if isinstance(payment_date, str):
        if payment_date and payment_date != 'null':
            payment_date = datetime.strptime(payment_date, '%Y-%m-%d').date()
        else:
            payment_date = date.today()

    # 出力先ディレクトリ
    year = payment_date.year if payment_date else datetime.now().year
    month = payment_date.month if payment_date else datetime.now().month
    output_dir = os.path.join(settings.MEDIA_ROOT, 'invoices', str(year), f"{month:02d}")
    os.makedirs(output_dir, exist_ok=True)

    # ファイル名
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    safe_client_name = client_name.replace('/', '_').replace('\\', '_')[:30]
    filename = f"請求書_{safe_client_name}_{timestamp}.pdf"
    filepath = os.path.join(output_dir, filename)

    # PDFドキュメント作成
    doc = SimpleDocTemplate(
        filepath,
        pagesize=A4,
        rightMargin=20*mm,
        leftMargin=20*mm,
        topMargin=15*mm,
        bottomMargin=15*mm
    )

    # 日本語フォント設定
    font_name = setup_japanese_fonts()

    # スタイル設定
    styles = getSampleStyleSheet()

    # カスタムスタイル
    title_style = ParagraphStyle(
        'InvoiceTitle',
        parent=styles['Heading1'],
        fontName=font_name,
        fontSize=24,
        textColor=colors.HexColor('#1e3a8a'),
        spaceAfter=8,
        alignment=TA_CENTER
    )

    heading_style = ParagraphStyle(
        'InvoiceHeading',
        parent=styles['Heading2'],
        fontName=font_name,
        fontSize=12,
        textColor=colors.HexColor('#374151'),
        spaceAfter=4,
        spaceBefore=8
    )

    body_style = ParagraphStyle(
        'InvoiceBody',
        parent=styles['Normal'],
        fontName=font_name,
        fontSize=10,
        leading=14
    )

    # ストーリー（PDFの内容）
    story = []

    # タイトル
    story.append(Paragraph("請求書", title_style))
    story.append(Spacer(1, 5*mm))

    # 請求先情報（左側）と請求元情報（右側）を2カラムレイアウトで配置
    left_content = []
    right_content = []

    # 左側：請求先情報
    left_content.append(Paragraph(f"請求先: {client_name} 御中", heading_style))

    if client_info:
        if client_info.get('company_name'):
            left_content.append(Paragraph(f"会社名: {client_info['company_name']}", body_style))
        if client_info.get('address'):
            left_content.append(Paragraph(f"住所: {client_info['address']}", body_style))
        if client_info.get('phone'):
            left_content.append(Paragraph(f"TEL: {client_info['phone']}", body_style))

    left_content.append(Spacer(1, 3*mm))

    # 入金情報
    payment_date_str = payment_date.strftime('%Y年%m月%d日') if payment_date else '未定'
    left_content.append(Paragraph(f"入金予定日: {payment_date_str}", body_style))

    if client_info and client_info.get('payment_terms'):
        left_content.append(Paragraph(f"支払条件: {client_info['payment_terms']}", body_style))

    # 右側：請求元（自社）情報（上部に10mmのスペースを追加）
    right_content.append(Spacer(1, 10*mm))

    if company_settings.company_name:
        right_content.append(Paragraph(f"請求元: {company_settings.company_name}", heading_style))

        if company_settings.company_address:
            right_content.append(Paragraph(f"住所: {company_settings.company_address}", body_style))
        if company_settings.company_phone:
            right_content.append(Paragraph(f"TEL: {company_settings.company_phone}", body_style))
        if company_settings.company_fax:
            right_content.append(Paragraph(f"FAX: {company_settings.company_fax}", body_style))
        if company_settings.company_email:
            right_content.append(Paragraph(f"Email: {company_settings.company_email}", body_style))
        if company_settings.company_representative:
            right_content.append(Paragraph(f"担当: {company_settings.company_representative}", body_style))

    # 3カラムテーブルを作成（真ん中を空白にして右側に発注元情報を配置）
    header_table_data = [[left_content, '', right_content]]
    header_table = Table(header_table_data, colWidths=[40*mm, 70*mm, 60*mm])
    header_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING', (0, 0), (-1, -1), 0),
        ('RIGHTPADDING', (0, 0), (-1, -1), 0),
        ('ALIGN', (2, 0), (2, 0), 'RIGHT'),  # 右側を右寄せ
    ]))
    story.append(header_table)
    story.append(Spacer(1, 8*mm))

    # 案件一覧テーブル
    story.append(Paragraph("請求明細", heading_style))
    story.append(Spacer(1, 3*mm))

    # テーブルデータ
    table_data = [['No.', '案件No.', '現場名', '期間', '請求金額']]

    total_amount = Decimal('0')
    for idx, project in enumerate(projects_data, 1):
        project_no = project.get('management_no', 'N/A')
        site_name = project.get('site_name', 'N/A')

        # 期間（改行を入れて表示）
        start_date = project.get('start_date', '')
        end_date = project.get('end_date', '')
        if start_date and end_date:
            work_period = f"{start_date}\n ~ \n{end_date}"
        else:
            work_period = 'N/A'

        # 請求金額
        order_amount = project.get('order_amount', 0)

        if order_amount:
            total_amount += Decimal(str(order_amount))

        # 現場名をParagraphで包んで折り返しを有効にする
        site_name_paragraph = Paragraph(site_name, body_style)

        table_data.append([
            str(idx),
            project_no,
            site_name_paragraph,
            work_period,
            f"¥{order_amount:,.0f}" if order_amount else '-'
        ])

    # 合計行
    table_data.append(['', '', '', '合計', f"¥{total_amount:,.0f}"])

    # テーブル作成
    projects_table = Table(table_data, colWidths=[15*mm, 20*mm, 70*mm, 35*mm, 35*mm])
    projects_table.setStyle(TableStyle([
        # ヘッダー
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#10b981')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('FONTNAME', (0, 0), (-1, 0), font_name),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('FONTNAME', (0, 1), (-1, -1), font_name),
        ('FONTSIZE', (0, 1), (-1, -1), 9),

        # 合計行
        ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#f3f4f6')),
        ('FONTNAME', (0, -1), (-1, -1), font_name),
        ('FONTSIZE', (0, -1), (-1, -1), 10),

        # アライメント
        ('ALIGN', (0, 0), (0, -1), 'CENTER'),  # No.列
        ('ALIGN', (4, 0), (4, -1), 'RIGHT'),  # 金額列
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),

        # パディング
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('LEFTPADDING', (0, 0), (-1, -1), 4),
        ('RIGHTPADDING', (0, 0), (-1, -1), 4),

        # グリッド
        ('GRID', (0, 0), (-1, -1), 1, colors.grey),
    ]))

    story.append(projects_table)
    story.append(Spacer(1, 10*mm))

    # 備考欄
    story.append(Paragraph("備考", heading_style))
    story.append(Spacer(1, 2*mm))

    # カスタム備考があればそれを使用、なければ設定から備考を取得
    if custom_remarks:
        remarks_text = custom_remarks
    else:
        remarks_text = company_settings.invoice_remarks or '上記の通り請求させていただきます。\nお支払いの程よろしくお願い申し上げます。'
    remarks_data = [[remarks_text]]
    remarks_table = Table(remarks_data, colWidths=[170*mm])
    remarks_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, -1), font_name),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('BOX', (0, 0), (-1, -1), 1, colors.grey),
    ]))
    story.append(remarks_table)

    # フッター（発行日時）
    story.append(Spacer(1, 10*mm))
    footer_text = f"発行日: {datetime.now().strftime('%Y年%m月%d日')}"
    footer_style = ParagraphStyle('InvoiceFooter', parent=body_style, fontSize=8, textColor=colors.grey, alignment=TA_RIGHT)
    story.append(Paragraph(footer_text, footer_style))

    # PDFビルド
    doc.build(story)

    # 相対パスを返す
    relative_path = os.path.relpath(filepath, settings.MEDIA_ROOT)
    return relative_path
