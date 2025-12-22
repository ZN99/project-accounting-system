"""
Management command to recalculate profit for all existing projects.
"""
from django.core.management.base import BaseCommand
from django.db import transaction
from order_management.models import Project


class Command(BaseCommand):
    help = 'Recalculate gross_profit and profit_margin for all projects'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Run without actually updating the database',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']

        if dry_run:
            self.stdout.write(self.style.WARNING('🔍 DRY RUN MODE - No changes will be saved'))

        projects = Project.objects.all().order_by('id')
        total = projects.count()

        self.stdout.write(f'Found {total} projects to process')

        success_count = 0
        error_count = 0

        with transaction.atomic():
            for idx, project in enumerate(projects, 1):
                try:
                    # 利益を計算
                    project._update_profit_cache()

                    if not dry_run:
                        # update()を使ってsave()シグナルを回避
                        Project.objects.filter(pk=project.pk).update(
                            gross_profit=project.gross_profit,
                            profit_margin=project.profit_margin
                        )

                    success_count += 1

                    # 進捗表示（10%ごと）
                    if idx % max(1, total // 10) == 0 or idx == total:
                        progress = int((idx / total) * 100)
                        self.stdout.write(
                            f'  Progress: {progress}% ({idx}/{total}) - '
                            f'Last: {project.management_no} '
                            f'(profit: ¥{project.gross_profit:,.0f}, margin: {project.profit_margin:.1f}%)'
                        )

                except Exception as e:
                    error_count += 1
                    self.stdout.write(
                        self.style.ERROR(
                            f'  ❌ Error processing project {project.management_no}: {e}'
                        )
                    )

            if dry_run:
                # ロールバック
                transaction.set_rollback(True)
                self.stdout.write(self.style.WARNING('\n🔄 Rolling back (dry run)'))

        # 結果サマリー
        self.stdout.write('\n' + '='*50)
        self.stdout.write(self.style.SUCCESS(f'✅ Successfully processed: {success_count}'))
        if error_count > 0:
            self.stdout.write(self.style.ERROR(f'❌ Errors: {error_count}'))

        if dry_run:
            self.stdout.write(self.style.WARNING('\n⚠️  This was a DRY RUN - no changes were saved'))
            self.stdout.write('    Run without --dry-run to apply changes')
        else:
            self.stdout.write(self.style.SUCCESS('\n✨ All changes have been saved'))
