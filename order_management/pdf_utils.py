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
    """日本語フォントをセットアップ"""
    try:
        # IPAフォントをシステムから探す
        font_paths = [
            '/System/Library/Fonts/ヒラギノ角ゴシック W3.ttc',  # macOS
            '/usr/share/fonts/opentype/ipaexfont-gothic/ipaexg.ttf',  # Ubuntu
            'C:\\Windows\\Fonts\\msgothic.ttc',  # Windows
        ]

        for font_path in font_paths:
            if os.path.exists(font_path):
                try:
                    pdfmetrics.registerFont(TTFont('Japanese', font_path))
                    return 'Japanese'
                except:
                    pass

        # フォントが見つからない場合はHelveticaを使用
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
