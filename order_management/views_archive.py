"""
アーカイブ機能管理ビュー
旧バージョンの経理機能を参照専用で表示
"""

from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from datetime import datetime


class ArchivedFeaturesView(LoginRequiredMixin, TemplateView):
    """アーカイブされた機能一覧ページ"""
    template_name = 'order_management/archived_features.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # アーカイブされた機能のリスト
        context['archived_features'] = [
            {
                'category': '会計・キャッシュフロー管理',
                'features': [
                    {
                        'name': '会計ダッシュボード',
                        'icon': 'fa-chart-line',
                        'description': '総合的な会計ダッシュボード（旧版）',
                        'archived_date': '2025-11-30',
                    },
                    {
                        'name': '支払いダッシュボード',
                        'icon': 'fa-money-bill-wave',
                        'description': '支払い管理ダッシュボード（旧版）',
                        'archived_date': '2025-11-30',
                    },
                    {
                        'name': '入金ダッシュボード',
                        'icon': 'fa-receipt',
                        'description': '入金管理ダッシュボード（旧版）',
                        'archived_date': '2025-11-30',
                    },
                    {
                        'name': 'CF管理',
                        'icon': 'fa-exchange-alt',
                        'description': 'キャッシュフロー管理機能（旧版）',
                        'archived_date': '2025-11-30',
                    },
                    {
                        'name': '売掛金詳細',
                        'icon': 'fa-hand-holding-usd',
                        'description': '売掛金管理機能（旧版）',
                        'archived_date': '2025-11-30',
                    },
                    {
                        'name': '買掛金詳細',
                        'icon': 'fa-file-invoice-dollar',
                        'description': '買掛金管理機能（旧版）',
                        'archived_date': '2025-11-30',
                    },
                ]
            },
            {
                'category': '売上予測・シミュレーション',
                'features': [
                    {
                        'name': '売上予測ダッシュボード',
                        'icon': 'fa-chart-line',
                        'description': '売上予測機能（旧版）',
                        'archived_date': '2025-11-30',
                    },
                    {
                        'name': 'シナリオ分析',
                        'icon': 'fa-tasks',
                        'description': 'シナリオベースの予測分析（旧版）',
                        'archived_date': '2025-11-30',
                    },
                    {
                        'name': '季節性指数管理',
                        'icon': 'fa-calendar-alt',
                        'description': '季節性を考慮した予測（旧版）',
                        'archived_date': '2025-11-30',
                    },
                ]
            },
            {
                'category': 'レポート管理',
                'features': [
                    {
                        'name': 'レポート一覧',
                        'icon': 'fa-file-alt',
                        'description': '生成済みレポートの一覧（旧版）',
                        'archived_date': '2025-11-30',
                    },
                    {
                        'name': 'レポート生成',
                        'icon': 'fa-file-export',
                        'description': '各種レポートの生成機能（旧版）',
                        'archived_date': '2025-11-30',
                    },
                ]
            },
            {
                'category': 'コスト管理',
                'features': [
                    {
                        'name': '固定費管理',
                        'icon': 'fa-calculator',
                        'description': '固定費の登録・管理（旧版）',
                        'archived_date': '2025-11-30',
                        'note': '※ 一部機能は継続利用可能'
                    },
                    {
                        'name': '変動費管理',
                        'icon': 'fa-coins',
                        'description': '変動費の登録・管理（旧版）',
                        'archived_date': '2025-11-30',
                        'note': '※ 一部機能は継続利用可能'
                    },
                ]
            },
        ]

        # アーカイブ理由
        context['archive_reasons'] = [
            '複雑すぎる設計で実際の業務フローと乖離',
            'CashFlowTransactionモデルによる二重管理',
            '使いにくいUI/UX',
            '保守・拡張が困難な実装',
        ]

        # 新機能の情報
        context['new_features'] = {
            'status': '実装中',
            'release_date': '近日公開予定',
            'features': [
                '今月の出金/入金管理（シンプル・実用的）',
                'SubcontractとProjectモデルから直接計算',
                '使いやすい2タブUI（出金/入金）',
                '月次レポート機能',
            ]
        }

        context['archive_date'] = '2025年11月30日'

        return context
