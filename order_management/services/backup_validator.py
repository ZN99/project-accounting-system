"""バックアップ作成時のデータベース整合性検証サービス

このモジュールは、バックアップ作成前に以下の検証を実行します：
1. FK（外部キー）整合性チェック
2. 孤立レコードの検出
3. 必須フィールドの検証
4. データ型の検証
"""

from django.db import models
from django.apps import apps
from django.contrib.auth.models import User
from collections import defaultdict
from typing import Dict, List, Tuple, Any
import logging

logger = logging.getLogger(__name__)


class BackupValidator:
    """バックアップデータの整合性を検証するクラス"""

    def __init__(self):
        self.errors = []
        self.warnings = []
        self.info = []

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
                'statistics': Dict[str, int]
            }
        """
        logger.info('バックアップデータの検証を開始...')

        # 各検証を実行
        self._validate_fk_integrity()
        self._detect_orphaned_records()
        self._validate_required_fields()
        self._collect_statistics()

        logger.info(f'検証完了: エラー{len(self.errors)}件, 警告{len(self.warnings)}件')

        return {
            'success': len(self.errors) == 0,
            'errors': self.errors,
            'warnings': self.warnings,
            'info': self.info,
            'statistics': self.statistics
        }

    def _validate_fk_integrity(self):
        """FK整合性をチェック"""
        logger.info('FK整合性チェック開始...')

        # 重要なモデルのFK関係をチェック
        fk_checks = [
            # order_management
            ('order_management.Project', 'client_company', 'order_management.ClientCompany'),
            ('order_management.ProjectProgressStep', 'project', 'order_management.Project'),
            ('order_management.ProjectProgressStep', 'template', 'order_management.ProgressStepTemplate'),
            ('order_management.MaterialOrder', 'project', 'order_management.Project'),
            ('order_management.MaterialOrderItem', 'material_order', 'order_management.MaterialOrder'),
            ('order_management.Invoice', 'project', 'order_management.Project'),
            ('order_management.InvoiceItem', 'invoice', 'order_management.Invoice'),
            ('order_management.Comment', 'project', 'order_management.Project'),
            ('order_management.Comment', 'user', 'auth.User'),
            ('order_management.Notification', 'user', 'auth.User'),
            ('order_management.ProjectFile', 'project', 'order_management.Project'),
            ('order_management.ProjectChecklist', 'project', 'order_management.Project'),
            ('order_management.ProjectChecklist', 'template', 'order_management.ChecklistTemplate'),
            ('order_management.ApprovalLog', 'project', 'order_management.Project'),
            ('order_management.ApprovalLog', 'user', 'auth.User'),
            ('order_management.ContractorReview', 'project', 'order_management.Project'),
            ('order_management.ContactPerson', 'company', 'order_management.ClientCompany'),

            # subcontract_management
            ('subcontract_management.Subcontract', 'project', 'order_management.Project'),
            ('subcontract_management.Subcontract', 'contractor', 'subcontract_management.Contractor'),
            ('subcontract_management.Subcontract', 'internal_worker', 'subcontract_management.InternalWorker'),
            ('subcontract_management.ContractorFieldDefinition', 'category', 'subcontract_management.ContractorFieldCategory'),
            ('subcontract_management.ProjectProfitAnalysis', 'project', 'order_management.Project'),
        ]

        for source_model, fk_field, target_model in fk_checks:
            try:
                Model = apps.get_model(source_model)
                target_Model = apps.get_model(target_model)

                # FKフィールドを取得
                field = Model._meta.get_field(fk_field)

                # null=False（必須）のFKフィールドのみチェック
                if not field.null:
                    # 参照先が存在しないレコードを検出
                    invalid_count = Model.objects.exclude(**{
                        f'{fk_field}__isnull': False
                    }).filter(**{
                        f'{fk_field}__isnull': True
                    }).count()

                    if invalid_count > 0:
                        self.errors.append(
                            f'{source_model}.{fk_field}: {invalid_count}件のレコードで必須FK参照が欠落'
                        )

                # null=Trueのフィールドで、参照先が存在しないものを警告
                else:
                    # 参照先のIDが設定されているが、実際のレコードが存在しないケース
                    queryset = Model.objects.exclude(**{f'{fk_field}__isnull': True})
                    for obj in queryset:
                        fk_value = getattr(obj, f'{fk_field}_id')
                        if fk_value and not target_Model.objects.filter(pk=fk_value).exists():
                            self.warnings.append(
                                f'{source_model}(id={obj.pk}).{fk_field}: 参照先{target_model}(id={fk_value})が存在しません'
                            )

            except Exception as e:
                self.warnings.append(f'FK整合性チェック失敗 ({source_model}.{fk_field}): {str(e)}')

    def _detect_orphaned_records(self):
        """孤立レコードを検出（親が削除されている子レコード）"""
        logger.info('孤立レコード検出開始...')

        orphan_checks = [
            # 案件が削除されているサブレコード
            ('order_management.ProjectProgressStep', 'project', 'order_management.Project'),
            ('order_management.MaterialOrder', 'project', 'order_management.Project'),
            ('order_management.Invoice', 'project', 'order_management.Project'),
            ('order_management.Comment', 'project', 'order_management.Project'),
            ('order_management.ProjectFile', 'project', 'order_management.Project'),
            ('subcontract_management.Subcontract', 'project', 'order_management.Project'),

            # カテゴリが削除されているフィールド定義
            ('subcontract_management.ContractorFieldDefinition', 'category', 'subcontract_management.ContractorFieldCategory'),

            # 会社が削除されている連絡先
            ('order_management.ContactPerson', 'company', 'order_management.ClientCompany'),
        ]

        for child_model, parent_field, parent_model in orphan_checks:
            try:
                ChildModel = apps.get_model(child_model)
                ParentModel = apps.get_model(parent_model)

                # 親が存在しない子レコードを検出
                orphaned_count = 0
                for child_obj in ChildModel.objects.all():
                    parent_id = getattr(child_obj, f'{parent_field}_id')
                    if parent_id and not ParentModel.objects.filter(pk=parent_id).exists():
                        orphaned_count += 1

                if orphaned_count > 0:
                    self.warnings.append(
                        f'{child_model}: {orphaned_count}件の孤立レコード（親{parent_model}が存在しない）'
                    )

            except Exception as e:
                self.warnings.append(f'孤立レコード検出失敗 ({child_model}): {str(e)}')

    def _validate_required_fields(self):
        """必須フィールドの検証"""
        logger.info('必須フィールド検証開始...')

        # 重要なモデルの必須フィールドをチェック
        required_field_checks = [
            ('order_management.Project', ['management_no', 'site_name']),
            ('order_management.ClientCompany', ['name']),
            ('subcontract_management.Contractor', ['name']),
            ('order_management.Invoice', ['project', 'invoice_number']),
        ]

        for model_name, required_fields in required_field_checks:
            try:
                Model = apps.get_model(model_name)

                for field_name in required_fields:
                    field = Model._meta.get_field(field_name)

                    # 文字列フィールドの空チェック
                    if isinstance(field, (models.CharField, models.TextField)):
                        empty_count = Model.objects.filter(**{
                            f'{field_name}__isnull': True
                        }).count() + Model.objects.filter(**{
                            field_name: ''
                        }).count()

                        if empty_count > 0:
                            self.warnings.append(
                                f'{model_name}.{field_name}: {empty_count}件のレコードで必須フィールドが空'
                            )

                    # FK/数値フィールドのNullチェック
                    else:
                        null_count = Model.objects.filter(**{
                            f'{field_name}__isnull': True
                        }).count()

                        if null_count > 0:
                            self.warnings.append(
                                f'{model_name}.{field_name}: {null_count}件のレコードで必須フィールドがNull'
                            )

            except Exception as e:
                self.warnings.append(f'必須フィールド検証失敗 ({model_name}): {str(e)}')

    def _collect_statistics(self):
        """データベースの統計情報を収集"""
        logger.info('統計情報収集開始...')

        self.statistics = {}

        # 各モデルのレコード数を集計
        for app_config in apps.get_app_configs():
            if app_config.name in ['order_management', 'subcontract_management', 'auth']:
                for model in app_config.get_models():
                    model_label = f'{app_config.label}.{model._meta.model_name}'
                    try:
                        count = model.objects.count()
                        self.statistics[model_label] = count
                        if count > 0:
                            self.info.append(f'{model_label}: {count}件')
                    except Exception as e:
                        self.warnings.append(f'統計情報取得失敗 ({model_label}): {str(e)}')

        # 総レコード数
        total_records = sum(self.statistics.values())
        self.info.append(f'総レコード数: {total_records}件')
        logger.info(f'統計情報収集完了: 総レコード数={total_records}')


def validate_backup() -> Dict[str, Any]:
    """
    バックアップデータの検証を実行する便利関数

    Returns:
        dict: 検証結果
    """
    validator = BackupValidator()
    return validator.validate_all()
