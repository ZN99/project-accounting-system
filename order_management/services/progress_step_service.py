"""
進捗ステップ管理サービス

プロジェクトの進捗ステップ（スケジュール）の作成・更新を管理します。
"""
import json
from datetime import datetime
from django.utils import timezone
from order_management.models import ProgressStepTemplate, ProjectProgressStep


# フロントエンドのステップキーとテンプレート情報のマッピング
STEP_TEMPLATES = {
    # デフォルトステップ
    'attendance': {
        'name': '立ち会い日',
        'icon': 'fas fa-user-check',
        'order': 1,
        'is_default': False,
        'field_type': 'date'
    },
    'survey': {
        'name': '現調日',
        'icon': 'fas fa-clipboard-list',
        'order': 2,
        'is_default': False,
        'field_type': 'date'
    },
    'estimate': {
        'name': '見積書発行日',
        'icon': 'fas fa-file-invoice',
        'order': 3,
        'is_default': True,
        'field_type': 'date'
    },
    'construction_start': {
        'name': '着工日',
        'icon': 'fas fa-hard-hat',
        'order': 4,
        'is_default': True,
        'field_type': 'date'
    },
    'completion': {
        'name': '完工日',
        'icon': 'fas fa-check-circle',
        'order': 5,
        'is_default': True,
        'field_type': 'date'
    },
    # 追加可能なステップ
    'contract': {
        'name': '契約',
        'icon': 'fas fa-handshake',
        'order': 6,
        'is_default': False,
        'field_type': 'date'
    },
    'invoice': {
        'name': '請求書発行',
        'icon': 'fas fa-file-invoice-dollar',
        'order': 7,
        'is_default': False,
        'field_type': 'date'
    },
    'permit_application': {
        'name': '許可申請',
        'icon': 'fas fa-file-signature',
        'order': 8,
        'is_default': False,
        'field_type': 'date'
    },
    'material_order': {
        'name': '資材発注',
        'icon': 'fas fa-boxes',
        'order': 9,
        'is_default': False,
        'field_type': 'date'
    },
    'inspection': {
        'name': '検査',
        'icon': 'fas fa-clipboard-check',
        'order': 10,
        'is_default': False,
        'field_type': 'date'
    }
}


def ensure_step_templates():
    """
    すべてのステップテンプレートがDBに存在することを確認し、
    存在しない場合は作成する。

    Returns:
        dict: ステップキーをキー、ProgressStepTemplateインスタンスを値とする辞書
    """
    templates = {}

    for key, config in STEP_TEMPLATES.items():
        # name フィールドでテンプレートを検索（一意性を保証）
        template, created = ProgressStepTemplate.objects.get_or_create(
            name=config['name'],
            defaults={
                'icon': config['icon'],
                'order': config['order'],
                'is_default': config['is_default'],
                'field_type': config['field_type'],
                'is_system': True  # システムで管理されるテンプレート
            }
        )
        templates[key] = template

        if created:
            print(f"✓ ProgressStepTemplate created: {config['name']}")

    return templates


def save_project_progress_steps(project, schedule_steps_json):
    """
    プロジェクトの進捗ステップを保存する。

    Args:
        project: Projectインスタンス
        schedule_steps_json: スケジュールステップデータのJSON文字列
            例: '[{"key": "attendance", "order": 1, "scheduled_date": "2025-01-15", "completed": false}, ...]'

    Returns:
        int: 作成/更新されたステップ数
    """
    # プロジェクトが保存されていない場合はスキップ
    if not project.pk:
        print("⚠ Project must be saved before creating progress steps. Skipping...")
        return 0

    if not schedule_steps_json or schedule_steps_json.strip() == '':
        print("⚠ No schedule steps data provided")
        return 0

    try:
        # JSON をパース
        steps_data = json.loads(schedule_steps_json)

        if not isinstance(steps_data, list):
            print(f"⚠ Invalid steps data format: {type(steps_data)}")
            return 0

        # ステップテンプレートを確保
        templates = ensure_step_templates()

        # 既存のプロジェクトステップをすべて削除（上書き保存）
        # 新規プロジェクト（pk未設定）の場合はスキップ
        if project.pk:
            ProjectProgressStep.objects.filter(project=project).delete()

        # 新しいステップを作成
        created_count = 0
        for step_data in steps_data:
            key = step_data.get('key')
            order = step_data.get('order', 0)
            scheduled_date = step_data.get('scheduled_date')
            completed = step_data.get('completed', False)

            if not key or key not in templates:
                print(f"⚠ Unknown step key: {key}")
                continue

            template = templates[key]

            # 日付の値を準備
            value = {}
            if scheduled_date:
                value['scheduled_date'] = scheduled_date

            # 完了日時の設定
            completed_date = None
            if completed:
                # 既に完了している場合は現在時刻を設定
                completed_date = timezone.now()

            # ProjectProgressStep を作成
            ProjectProgressStep.objects.create(
                project=project,
                template=template,
                order=order,
                is_active=True,
                is_completed=completed,
                value=value,
                completed_date=completed_date
            )
            created_count += 1
            print(f"✓ ProjectProgressStep created: {template.name} (order: {order})")

        print(f"✓ Saved {created_count} progress steps for project {project.management_no}")
        return created_count

    except json.JSONDecodeError as e:
        print(f"❌ JSON decode error: {e}")
        return 0
    except Exception as e:
        print(f"❌ Error saving progress steps: {e}")
        import traceback
        traceback.print_exc()
        return 0


def load_project_progress_steps(project):
    """
    プロジェクトの進捗ステップを読み込み、フロントエンド用のJSON形式で返す。

    Args:
        project: Projectインスタンス

    Returns:
        str: JSON文字列
            例: '[{"key": "attendance", "order": 1, "scheduled_date": "2025-01-15", "completed": false}, ...]'
    """
    # ステップテンプレートのマッピングを逆引き用に作成
    template_to_key = {}
    for key, config in STEP_TEMPLATES.items():
        template_to_key[config['name']] = key

    # プロジェクトのステップを取得
    steps = ProjectProgressStep.objects.filter(
        project=project
    ).select_related('template').order_by('order')

    steps_data = []
    for step in steps:
        key = template_to_key.get(step.template.name)
        if not key:
            continue

        scheduled_date = ''
        if step.value and isinstance(step.value, dict):
            scheduled_date = step.value.get('scheduled_date', '')

        steps_data.append({
            'key': key,
            'order': step.order,
            'scheduled_date': scheduled_date,
            'completed': step.is_completed
        })

    return json.dumps(steps_data)


# ============================================================================
# High-Level API for Single Source of Truth (SSOT) Architecture
# ============================================================================

def get_step(project, step_key):
    """
    指定されたステップキーに対応するProjectProgressStepを取得

    Args:
        project: Projectインスタンス
        step_key: ステップキー（例: 'attendance', 'survey', 'estimate'）

    Returns:
        ProjectProgressStep or None
    """
    # プロジェクトが未保存の場合はNoneを返す
    if not project.pk:
        return None

    template_name = STEP_TEMPLATES.get(step_key, {}).get('name')
    if not template_name:
        return None

    return ProjectProgressStep.objects.filter(
        project=project,
        template__name=template_name,
        is_active=True
    ).first()


def get_step_scheduled_date(project, step_key):
    """
    ステップの予定日を取得

    Args:
        project: Projectインスタンス
        step_key: ステップキー（例: 'attendance', 'survey', 'estimate'）

    Returns:
        str: 日付文字列（'YYYY-MM-DD'形式）or None
    """
    step = get_step(project, step_key)
    if step and step.value and isinstance(step.value, dict):
        return step.value.get('scheduled_date')
    return None


def get_step_actual_date(project, step_key):
    """
    ステップの実施日を取得

    Args:
        project: Projectインスタンス
        step_key: ステップキー（例: 'attendance', 'survey', 'estimate'）

    Returns:
        str: 日付文字列（'YYYY-MM-DD'形式）or None
    """
    step = get_step(project, step_key)
    if step and step.value and isinstance(step.value, dict):
        return step.value.get('actual_date')
    return None


def set_step_scheduled_date(project, step_key, date_value):
    """
    ステップの予定日を設定

    Args:
        project: Projectインスタンス
        step_key: ステップキー（例: 'attendance', 'survey', 'estimate'）
        date_value: 日付文字列（'YYYY-MM-DD'形式）or None

    Returns:
        ProjectProgressStep
    """
    templates = ensure_step_templates()
    template = templates.get(step_key)

    if not template:
        raise ValueError(f"Unknown step key: {step_key}")

    step, created = ProjectProgressStep.objects.get_or_create(
        project=project,
        template=template,
        defaults={'order': template.order, 'value': {}, 'is_active': True}
    )

    if not step.value:
        step.value = {}

    if date_value:
        step.value['scheduled_date'] = date_value
    else:
        # 日付を削除
        step.value.pop('scheduled_date', None)

    step.save()
    return step


def set_step_actual_date(project, step_key, date_value):
    """
    ステップの実施日を設定

    Args:
        project: Projectインスタンス
        step_key: ステップキー（例: 'attendance', 'survey', 'estimate'）
        date_value: 日付文字列（'YYYY-MM-DD'形式）or None

    Returns:
        ProjectProgressStep
    """
    templates = ensure_step_templates()
    template = templates.get(step_key)

    if not template:
        raise ValueError(f"Unknown step key: {step_key}")

    step, created = ProjectProgressStep.objects.get_or_create(
        project=project,
        template=template,
        defaults={'order': template.order, 'value': {}, 'is_active': True}
    )

    if not step.value:
        step.value = {}

    if date_value:
        step.value['actual_date'] = date_value
    else:
        # 日付を削除
        step.value.pop('actual_date', None)

    step.save()
    return step


def get_step_assignees(project, step_key):
    """
    ステップの担当者リストを取得

    Args:
        project: Projectインスタンス
        step_key: ステップキー（例: 'attendance', 'survey', 'construction_start'）

    Returns:
        list: 担当者名のリスト
    """
    step = get_step(project, step_key)
    if step and step.value and isinstance(step.value, dict):
        assignees = step.value.get('assignees', [])
        return assignees if isinstance(assignees, list) else []
    return []


def set_step_assignees(project, step_key, assignees):
    """
    ステップの担当者リストを設定

    Args:
        project: Projectインスタンス
        step_key: ステップキー（例: 'attendance', 'survey', 'construction_start'）
        assignees: 担当者名のリスト

    Returns:
        ProjectProgressStep
    """
    templates = ensure_step_templates()
    template = templates.get(step_key)

    if not template:
        raise ValueError(f"Unknown step key: {step_key}")

    step, created = ProjectProgressStep.objects.get_or_create(
        project=project,
        template=template,
        defaults={'order': template.order, 'value': {}, 'is_active': True}
    )

    if not step.value:
        step.value = {}

    if assignees and isinstance(assignees, list):
        step.value['assignees'] = [a.strip() for a in assignees if a.strip()]
    else:
        # 空リストの場合は削除
        step.value.pop('assignees', None)

    step.save()
    return step


def complete_step(project, step_key, completed=True):
    """
    ステップを完了/未完了に設定

    Args:
        project: Projectインスタンス
        step_key: ステップキー（例: 'attendance', 'survey', 'estimate'）
        completed: 完了フラグ（True=完了、False=未完了）

    Returns:
        ProjectProgressStep
    """
    templates = ensure_step_templates()
    template = templates.get(step_key)

    if not template:
        raise ValueError(f"Unknown step key: {step_key}")

    step, created = ProjectProgressStep.objects.get_or_create(
        project=project,
        template=template,
        defaults={'order': template.order, 'value': {}, 'is_active': True}
    )

    step.is_completed = completed

    if completed:
        # 完了時は完了日時を設定
        if not step.completed_date:
            step.completed_date = timezone.now()
    else:
        # 未完了時は完了日時をクリア
        step.completed_date = None

    step.save()
    return step


def is_step_completed(project, step_key):
    """
    ステップが完了しているかチェック

    Args:
        project: Projectインスタンス
        step_key: ステップキー（例: 'attendance', 'survey', 'estimate'）

    Returns:
        bool: 完了していればTrue
    """
    step = get_step(project, step_key)
    return step.is_completed if step else False
