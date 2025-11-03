"""
銀行振込ファイル生成ユーティリティ
全銀協フォーマット対応
"""
import csv
import io
from datetime import datetime
from decimal import Decimal
from typing import List, Dict, Any
from django.http import HttpResponse


class BankTransferFileGenerator:
    """銀行振込ファイル生成クラス"""

    def __init__(self):
        self.company_info = {
            'name': '建築派遣管理株式会社',
            'code': '1234567',  # 会社コード
            'bank_code': '0001',  # みずほ銀行
            'branch_code': '001',  # 本店
            'account_number': '1234567',
            'account_holder': 'ケンチクハケンカンリ(カ',
        }

    def generate_zengin_format(self, transfers: List[Dict[str, Any]], transfer_date: datetime = None) -> str:
        """
        全銀協フォーマットの振込ファイルを生成

        Args:
            transfers: 振込データのリスト
            transfer_date: 振込実行日

        Returns:
            全銀協フォーマットの文字列
        """
        if transfer_date is None:
            transfer_date = datetime.now()

        lines = []

        # ヘッダーレコード (1行目)
        header = self._create_header_record(transfer_date, len(transfers))
        lines.append(header)

        # データレコード (各振込データ)
        for i, transfer in enumerate(transfers, 1):
            data_record = self._create_data_record(transfer, i)
            lines.append(data_record)

        # トレーラーレコード (最終行)
        total_amount = sum(transfer['amount'] for transfer in transfers)
        trailer = self._create_trailer_record(len(transfers), total_amount)
        lines.append(trailer)

        return '\n'.join(lines)

    def _create_header_record(self, transfer_date: datetime, record_count: int) -> str:
        """ヘッダーレコード生成"""
        return (
            '1'  # レコード区分 (1:ヘッダー)
            + '21'  # 種別コード (21:総合振込)
            + '0'  # コード区分 (0:JIS)
            + self.company_info['code'].ljust(10)  # 委託者コード
            + self.company_info['name'][:40].ljust(40)  # 委託者名
            + transfer_date.strftime('%m%d')  # 振込指定日 (MMDD)
            + self.company_info['bank_code']  # 仕向銀行番号
            + self.company_info['bank_code'][:15].ljust(15)  # 仕向銀行名
            + self.company_info['branch_code']  # 仕向支店番号
            + self.company_info['branch_code'][:15].ljust(15)  # 仕向支店名
            + '1'  # 預金種目 (1:普通)
            + self.company_info['account_number'].rjust(7, '0')  # 口座番号
            + self.company_info['account_holder'][:30].ljust(30)  # 口座名義人
            + ' ' * 17  # ダミー項目
        )

    def _create_data_record(self, transfer: Dict[str, Any], sequence: int) -> str:
        """データレコード生成"""
        return (
            '2'  # レコード区分 (2:データ)
            + str(sequence).zfill(6)  # 連番
            + transfer['bank_code'][:4].ljust(4)  # 被仕向銀行番号
            + transfer['bank_name'][:15].ljust(15)  # 被仕向銀行名
            + transfer['branch_code'][:3].ljust(3)  # 被仕向支店番号
            + transfer['branch_name'][:15].ljust(15)  # 被仕向支店名
            + '1'  # 預金種目 (1:普通, 2:当座, 4:貯蓄)
            + transfer['account_number'].rjust(7, '0')  # 口座番号
            + transfer['account_holder'][:30].ljust(30)  # 受取人名
            + str(int(transfer['amount'])).zfill(10)  # 振込金額
            + '0'  # 新規コード (0:新規)
            + transfer['client_code'][:10].ljust(10)  # 顧客コード1
            + transfer['transfer_purpose'][:20].ljust(20)  # 振込依頼人名
            + ' ' * 7  # ダミー項目
        )

    def _create_trailer_record(self, record_count: int, total_amount: Decimal) -> str:
        """トレーラーレコード生成"""
        return (
            '8'  # レコード区分 (8:トレーラー)
            + str(record_count).zfill(6)  # 合計件数
            + str(int(total_amount)).zfill(12)  # 合計金額
            + ' ' * 101  # ダミー項目
        )

    def generate_csv_format(self, transfers: List[Dict[str, Any]]) -> str:
        """
        CSV形式の振込ファイルを生成

        Args:
            transfers: 振込データのリスト

        Returns:
            CSV形式の文字列
        """
        output = io.StringIO()
        writer = csv.writer(output)

        # ヘッダー行
        headers = [
            '振込先名', '銀行名', '支店名', '口座種別', '口座番号',
            '振込金額', '振込依頼人名', '備考'
        ]
        writer.writerow(headers)

        # データ行
        for transfer in transfers:
            row = [
                transfer['account_holder'],
                transfer['bank_name'],
                transfer['branch_name'],
                transfer['account_type_display'],
                transfer['account_number'],
                f"¥{transfer['amount']:,}",
                transfer['transfer_purpose'],
                transfer['memo']
            ]
            writer.writerow(row)

        return output.getvalue()

    def create_http_response(self, content: str, filename: str, content_type: str = 'text/plain') -> HttpResponse:
        """
        ダウンロード用のHTTPレスポンスを作成

        Args:
            content: ファイル内容
            filename: ファイル名
            content_type: コンテンツタイプ

        Returns:
            HttpResponse
        """
        response = HttpResponse(content, content_type=content_type)
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response


def convert_contractor_to_transfer_data(contractor_payment: Dict[str, Any]) -> Dict[str, Any]:
    """
    業者支払いデータを振込データ形式に変換

    Args:
        contractor_payment: 業者支払いデータ

    Returns:
        振込データ形式の辞書
    """
    contractor = contractor_payment.get('contractor')

    # 銀行コードのマッピング（実際の銀行コードを使用）
    bank_code_mapping = {
        'みずほ銀行': '0001',
        '三菱UFJ銀行': '0005',
        '三井住友銀行': '0009',
        'りそな銀行': '0010',
        '埼玉りそな銀行': '0017',
        'ゆうちょ銀行': '9900',
    }

    # 支店コードの生成（実際には銀行の支店コード一覧から取得）
    branch_code = '001'  # デフォルト値

    # 口座種別のマッピング
    account_type_mapping = {
        'ordinary': ('1', '普通'),
        'current': ('2', '当座'),
        'savings': ('4', '貯蓄'),
    }

    account_type_code, account_type_display = account_type_mapping.get(
        contractor.account_type if contractor else 'ordinary', ('1', '普通')
    )

    return {
        'bank_code': bank_code_mapping.get(contractor.bank_name if contractor else '', '0000'),
        'bank_name': contractor.bank_name if contractor else '',
        'branch_code': branch_code,
        'branch_name': contractor.branch_name if contractor else '',
        'account_type': account_type_code,
        'account_type_display': account_type_display,
        'account_number': contractor.account_number if contractor else '',
        'account_holder': contractor.account_holder if contractor else '',
        'amount': contractor_payment.get('total_amount', 0),
        'client_code': str(contractor.id if contractor else ''),
        'transfer_purpose': f"工事代金 {contractor_payment.get('sites_count', 0)}件分",
        'memo': f"振込日: {datetime.now().strftime('%Y/%m/%d')}",
    }


def generate_bulk_transfer_file(contractor_payments: List[Dict[str, Any]], file_format: str = 'zengin') -> tuple:
    """
    一括振込ファイルを生成

    Args:
        contractor_payments: 業者支払いデータのリスト
        file_format: ファイル形式 ('zengin' or 'csv')

    Returns:
        (ファイル内容, ファイル名, コンテンツタイプ) のタプル
    """
    generator = BankTransferFileGenerator()

    # 業者支払いデータを振込データに変換
    transfers = [convert_contractor_to_transfer_data(cp) for cp in contractor_payments]

    # 銀行口座情報が不完全なデータを除外
    valid_transfers = [
        t for t in transfers
        if t['bank_name'] and t['account_number'] and t['account_holder']
    ]

    if not valid_transfers:
        raise ValueError("振込可能な業者データがありません。銀行口座情報を確認してください。")

    current_date = datetime.now()

    if file_format == 'zengin':
        content = generator.generate_zengin_format(valid_transfers)
        filename = f"furikomi_zengin_{current_date.strftime('%Y%m%d_%H%M%S')}.txt"
        content_type = 'text/plain'
    elif file_format == 'csv':
        content = generator.generate_csv_format(valid_transfers)
        filename = f"furikomi_list_{current_date.strftime('%Y%m%d_%H%M%S')}.csv"
        content_type = 'text/csv'
    else:
        raise ValueError("サポートされていないファイル形式です。")

    return content, filename, content_type