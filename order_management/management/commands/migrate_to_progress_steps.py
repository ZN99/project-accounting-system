"""
データ移行コマンド: 古いフィールドからProjectProgressStepへ

ProjectProgressStepを持たないプロジェクトに対して、
基本5ステップを作成し、古いフィールドからデータをコピーします。
"""
from django.core.management.base import BaseCommand
from django.db import transaction
from order_management.models import Project
from order_management.services.progress_step_service import (
    ensure_step_templates,
    set_step_scheduled_date,
    STEP_TEMPLATES
)


class Command(BaseCommand):
    help = '古いフィールドからProjectProgressStepへデータを移行'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='実際には変更せず、何が行われるかを表示'
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']

        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN モード: 実際の変更は行いません'))

        # テンプレートを確保
        templates = ensure_step_templates()
        self.stdout.write(self.style.SUCCESS(f'✓ {len(templates)} ステップテンプレートを確認'))

        # ProjectProgressStepを持たないプロジェクトを取得
        projects_without_steps = Project.objects.filter(progress_steps__isnull=True).distinct()
        total_count = projects_without_steps.count()

        if total_count == 0:
            self.stdout.write(self.style.SUCCESS('✓ すべてのプロジェクトが既にProjectProgressStepを持っています'))
            return

        self.stdout.write(self.style.WARNING(f'移行対象: {total_count} プロジェクト'))

        migrated_count = 0
        skipped_count = 0

        for project in projects_without_steps:
            self.stdout.write(f'\n処理中: {project.management_no} (ID: {project.pk})')

            # 古いフィールドにデータがあるか確認
            has_data = any([
                project.witness_date,
                project.survey_date,
                project.estimate_issued_date,
                project.work_start_date,
                project.work_end_date
            ])

            if not has_data:
                self.stdout.write(self.style.WARNING(f'  ⊘ データなし - デフォルトステップのみ作成'))

            if not dry_run:
                with transaction.atomic():
                    # 基本5ステップを作成
                    created_steps = []

                    # 立ち会い日 (attendance)
                    if project.witness_date:
                        set_step_scheduled_date(project, 'attendance', project.witness_date.strftime('%Y-%m-%d'))
                        created_steps.append(f'attendance: {project.witness_date}')

                    # 現調日 (survey)
                    if project.survey_date:
                        set_step_scheduled_date(project, 'survey', project.survey_date.strftime('%Y-%m-%d'))
                        created_steps.append(f'survey: {project.survey_date}')

                    # 見積書発行日 (estimate)
                    if project.estimate_issued_date:
                        set_step_scheduled_date(project, 'estimate', project.estimate_issued_date.strftime('%Y-%m-%d'))
                        created_steps.append(f'estimate: {project.estimate_issued_date}')

                    # 着工日 (construction_start)
                    if project.work_start_date:
                        set_step_scheduled_date(project, 'construction_start', project.work_start_date.strftime('%Y-%m-%d'))
                        created_steps.append(f'construction_start: {project.work_start_date}')

                    # 完工日 (completion)
                    if project.work_end_date:
                        set_step_scheduled_date(project, 'completion', project.work_end_date.strftime('%Y-%m-%d'))
                        created_steps.append(f'completion: {project.work_end_date}')

                    # データがない場合でも、基本ステップは ensure_step_templates で作成される
                    # （get_or_create により自動作成）

                    if created_steps:
                        self.stdout.write(self.style.SUCCESS(f'  ✓ 移行完了: {", ".join(created_steps)}'))
                        migrated_count += 1
                    else:
                        self.stdout.write(self.style.SUCCESS(f'  ✓ 基本ステップ作成完了'))
                        skipped_count += 1
            else:
                # DRY RUN: 何が行われるかを表示
                if project.witness_date:
                    self.stdout.write(f'  [DRY RUN] attendance: {project.witness_date}')
                if project.survey_date:
                    self.stdout.write(f'  [DRY RUN] survey: {project.survey_date}')
                if project.estimate_issued_date:
                    self.stdout.write(f'  [DRY RUN] estimate: {project.estimate_issued_date}')
                if project.work_start_date:
                    self.stdout.write(f'  [DRY RUN] construction_start: {project.work_start_date}')
                if project.work_end_date:
                    self.stdout.write(f'  [DRY RUN] completion: {project.work_end_date}')

        # サマリー表示
        self.stdout.write('\n' + '=' * 60)
        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN完了 - 実際の変更は行われていません'))
            self.stdout.write(self.style.WARNING(f'実行する場合は --dry-run フラグを外してください'))
        else:
            self.stdout.write(self.style.SUCCESS(f'✓ データ移行完了'))
            self.stdout.write(self.style.SUCCESS(f'  移行: {migrated_count} プロジェクト'))
            self.stdout.write(self.style.SUCCESS(f'  基本作成: {skipped_count} プロジェクト'))
        self.stdout.write('=' * 60)
