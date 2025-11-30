"""
既存プロジェクトの工期データを動的ステップに同期する管理コマンド
"""
from django.core.management.base import BaseCommand
from order_management.models import Project


class Command(BaseCommand):
    help = '既存プロジェクトのwork_start_date/work_end_dateを動的ステップに同期'

    def handle(self, *args, **options):
        projects = Project.objects.all()
        synced_count = 0

        for project in projects:
            updated = False

            # additional_itemsが存在しない場合は初期化
            if not project.additional_items:
                project.additional_items = {}

            # complex_step_fieldsが存在しない場合は初期化
            if 'complex_step_fields' not in project.additional_items:
                project.additional_items['complex_step_fields'] = {}

            complex_fields = project.additional_items['complex_step_fields']

            # work_start_dateを construction_start_scheduled_date に同期
            if project.work_start_date and not complex_fields.get('construction_start_scheduled_date'):
                complex_fields['construction_start_scheduled_date'] = project.work_start_date.isoformat()
                updated = True
                self.stdout.write(f'  {project.site_name}: 着工日を同期 ({project.work_start_date})')

            # work_end_dateを completion_scheduled_date に同期
            if project.work_end_date and not complex_fields.get('completion_scheduled_date'):
                complex_fields['completion_scheduled_date'] = project.work_end_date.isoformat()
                updated = True
                self.stdout.write(f'  {project.site_name}: 完工日を同期 ({project.work_end_date})')

            # construction_start_completedを work_start_completed に同期（動的→静的）
            if 'construction_start_completed' in complex_fields:
                value = complex_fields['construction_start_completed']
                if value in ['on', 'true', True]:
                    project.work_start_completed = True
                    updated = True
                    self.stdout.write(f'  {project.site_name}: 着工完了フラグを同期')

            # completion_completedを work_end_completed に同期（動的→静的）
            if 'completion_completed' in complex_fields:
                value = complex_fields['completion_completed']
                if value in ['on', 'true', True]:
                    project.work_end_completed = True
                    updated = True
                    self.stdout.write(f'  {project.site_name}: 完工済みフラグを同期')

            if updated:
                project.save()
                synced_count += 1

        self.stdout.write(self.style.SUCCESS(f'\n完了: {synced_count}件のプロジェクトを同期しました'))
