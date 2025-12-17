"""対応エリアフィールドを47都道府県に更新する管理コマンド"""
from django.core.management.base import BaseCommand
from subcontract_management.models import ContractorFieldCategory, ContractorFieldDefinition


# 47都道府県マスタ（地方ごとに整理）
PREFECTURES_47 = [
    # 北海道
    '北海道',
    # 東北
    '青森県', '岩手県', '宮城県', '秋田県', '山形県', '福島県',
    # 関東
    '茨城県', '栃木県', '群馬県', '埼玉県', '千葉県', '東京都', '神奈川県',
    # 中部
    '新潟県', '富山県', '石川県', '福井県', '山梨県', '長野県', '岐阜県', '静岡県', '愛知県',
    # 近畿
    '三重県', '滋賀県', '京都府', '大阪府', '兵庫県', '奈良県', '和歌山県',
    # 中国
    '鳥取県', '島根県', '岡山県', '広島県', '山口県',
    # 四国
    '徳島県', '香川県', '愛媛県', '高知県',
    # 九州・沖縄
    '福岡県', '佐賀県', '長崎県', '熊本県', '大分県', '宮崎県', '鹿児島県', '沖縄県'
]


class Command(BaseCommand):
    help = '対応エリアフィールドの選択肢を47都道府県に更新します'

    def add_arguments(self, parser):
        parser.add_argument(
            '--kanto-only',
            action='store_true',
            help='関東7都県のみに戻す',
        )

    def handle(self, *args, **options):
        if options['kanto_only']:
            # 関東7都県のみに戻す
            prefectures = ['茨城県', '栃木県', '群馬県', '埼玉県', '千葉県', '東京都', '神奈川県']
            self.stdout.write('関東7都県モード')
        else:
            # 47都道府県に更新
            prefectures = PREFECTURES_47
            self.stdout.write('47都道府県モード')

        self.stdout.write(f'選択肢数: {len(prefectures)}')

        # 対応可能エリアフィールドを更新
        try:
            service_areas_field = ContractorFieldDefinition.objects.get(slug='service_areas')
            service_areas_field.choices = prefectures
            service_areas_field.save()
            self.stdout.write(self.style.SUCCESS(f'✓ 「{service_areas_field.name}」を更新しました'))
        except ContractorFieldDefinition.DoesNotExist:
            self.stdout.write(self.style.ERROR('✗ 「対応可能エリア」フィールドが見つかりません'))

        # 出張費のかかるエリアフィールドを更新
        try:
            travel_expense_field = ContractorFieldDefinition.objects.get(slug='travel_expense_areas')
            travel_expense_field.choices = prefectures
            travel_expense_field.save()
            self.stdout.write(self.style.SUCCESS(f'✓ 「{travel_expense_field.name}」を更新しました'))
        except ContractorFieldDefinition.DoesNotExist:
            self.stdout.write(self.style.ERROR('✗ 「出張費のかかるエリア」フィールドが見つかりません'))

        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('✅ 更新完了'))
        self.stdout.write('')
        self.stdout.write('利用可能な都道府県:')
        for i, pref in enumerate(prefectures, 1):
            self.stdout.write(f'  {i:2d}. {pref}')
