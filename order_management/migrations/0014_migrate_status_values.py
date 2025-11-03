# Data migration for Phase 0: ステータス値の変換

from django.db import migrations


def migrate_status_values(apps, schema_editor):
    """既存のステータス値を新しい値に変換"""
    Project = apps.get_model('order_management', 'Project')

    # ステータス値のマッピング
    status_mapping = {
        '検討中': 'ネタ',
        'A': '施工日待ち',
        '受注': '完工',
        'NG': 'NG',  # 変更なし
    }

    # 全プロジェクトを走査して変換
    for project in Project.objects.all():
        old_status = project.project_status
        if old_status in status_mapping:
            new_status = status_mapping[old_status]
            if new_status != old_status:
                project.project_status = new_status
                project.save(update_fields=['project_status'])
                print(f"Project {project.management_no}: {old_status} → {new_status}")


def reverse_migrate_status_values(apps, schema_editor):
    """ロールバック時に元のステータス値に戻す"""
    Project = apps.get_model('order_management', 'Project')

    # 逆マッピング
    reverse_status_mapping = {
        'ネタ': '検討中',
        '施工日待ち': 'A',
        '完工': '受注',
        'NG': 'NG',
        '進行中': 'A',  # 進行中が追加されている場合はAに戻す
    }

    for project in Project.objects.all():
        new_status = project.project_status
        if new_status in reverse_status_mapping:
            old_status = reverse_status_mapping[new_status]
            if old_status != new_status:
                project.project_status = old_status
                project.save(update_fields=['project_status'])
                print(f"Project {project.management_no}: {new_status} → {old_status}")


class Migration(migrations.Migration):

    dependencies = [
        ('order_management', '0013_rename_project_fields'),
    ]

    operations = [
        migrations.RunPython(
            migrate_status_values,
            reverse_code=reverse_migrate_status_values
        ),
    ]
