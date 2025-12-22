"""
CSV一括インポートコマンド

受注側FMTと依頼側FMTからプロジェクトデータをインポートします。

Usage:
    python manage.py import_project_csv <受注側CSV> <依頼側CSV> [options]

Example:
    python manage.py import_project_csv order.csv subcontract.csv --dry-run
"""

import csv
import os
import re
from datetime import datetime
from decimal import Decimal
from collections import defaultdict
from typing import Dict, List, Tuple, Optional, Any

from django.core.management.base import BaseCommand, CommandError
from django.core.management import call_command
from django.db import transaction
from django.utils import timezone

from order_management.models import (
    Project, ClientCompany, ContactPerson
)
from subcontract_management.models import Contractor, Subcontract
from order_management.services.progress_step_service import set_step_scheduled_date, complete_step


class CSVReader:
    """CSV読み込みクラス（エンコーディング自動検出）"""

    @staticmethod
    def detect_encoding(file_path: str) -> str:
        """
        CSVファイルのエンコーディングを検出

        Args:
            file_path: CSVファイルパス

        Returns:
            エンコーディング名（'utf-8', 'cp932', 'shift_jis'）
        """
        encodings = ['utf-8', 'cp932', 'shift_jis', 'utf-8-sig']

        for encoding in encodings:
            try:
                with open(file_path, 'r', encoding=encoding) as f:
                    f.read()
                return encoding
            except (UnicodeDecodeError, UnicodeError):
                continue

        return 'utf-8'  # デフォルト

    @staticmethod
    def read_csv(file_path: str) -> List[Dict[str, str]]:
        """
        CSVファイルを読み込んで辞書のリストを返す

        注意: CSVに重複した列名がある場合（例: 「請負業者名」が列7と列16）、
              最初に出現した列の値を使用します（csv.DictReaderは最後の列を使うため、
              カスタム実装で対応）

        Args:
            file_path: CSVファイルパス

        Returns:
            [{列名: 値, ...}, ...]
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f'CSVファイルが見つかりません: {file_path}')

        encoding = CSVReader.detect_encoding(file_path)

        with open(file_path, 'r', encoding=encoding) as f:
            lines = f.readlines()

        # メタデータ行をスキップ（1行目が「固定」「手動」「自動」の場合）
        if lines and any(marker in lines[0] for marker in ['固定', '手動', '自動']):
            lines = lines[1:]  # メタデータ行をスキップ

        # 2行目以降をCSVとして読み込み
        # csv.reader を使って列インデックスベースで読み込む（重複列名に対応）
        import io
        csv_text = ''.join(lines)
        reader = csv.reader(io.StringIO(csv_text))

        rows_list = list(reader)
        if not rows_list:
            return []

        # ヘッダー行（1行目）
        headers = rows_list[0]

        # 重複した列名の最初の出現インデックスを記録
        # 例: '請負業者名'が列7と列16にある場合、列7のみを使用
        header_first_occurrence = {}
        for idx, header in enumerate(headers):
            if header and header not in header_first_occurrence:
                header_first_occurrence[header] = idx

        # データ行を辞書に変換
        result = []
        for row in rows_list[1:]:  # ヘッダー行をスキップ
            row_dict = {}

            # 各ヘッダーに対して、最初に出現した列のインデックスから値を取得
            for header, first_idx in header_first_occurrence.items():
                if first_idx < len(row):
                    row_dict[header] = row[first_idx]
                else:
                    row_dict[header] = ''

            result.append(row_dict)

        return result


class ManagementNoConverter:
    """管理番号変換クラス"""

    @staticmethod
    def convert(csv_no: str) -> str:
        """
        CSV管理番号をアプリ形式に変換

        CSV: 1 → App: M250001
        CSV: 123 → App: M250123
        CSV: 5678 → App: M255678

        Args:
            csv_no: CSV管理番号（文字列または数値）

        Returns:
            アプリ形式管理番号（M25xxxx）
        """
        # 数値部分を抽出
        csv_no_str = str(csv_no).strip()

        # 数値のみ抽出
        numeric_part = re.sub(r'[^\d]', '', csv_no_str)

        if not numeric_part:
            raise ValueError(f'無効な管理番号: {csv_no}')

        # M25 + 4桁ゼロ埋め
        return f"M25{numeric_part.zfill(4)}"


class DataMerger:
    """CSV結合クラス"""

    @staticmethod
    def merge(order_rows: List[Dict], subcontract_rows: List[Dict]) -> Dict[str, Dict]:
        """
        受注側と依頼側CSVを管理番号でグループ化

        Args:
            order_rows: 受注側CSV行リスト
            subcontract_rows: 依頼側CSV行リスト

        Returns:
            {
                '1': {
                    'project': {...受注側データ...},
                    'subcontracts': [...依頼側データ...]
                },
                ...
            }
        """
        merged_data = defaultdict(lambda: {'project': None, 'subcontracts': []})

        # 受注側データをグループ化
        for row in order_rows:
            mgmt_no = row.get('管理No', '').strip()
            if mgmt_no:
                merged_data[mgmt_no]['project'] = row

        # 依頼側データをグループ化
        for row in subcontract_rows:
            mgmt_no = row.get('管理No', '').strip()
            if mgmt_no:
                merged_data[mgmt_no]['subcontracts'].append(row)

        return dict(merged_data)


class DataParser:
    """データ解析・変換クラス"""

    @staticmethod
    def parse_currency(value: str) -> Optional[Decimal]:
        """
        通貨文字列を数値に変換

        ¥35,020 → 35020
        35020 → 35020
        #VALUE! → None (Excelエラー)
        "" → None
        """
        if not value or value.strip() == '':
            return None

        value_str = str(value).strip()

        # Excelエラーをチェック
        if value_str.startswith('#'):
            return None

        # ¥記号、カンマ、スペースを削除
        cleaned = re.sub(r'[¥,\s]', '', value_str)

        if not cleaned:
            return None

        try:
            return Decimal(cleaned)
        except (ValueError, TypeError, Exception):
            return None

    @staticmethod
    def parse_date(value: str) -> Optional[datetime]:
        """
        日付文字列を日付オブジェクトに変換

        2025/07/03 → datetime(2025, 7, 3)
        2025-07-03 → datetime(2025, 7, 3)
        "" → None
        """
        if not value or value.strip() == '':
            return None

        # 日付フォーマットパターン
        date_formats = [
            '%Y/%m/%d',
            '%Y-%m-%d',
            '%Y年%m月%d日',
        ]

        for fmt in date_formats:
            try:
                return datetime.strptime(value.strip(), fmt).date()
            except ValueError:
                continue

        return None

    @staticmethod
    def map_project_status(value: str) -> str:
        """
        受注ヨミ → project_status変換

        受注 → 受注確定
        A → A（そのまま保存）
        B → B（そのまま保存）
        ネタ → ネタ（そのまま保存）
        NG → NG
        空欄 → ネタ
        その他 → ネタ（デフォルト）
        """
        value = value.strip()

        status_map = {
            '受注': '受注確定',
            'A': 'A',
            'B': 'B',
            'ネタ': 'ネタ',
            'NG': 'NG',
            '': 'ネタ'  # 空欄は「ネタ」として扱う
        }

        return status_map.get(value, 'ネタ')  # デフォルトも「ネタ」

    @staticmethod
    def map_payment_status(value: str) -> str:
        """
        出金状況 → payment_status変換

        済 → paid
        未定 → pending (未払い)
        その他 → pending (未払い)
        """
        status_map = {
            '済': 'paid',
            '未定': 'pending',  # 'unpaid'は無効な値 → 'pending'（未払い）を使用
            '': 'pending'
        }

        return status_map.get(value.strip(), 'pending')


class ProjectImporter:
    """プロジェクトインポーター"""

    def __init__(self, dry_run: bool = False, verbosity: int = 1, progress_tracker=None):
        self.dry_run = dry_run
        self.verbosity = verbosity
        self.progress_tracker = progress_tracker
        self.stats = {
            'projects_created': 0,
            'clients_created': 0,
            'clients_existing': 0,
            'skipped': 0,
            'errors': []
        }

    def import_project(self, csv_mgmt_no: str, project_row: Dict) -> Optional[Project]:
        """
        プロジェクトをインポート

        Args:
            csv_mgmt_no: CSV管理番号
            project_row: 受注側CSV行データ

        Returns:
            作成されたProjectインスタンス（dry-runの場合はNone）
        """
        try:
            # 現場名チェック（空の場合はスキップ）
            site_name = project_row.get('現場名', '').strip()

            if self.progress_tracker:
                self.progress_tracker.add_log(f'管理No.{csv_mgmt_no}: データ検証中...', 'info')

            if not site_name:
                if self.verbosity >= 2:
                    self.log(f'  ⚠ スキップ: 現場名が空')
                if self.progress_tracker:
                    self.progress_tracker.add_log(f'管理No.{csv_mgmt_no}: スキップ（現場名が空）', 'warning')
                self.stats['skipped'] += 1
                return None

            # 管理番号変換
            app_mgmt_no = ManagementNoConverter.convert(csv_mgmt_no)

            if self.progress_tracker:
                self.progress_tracker.add_log(f'{app_mgmt_no} ({site_name}): 処理開始', 'info')

            # 既存チェック
            if Project.objects.filter(management_no=app_mgmt_no).exists():
                if self.verbosity >= 2:
                    self.log(f'  ⚠ スキップ: {app_mgmt_no} は既に存在')
                if self.progress_tracker:
                    self.progress_tracker.add_log(f'{app_mgmt_no}: スキップ（既に存在）', 'warning')
                self.stats['skipped'] += 1
                return None

            # 元請業者（ClientCompany）取得または作成
            if self.progress_tracker:
                self.progress_tracker.add_log(f'{app_mgmt_no}: 元請業者チェック中...', 'info')

            # 注意：CSVに「請負業者名」列が2回出現する場合がある（列7と列16）
            # CSVReader.read_csv()は最初に出現した列（列7）の値を使用するため、
            # 列16の「#VALUE!」エラーは読み込まれない
            client_name = project_row.get('請負業者名', '').strip()
            client_address = project_row.get('請負業社住所', '').strip()

            if not client_name and self.verbosity >= 2:
                self.log(f'    ⚠ 元請業者名が空です')

            client_company = self._get_or_create_client(client_name, client_address)

            # デバッグ: CSVから読み込んだ金額を確認
            order_amount_raw = project_row.get('請求額', '')
            order_amount = DataParser.parse_currency(order_amount_raw) or Decimal('0')

            if self.progress_tracker and self.verbosity >= 2:
                self.progress_tracker.add_log(f'{app_mgmt_no}: CSV請求額="{order_amount_raw}" → ¥{order_amount:,}', 'info')

            # プロジェクトデータ作成
            # NOTE: work_start_date と work_end_date は @property (read-only) なので、
            #       project_dataには含めず、後で _setup_progress_steps() で設定する

            # 諸経費を取得
            parking_fee = DataParser.parse_currency(project_row.get('駐車場代(税込)', '0')) or Decimal('0')
            expense_amount_1 = DataParser.parse_currency(project_row.get('諸経費代(税込)①', '0')) or Decimal('0')
            expense_amount_2 = DataParser.parse_currency(project_row.get('諸経費代(税込)②', '0')) or Decimal('0')

            # billing_amountを事前計算（Project.save()と同じロジック）
            billing_amount = order_amount + parking_fee + expense_amount_1 + expense_amount_2
            amount_difference = billing_amount - order_amount

            if self.progress_tracker and self.verbosity >= 2:
                self.progress_tracker.add_log(
                    f'{app_mgmt_no}: 請求額計算 = ¥{order_amount:,} + ¥{parking_fee:,} + ¥{expense_amount_1:,} + ¥{expense_amount_2:,} = ¥{billing_amount:,}',
                    'info'
                )

            project_data = {
                'management_no': app_mgmt_no,
                'site_name': site_name,
                'site_address': project_row.get('現場住所', ''),
                'work_type': project_row.get('種別', ''),
                'order_amount': order_amount,
                'project_status': DataParser.map_project_status(project_row.get('受注ヨミ', '')),
                'payment_due_date': DataParser.parse_date(project_row.get('入金予定日', '')),
                'contract_date': DataParser.parse_date(project_row.get('契約日', '')),
                'parking_fee': parking_fee,
                'billing_amount': billing_amount,  # 事前計算された請求額
                'amount_difference': amount_difference,  # 事前計算された金額差
                'project_manager': project_row.get('案件担当', ''),
                'invoice_issued': project_row.get('請求書発行', '0') != '0',
                'expense_item_1': project_row.get('諸経費項目①', ''),
                'expense_amount_1': expense_amount_1,
                'expense_item_2': project_row.get('諸経費項目②', ''),
                'expense_amount_2': expense_amount_2,
                'client_company': client_company,
            }

            if self.dry_run:
                self.log(f'  [DRY-RUN] Project作成: {app_mgmt_no} - {project_data["site_name"]}')
                if self.progress_tracker:
                    self.progress_tracker.add_log(f'{app_mgmt_no}: [DRY-RUN] プロジェクト作成完了', 'success')
                self.stats['projects_created'] += 1

                # Dry-run用にダミーのプロジェクトオブジェクトを返す（下請契約カウント用）
                class DummyProject:
                    def __init__(self, mgmt_no, site_name):
                        self.management_no = mgmt_no
                        self.site_name = site_name
                        self.pk = 0

                return DummyProject(app_mgmt_no, project_data["site_name"])

            # プロジェクト作成
            if self.progress_tracker:
                self.progress_tracker.add_log(f'{app_mgmt_no}: データベースに保存中...', 'info')

            # billing_amountはproject_dataに事前計算済み
            project = Project.objects.create(**project_data)

            # 進捗ステップ設定（エラーがあっても続行）
            try:
                if self.progress_tracker:
                    self.progress_tracker.add_log(f'{app_mgmt_no}: 進捗ステップ設定中...', 'info')
                self._setup_progress_steps(project, project_row)
            except Exception as step_error:
                if self.verbosity >= 2:
                    self.log(f'    ⚠ 進捗ステップ設定エラー: {str(step_error)}')
                if self.progress_tracker:
                    self.progress_tracker.add_log(f'{app_mgmt_no}: 進捗ステップ設定エラー', 'warning')

            # 進捗状態を計算してキャッシュに保存
            try:
                if self.progress_tracker:
                    self.progress_tracker.add_log(f'{app_mgmt_no}: 進捗状態を計算中...', 'info')
                result = project.calculate_current_stage()
                project.current_stage = result['stage']
                project.current_stage_color = result['color']
                project.save(update_fields=['current_stage', 'current_stage_color'])
            except Exception as stage_error:
                if self.verbosity >= 2:
                    self.log(f'    ⚠ 進捗状態計算エラー: {str(stage_error)}')
                if self.progress_tracker:
                    self.progress_tracker.add_log(f'{app_mgmt_no}: 進捗状態計算エラー', 'warning')

            # 利益を計算してキャッシュに保存
            try:
                if self.progress_tracker:
                    self.progress_tracker.add_log(f'{app_mgmt_no}: 利益を計算中...', 'info')
                project._update_profit_cache()
                project.save(update_fields=['gross_profit', 'profit_margin'])
            except Exception as profit_error:
                if self.verbosity >= 2:
                    self.log(f'    ⚠ 利益計算エラー: {str(profit_error)}')
                if self.progress_tracker:
                    self.progress_tracker.add_log(f'{app_mgmt_no}: 利益計算エラー', 'warning')

            self.stats['projects_created'] += 1

            if self.verbosity >= 1:
                self.log(f'  ✓ Project作成: {app_mgmt_no} - {project.site_name}')

            if self.progress_tracker:
                self.progress_tracker.add_log(f'{app_mgmt_no}: プロジェクト作成完了 ✓', 'success')

            return project

        except Exception as e:
            error_msg = f'プロジェクト作成エラー ({csv_mgmt_no}): {str(e)}'
            self.log(f'  ✗ {error_msg}')
            if self.progress_tracker:
                self.progress_tracker.add_log(f'{csv_mgmt_no}: エラー - {str(e)}', 'error')
            self.stats['errors'].append(error_msg)
            return None

    def _get_or_create_client(self, company_name: str, address: str) -> Optional[ClientCompany]:
        """元請業者を取得または作成"""
        if not company_name or company_name.strip() == '':
            return None

        company_name = company_name.strip()

        client, created = ClientCompany.objects.get_or_create(
            company_name=company_name,
            defaults={'address': address.strip() if address else ''}
        )

        if created:
            self.stats['clients_created'] += 1
            if self.verbosity >= 2:
                self.log(f'    ✓ ClientCompany作成: {company_name}')
        else:
            self.stats['clients_existing'] += 1
            if self.verbosity >= 2:
                self.log(f'    • ClientCompany既存: {company_name}')

        return client

    def _setup_progress_steps(self, project: Project, row: Dict):
        """進捗ステップを設定"""
        from datetime import datetime
        today = datetime.now().date()

        # 工事開始日（日付のみ設定、完了フラグは設定しない）
        construction_start = DataParser.parse_date(row.get('工事開始日', ''))
        if construction_start:
            set_step_scheduled_date(project, 'construction_start', construction_start.isoformat())

        # 工事終了日（完工日）
        completion_date = DataParser.parse_date(row.get('工事終了日', ''))
        if completion_date:
            set_step_scheduled_date(project, 'completion', completion_date.isoformat())

            # 完工日が過去の場合、自動的に完了としてマーク
            if completion_date < today:
                complete_step(project, 'completion', completed=True)

    def log(self, message: str):
        """ログ出力"""
        print(message)


class SubcontractImporter:
    """下請契約インポーター"""

    def __init__(self, dry_run: bool = False, verbosity: int = 1, progress_tracker=None):
        self.dry_run = dry_run
        self.verbosity = verbosity
        self.progress_tracker = progress_tracker
        self.stats = {
            'subcontracts_created': 0,
            'contractors_created': 0,
            'contractors_existing': 0,
            'errors': []
        }

    def import_subcontracts(self, project: Project, subcontract_rows: List[Dict]):
        """
        下請契約をインポート

        Args:
            project: 親プロジェクト
            subcontract_rows: 依頼側CSV行データリスト
        """
        if self.progress_tracker and len(subcontract_rows) > 0:
            self.progress_tracker.add_log(f'{project.management_no}: 下請契約{len(subcontract_rows)}件処理開始', 'info')

        for idx, row in enumerate(subcontract_rows, 1):
            try:
                if self.progress_tracker:
                    contractor_name = row.get('工事業者名', '不明')
                    self.progress_tracker.add_log(f'{project.management_no}: 下請契約{idx}/{len(subcontract_rows)} ({contractor_name})', 'info')
                self._import_single_subcontract(project, row)
            except Exception as e:
                error_msg = f'下請契約作成エラー: {str(e)}'
                self.log(f'  ✗ {error_msg}')
                if self.progress_tracker:
                    self.progress_tracker.add_log(f'{project.management_no}: 下請契約エラー - {str(e)}', 'error')
                self.stats['errors'].append(error_msg)

    def _import_single_subcontract(self, project: Project, row: Dict):
        """単一の下請契約をインポート"""
        # 下請業者（Contractor）取得または作成
        contractor = self._get_or_create_contractor(
            row.get('工事業者名', ''),
            row.get('工事業社住所', '')
        )

        if not contractor:
            if self.progress_tracker:
                self.progress_tracker.add_log(f'{project.management_no}: 下請業者名が空のためスキップ', 'warning')
            return

        # 契約金額
        contract_amount = DataParser.parse_currency(row.get('依頼金額', '0')) or Decimal('0')
        billed_amount = DataParser.parse_currency(row.get('被請求額', '0')) or Decimal('0')

        # 支払日
        payment_due_date = DataParser.parse_date(row.get('出金予定日', ''))
        payment_date = DataParser.parse_date(row.get('出金日', ''))

        # 支払状況
        payment_status = DataParser.map_payment_status(row.get('出金状況', ''))

        # 部材費
        material_item_1 = row.get('部材費項目①', '').strip()
        material_cost_1 = DataParser.parse_currency(row.get('部材費代(税込)①', '0')) or Decimal('0')
        material_item_2 = row.get('部材費項目②', '').strip()
        material_cost_2 = DataParser.parse_currency(row.get('部材費代(税込)②', '0')) or Decimal('0')
        material_item_3 = row.get('部材費項目③', '').strip()
        material_cost_3 = DataParser.parse_currency(row.get('部材費代(税込)③', '0')) or Decimal('0')

        # 下請契約データ
        subcontract_data = {
            'project': project,
            'contractor': contractor,
            'contract_amount': contract_amount,
            'billed_amount': billed_amount,
            'payment_due_date': payment_due_date,
            'payment_date': payment_date,
            'payment_status': payment_status,
            'step': 'step_construction_start',  # デフォルト: 着工
            'worker_type': 'external',  # 外注
            'material_item_1': material_item_1,
            'material_cost_1': material_cost_1,
            'material_item_2': material_item_2,
            'material_cost_2': material_cost_2,
            'material_item_3': material_item_3,
            'material_cost_3': material_cost_3,
        }

        if self.dry_run:
            self.log(f'    [DRY-RUN] Subcontract作成: {contractor.name} - ¥{contract_amount:,}')
            if self.progress_tracker:
                self.progress_tracker.add_log(f'{project.management_no}: [DRY-RUN] {contractor.name} ¥{contract_amount:,}', 'success')
            self.stats['subcontracts_created'] += 1
            return

        # 下請契約作成
        Subcontract.objects.create(**subcontract_data)
        self.stats['subcontracts_created'] += 1

        if self.verbosity >= 2:
            self.log(f'    ✓ Subcontract作成: {contractor.name} - ¥{contract_amount:,}')

        if self.progress_tracker:
            self.progress_tracker.add_log(f'{project.management_no}: ✓ {contractor.name} ¥{contract_amount:,}', 'success')

    def _get_or_create_contractor(self, contractor_name: str, address: str) -> Optional[Contractor]:
        """下請業者を取得または作成"""
        if not contractor_name or contractor_name.strip() == '':
            return None

        contractor_name = contractor_name.strip()

        contractor, created = Contractor.objects.get_or_create(
            name=contractor_name,
            defaults={
                'address': address.strip() if address else '',
                'contractor_type': 'company'  # 'partner'は無効な値 → 'company'（協力会社）を使用
            }
        )

        if created:
            self.stats['contractors_created'] += 1
            if self.verbosity >= 2:
                self.log(f'    ✓ Contractor作成: {contractor_name}')
        else:
            self.stats['contractors_existing'] += 1

        return contractor

    def log(self, message: str):
        """ログ出力"""
        print(message)


class Command(BaseCommand):
    help = 'CSV一括インポート - 受注側・依頼側FMTから案件データをインポート'

    def add_arguments(self, parser):
        parser.add_argument(
            'order_csv',
            type=str,
            help='受注側CSVファイルパス'
        )
        parser.add_argument(
            'subcontract_csv',
            type=str,
            help='依頼側CSVファイルパス'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='ドライラン（保存しない）'
        )
        parser.add_argument(
            '--no-backup',
            action='store_true',
            help='バックアップをスキップ'
        )
        parser.add_argument(
            '--progress-file',
            type=str,
            help='進捗ファイルパス（ProgressTracker用）',
            default=None
        )

    def handle(self, *args, **options):
        order_csv = options['order_csv']
        subcontract_csv = options['subcontract_csv']
        dry_run = options['dry_run']
        no_backup = options['no_backup']
        verbosity = options['verbosity']
        progress_file = options.get('progress_file')

        # ProgressTrackerの初期化
        progress_tracker = None
        if progress_file:
            from order_management.utils.progress_tracker import ProgressTracker
            progress_tracker = ProgressTracker(progress_file)

        self.stdout.write('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━')
        self.stdout.write('CSV一括インポート開始')
        self.stdout.write('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━')

        if dry_run:
            self.stdout.write(self.style.WARNING('⚠ DRY-RUNモード（データは保存されません）'))

        try:
            # 1. CSV読み込み
            self.stdout.write('\n📂 CSV読み込み中...')
            order_rows = CSVReader.read_csv(order_csv)
            subcontract_rows = CSVReader.read_csv(subcontract_csv)

            self.stdout.write(self.style.SUCCESS(f'  ✓ 受注側CSV: {len(order_rows)}行読み込み'))
            self.stdout.write(self.style.SUCCESS(f'  ✓ 依頼側CSV: {len(subcontract_rows)}行読み込み'))

            # 2. データ結合
            self.stdout.write('\n🔗 管理番号でグループ化中...')
            merged_data = DataMerger.merge(order_rows, subcontract_rows)

            # projectデータがあるもののみ
            valid_groups = {k: v for k, v in merged_data.items() if v['project']}

            self.stdout.write(self.style.SUCCESS(f'  ✓ グループ化完了: {len(valid_groups)}件'))

            # 3. バックアップ作成
            if not dry_run and not no_backup:
                self.stdout.write('\n💾 バックアップ作成中...')
                try:
                    call_command('backup_data', '--no-media', verbosity=0)
                    self.stdout.write(self.style.SUCCESS('  ✓ バックアップ完了'))
                except Exception as e:
                    self.stdout.write(self.style.WARNING(f'  ⚠ バックアップ失敗: {str(e)}'))

            # 4. インポート処理
            self.stdout.write(f'\n📥 インポート処理中... (0/{len(valid_groups)})')

            project_importer = ProjectImporter(dry_run=dry_run, verbosity=verbosity, progress_tracker=progress_tracker)
            subcontract_importer = SubcontractImporter(dry_run=dry_run, verbosity=verbosity, progress_tracker=progress_tracker)

            processed = 0

            # Project.save()をモンキーパッチしてwitness_statusエラーを回避
            original_save = Project.save

            def patched_save(self, *args, **kwargs):
                """インポート時専用のsave - witness_status書き込みをスキップ"""
                # 元のsave()を呼ぶ前に、NGステータスのロジックをスキップ
                # priority_scoreは計算するが、witness_status等への書き込みはしない
                self.priority_score = self._calculate_priority_score()

                # 親クラスのsave()を直接呼ぶ
                super(Project, self).save(*args, **kwargs)

            # save()をパッチ
            Project.save = patched_save

            try:
                for csv_mgmt_no, data in valid_groups.items():
                    processed += 1

                    if verbosity >= 1:
                        print(f'\n[{processed}/{len(valid_groups)}] {csv_mgmt_no}: {data["project"].get("現場名", "不明")}')

                    try:
                        with transaction.atomic():
                            # プロジェクトインポート
                            project = project_importer.import_project(csv_mgmt_no, data['project'])

                            # 下請契約インポート
                            if project and data['subcontracts']:
                                subcontract_importer.import_subcontracts(project, data['subcontracts'])

                            if dry_run:
                                raise Exception('DRY-RUNモード: ロールバック')
                    except Exception as e:
                        if 'DRY-RUNモード' not in str(e):
                            # Dry-run以外のエラーの場合のみログ出力（既にimport_project内でログ出力済み）
                            pass
            finally:
                # save()を復元
                Project.save = original_save

        except KeyboardInterrupt:
            self.stdout.write(self.style.ERROR('\n\n✗ 中断されました'))
            return

        # 5. 統計表示
        self.stdout.write('\n\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━')
        self.stdout.write('インポート統計')
        self.stdout.write('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━')

        self.stdout.write(f'プロジェクト: {project_importer.stats["projects_created"]}件作成')
        self.stdout.write(f'元請業者: {project_importer.stats["clients_created"]}件作成, '
                         f'{project_importer.stats["clients_existing"]}件既存')
        self.stdout.write(f'下請業者: {subcontract_importer.stats["contractors_created"]}件作成, '
                         f'{subcontract_importer.stats["contractors_existing"]}件既存')
        self.stdout.write(f'下請契約: {subcontract_importer.stats["subcontracts_created"]}件作成')
        self.stdout.write(f'スキップ: {project_importer.stats["skipped"]}件')

        total_errors = len(project_importer.stats['errors']) + len(subcontract_importer.stats['errors'])

        if total_errors > 0:
            self.stdout.write(self.style.ERROR(f'エラー: {total_errors}件'))

            if verbosity >= 2:
                self.stdout.write('\n⚠ エラー詳細:')
                for error in project_importer.stats['errors'] + subcontract_importer.stats['errors']:
                    self.stdout.write(f'  • {error}')
        else:
            self.stdout.write(self.style.SUCCESS('エラー: 0件'))

        self.stdout.write('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━')

        if dry_run:
            self.stdout.write(self.style.WARNING('\n⚠ DRY-RUNモードのため、データは保存されていません'))
        else:
            self.stdout.write(self.style.SUCCESS('\n✓ インポート完了！'))
