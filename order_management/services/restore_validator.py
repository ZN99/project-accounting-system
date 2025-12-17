"""リストア時のバックアップファイル検証サービス

このモジュールは、リストア実行前に以下の検証を実行します：
1. バックアップファイルの構造検証
2. メタデータの検証（バージョン互換性）
3. データの整合性チェック
4. FK前方参照の解決
"""

from typing import Dict, List, Any, Tuple
import json
import zipfile
import django
from django.conf import settings
import logging

logger = logging.getLogger(__name__)


class RestoreValidator:
    """リストアデータの整合性を検証するクラス"""

    def __init__(self, backup_file_path: str):
        """
        Args:
            backup_file_path: バックアップZIPファイルのパス
        """
        self.backup_file_path = backup_file_path
        self.errors = []
        self.warnings = []
        self.info = []
        self.metadata = None
        self.backup_data = None

    def validate_all(self) -> Dict[str, Any]:
        """
        全ての検証を実行

        Returns:
            dict: 検証結果のサマリー
            {
                'success': bool,
                'errors': List[str],
                'warnings': List[str],
                'info': List[str],
                'metadata': Dict[str, Any]
            }
        """
        logger.info(f'バックアップファイルの検証を開始: {self.backup_file_path}')

        # 各検証を実行
        self._validate_zip_structure()
        if self.metadata:  # ZIP構造が正常な場合のみ続行
            self._validate_metadata()
            self._validate_version_compatibility()
            self._validate_data_structure()
            self._check_fk_forward_references()

        logger.info(f'検証完了: エラー{len(self.errors)}件, 警告{len(self.warnings)}件')

        return {
            'success': len(self.errors) == 0,
            'errors': self.errors,
            'warnings': self.warnings,
            'info': self.info,
            'metadata': self.metadata
        }

    def _validate_zip_structure(self):
        """ZIPファイルの構造を検証"""
        logger.info('ZIPファイル構造検証開始...')

        try:
            with zipfile.ZipFile(self.backup_file_path, 'r') as zip_file:
                # ファイルリストを取得
                file_list = zip_file.namelist()

                # 必須ファイルの存在確認
                required_files = ['data.json', 'metadata.json']
                for required_file in required_files:
                    if required_file not in file_list:
                        self.errors.append(f'必須ファイル {required_file} が見つかりません')
                        return

                # metadata.json を読み込み
                try:
                    with zip_file.open('metadata.json') as meta_file:
                        self.metadata = json.load(meta_file)
                        self.info.append('metadata.json を読み込みました')
                except json.JSONDecodeError as e:
                    self.errors.append(f'metadata.json のJSON解析エラー: {str(e)}')
                    return

                # data.json を読み込み（サイズチェックのみ）
                data_info = zip_file.getinfo('data.json')
                data_size_mb = data_info.file_size / (1024 * 1024)
                self.info.append(f'data.json サイズ: {data_size_mb:.2f} MB')

                # media フォルダの存在確認
                media_files = [f for f in file_list if f.startswith('media/')]
                if media_files:
                    self.info.append(f'メディアファイル: {len(media_files)}個')
                else:
                    self.warnings.append('メディアファイルが含まれていません')

        except zipfile.BadZipFile:
            self.errors.append('ZIPファイルが破損しています')
        except FileNotFoundError:
            self.errors.append(f'ファイルが見つかりません: {self.backup_file_path}')
        except Exception as e:
            self.errors.append(f'ZIPファイル検証エラー: {str(e)}')

    def _validate_metadata(self):
        """メタデータの検証"""
        logger.info('メタデータ検証開始...')

        if not self.metadata:
            self.errors.append('メタデータが読み込まれていません')
            return

        # 必須フィールドの確認
        required_fields = ['backup_version', 'created_at', 'django_version', 'total_records']
        for field in required_fields:
            if field not in self.metadata:
                self.errors.append(f'メタデータに必須フィールド {field} がありません')

        # バックアップバージョンの確認
        backup_version = self.metadata.get('backup_version', '0.0')
        if backup_version != '1.0':
            self.warnings.append(f'バックアップバージョン {backup_version} は未サポートの可能性があります')

        # 総レコード数の確認
        total_records = self.metadata.get('total_records', 0)
        self.info.append(f'総レコード数: {total_records}件')

        # モデル統計の確認
        models = self.metadata.get('models', {})
        self.info.append(f'含まれるモデル: {len(models)}種類')

    def _validate_version_compatibility(self):
        """バージョン互換性の検証"""
        logger.info('バージョン互換性検証開始...')

        if not self.metadata:
            return

        # Djangoバージョンの比較
        backup_django_version = self.metadata.get('django_version', '')
        current_django_version = django.get_version()

        if backup_django_version != current_django_version:
            self.warnings.append(
                f'Djangoバージョンが異なります（バックアップ: {backup_django_version}, 現在: {current_django_version}）'
            )

        # データベースエンジンの比較
        backup_db_engine = self.metadata.get('database_engine', '')
        current_db_engine = settings.DATABASES['default']['ENGINE'].split('.')[-1]

        if backup_db_engine and backup_db_engine != current_db_engine:
            self.warnings.append(
                f'データベースエンジンが異なります（バックアップ: {backup_db_engine}, 現在: {current_db_engine}）'
            )

    def _validate_data_structure(self):
        """データ構造の検証"""
        logger.info('データ構造検証開始...')

        try:
            with zipfile.ZipFile(self.backup_file_path, 'r') as zip_file:
                # data.json を読み込み
                with zip_file.open('data.json') as data_file:
                    try:
                        self.backup_data = json.load(data_file)

                        # 基本的な形式チェック
                        if not isinstance(self.backup_data, list):
                            self.errors.append('data.json の形式が不正です（リスト形式である必要があります）')
                            return

                        # 空チェック
                        if len(self.backup_data) == 0:
                            self.errors.append('data.json にデータが含まれていません')
                            return

                        # 各レコードの基本構造チェック
                        for i, record in enumerate(self.backup_data[:10]):  # 最初の10件のみチェック
                            if not isinstance(record, dict):
                                self.errors.append(f'レコード {i} の形式が不正です')
                                continue

                            if 'model' not in record:
                                self.errors.append(f'レコード {i} に model フィールドがありません')

                            if 'pk' not in record:
                                self.errors.append(f'レコード {i} に pk フィールドがありません')

                            if 'fields' not in record:
                                self.errors.append(f'レコード {i} に fields フィールドがありません')

                        self.info.append(f'data.json: {len(self.backup_data)}件のレコード')

                    except json.JSONDecodeError as e:
                        self.errors.append(f'data.json のJSON解析エラー: {str(e)}')

        except Exception as e:
            self.errors.append(f'データ構造検証エラー: {str(e)}')

    def _check_fk_forward_references(self):
        """FK前方参照の確認"""
        logger.info('FK前方参照チェック開始...')

        if not self.backup_data:
            return

        # PKのセットを構築（どのモデルにどのPKが存在するか）
        existing_pks = {}
        for record in self.backup_data:
            model = record.get('model')
            pk = record.get('pk')
            if model and pk:
                if model not in existing_pks:
                    existing_pks[model] = set()
                existing_pks[model].add(pk)

        # FK参照の検証
        fk_violations = []
        for record in self.backup_data:
            model = record.get('model')
            pk = record.get('pk')
            fields = record.get('fields', {})

            # 重要なFKフィールドをチェック
            fk_mappings = {
                'order_management.project': [
                    ('client_company', 'order_management.clientcompany'),
                ],
                'order_management.projectprogressstep': [
                    ('project', 'order_management.project'),
                    ('template', 'order_management.progresssteptemplate'),
                ],
                'subcontract_management.subcontract': [
                    ('project', 'order_management.project'),
                    ('contractor', 'subcontract_management.contractor'),
                ],
            }

            if model in fk_mappings:
                for fk_field, target_model in fk_mappings[model]:
                    fk_value = fields.get(fk_field)
                    if fk_value:
                        # 参照先が存在するかチェック
                        if target_model not in existing_pks or fk_value not in existing_pks[target_model]:
                            fk_violations.append(
                                f'{model}(pk={pk}).{fk_field}={fk_value}: 参照先{target_model}が存在しません'
                            )

        if fk_violations:
            # 最初の10件のみ警告として表示
            for violation in fk_violations[:10]:
                self.warnings.append(violation)

            if len(fk_violations) > 10:
                self.warnings.append(f'...他 {len(fk_violations) - 10}件のFK参照違反')


def validate_restore(backup_file_path: str) -> Dict[str, Any]:
    """
    リストアファイルの検証を実行する便利関数

    Args:
        backup_file_path: バックアップZIPファイルのパス

    Returns:
        dict: 検証結果
    """
    validator = RestoreValidator(backup_file_path)
    return validator.validate_all()
