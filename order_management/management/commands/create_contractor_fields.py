"""業者カスタムフィールドの初期データを作成する管理コマンド"""
from django.core.management.base import BaseCommand
from subcontract_management.models import ContractorFieldCategory, ContractorFieldDefinition


class Command(BaseCommand):
    help = '業者カスタムフィールドのカテゴリとフィールド定義を作成します'

    def handle(self, *args, **options):
        self.stdout.write('業者カスタムフィールドを作成中...')

        # 既存のカテゴリとフィールドを削除（オプション）
        # ContractorFieldDefinition.objects.all().delete()
        # ContractorFieldCategory.objects.all().delete()

        # カテゴリ1: 基本情報
        basic_info, _ = ContractorFieldCategory.objects.get_or_create(
            slug='basic_info',
            defaults={
                'name': '基本情報',
                'description': '業者の基本的な情報',
                'order': 1
            }
        )
        self.create_fields(basic_info, [
            ('スケジュール確認の速さ', 'schedule_response_speed', 'select', {
                'choices': ['1. 当日中', '2. 翌日まで', '3. 3〜4日後', '4. 1週間以内', '5. 確認遅い'],
                'help_text': 'スケジュール確認の対応速度を選択'
            }),
            ('業者の人数', 'number_of_workers', 'number', {
                'help_text': '業者の人数を入力',
                'min_value': 1
            }),
            ('1日あたりの可能施工数', 'daily_construction_capacity', 'number', {
                'help_text': '1日あたりに可能な施工数',
                'min_value': 1
            }),
            ('年齢', 'age_range', 'select', {
                'choices': ['10代後半', '20代前半', '20代後半', '30代前半', '30代後半',
                           '40代前半', '40代後半', '50代前半', '50代後半', '60歳以降'],
                'help_text': '業者の年齢層を選択'
            }),
            ('インボイス登録番号', 'invoice_number', 'text', {
                'help_text': 'T####-####-####形式で入力（ハイフンは自動で挿入されます）',
                'placeholder': 'T1234-5678-9012'
            }),
        ])

        # カテゴリ2: 対応エリア
        service_areas, _ = ContractorFieldCategory.objects.get_or_create(
            slug='service_areas',
            defaults={
                'name': '対応エリア',
                'description': '対応可能なエリアと出張費のかかるエリア',
                'order': 2
            }
        )
        self.create_fields(service_areas, [
            ('対応可能エリア - 栃木県', 'service_area_tochigi', 'checkbox', {}),
            ('対応可能エリア - 群馬県', 'service_area_gunma', 'checkbox', {}),
            ('対応可能エリア - 茨城県', 'service_area_ibaraki', 'checkbox', {}),
            ('出張費のかかるエリア - 栃木県', 'travel_expense_tochigi', 'checkbox', {}),
            ('出張費のかかるエリア - 群馬県', 'travel_expense_gunma', 'checkbox', {}),
            ('出張費のかかるエリア - 茨城県', 'travel_expense_ibaraki', 'checkbox', {}),
        ])

        # カテゴリ3: 問屋契約
        wholesale, _ = ContractorFieldCategory.objects.get_or_create(
            slug='wholesale_contract',
            defaults={
                'name': '問屋契約',
                'description': '問屋契約の有無と詳細',
                'order': 3
            }
        )
        self.create_fields(wholesale, [
            ('問屋契約の可否', 'has_wholesale_contract', 'select', {
                'choices': ['あり', 'なし'],
                'help_text': '問屋契約があるか選択'
            }),
            ('問屋契約詳細', 'wholesale_contract_details', 'textarea', {
                'help_text': '問屋契約の詳細を箇条書きで入力（問屋契約ありの場合）',
                'placeholder': '例：\n- ○○問屋と契約\n- 割引率10%'
            }),
        ])

        # カテゴリ4: クロス工事
        wallpaper, _ = ContractorFieldCategory.objects.get_or_create(
            slug='wallpaper',
            defaults={
                'name': 'クロス工事',
                'description': 'クロス関連の施工費用',
                'order': 4
            }
        )
        self.create_fields(wallpaper, [
            ('クロス張り手間 (¥)', 'wallpaper_labor_cost', 'number', {
                'help_text': 'クロス張りの手間代',
                'placeholder': '例: 15000',
                'min_value': 0
            }),
            ('クロス材工 (¥)', 'wallpaper_material_labor_cost', 'number', {
                'help_text': 'クロス材工の費用',
                'placeholder': '例: 25000',
                'min_value': 0
            }),
            ('クロスアクセント手間 (¥)', 'wallpaper_accent_labor_cost', 'number', {
                'help_text': 'クロスアクセントの手間代',
                'placeholder': '例: 18000',
                'min_value': 0
            }),
            ('クロスアクセント材工 (¥)', 'wallpaper_accent_material_labor_cost', 'number', {
                'help_text': 'クロスアクセント材工の費用',
                'placeholder': '例: 28000',
                'min_value': 0
            }),
        ])

        # カテゴリ5: 床工事
        flooring, _ = ContractorFieldCategory.objects.get_or_create(
            slug='flooring',
            defaults={
                'name': '床工事',
                'description': 'CF・FT関連の施工費用',
                'order': 5
            }
        )
        self.create_fields(flooring, [
            ('CF張り手間 (¥)', 'cf_labor_cost', 'number', {
                'help_text': 'CF張りの手間代',
                'placeholder': '例: 12000',
                'min_value': 0
            }),
            ('CF材工 (¥)', 'cf_material_labor_cost', 'number', {
                'help_text': 'CF材工の費用',
                'placeholder': '例: 22000',
                'min_value': 0
            }),
            ('FT手間 (¥)', 'ft_labor_cost', 'number', {
                'help_text': 'FTの手間代',
                'placeholder': '例: 15000',
                'min_value': 0
            }),
            ('FT材工 (¥)', 'ft_material_labor_cost', 'number', {
                'help_text': 'FT材工の費用',
                'placeholder': '例: 25000',
                'min_value': 0
            }),
        ])

        # カテゴリ6: ハウスクリーニング
        cleaning, _ = ContractorFieldCategory.objects.get_or_create(
            slug='house_cleaning',
            defaults={
                'name': 'ハウスクリーニング',
                'description': '部屋タイプ別のクリーニング費用',
                'order': 6
            }
        )
        self.create_fields(cleaning, [
            ('1R (¥)', 'cleaning_1r_cost', 'number', {
                'help_text': '1Rのクリーニング費用',
                'placeholder': '例: 20000',
                'min_value': 0
            }),
            ('1K (¥)', 'cleaning_1k_cost', 'number', {
                'help_text': '1Kのクリーニング費用',
                'placeholder': '例: 22000',
                'min_value': 0
            }),
            ('1DK (¥)', 'cleaning_1dk_cost', 'number', {
                'help_text': '1DKのクリーニング費用',
                'placeholder': '例: 25000',
                'min_value': 0
            }),
            ('1LDK (¥)', 'cleaning_1ldk_cost', 'number', {
                'help_text': '1LDKのクリーニング費用',
                'placeholder': '例: 30000',
                'min_value': 0
            }),
            ('2DK (¥)', 'cleaning_2dk_cost', 'number', {
                'help_text': '2DKのクリーニング費用',
                'placeholder': '例: 35000',
                'min_value': 0
            }),
            ('2LDK (¥)', 'cleaning_2ldk_cost', 'number', {
                'help_text': '2LDKのクリーニング費用',
                'placeholder': '例: 40000',
                'min_value': 0
            }),
            ('3LDK (¥)', 'cleaning_3ldk_cost', 'number', {
                'help_text': '3LDKのクリーニング費用',
                'placeholder': '例: 50000',
                'min_value': 0
            }),
            ('在宅対応可能', 'occupied_cleaning_available', 'checkbox', {
                'help_text': '在宅でのクリーニングに対応可能'
            }),
        ])

        # カテゴリ7: エアコン
        ac, _ = ContractorFieldCategory.objects.get_or_create(
            slug='air_conditioning',
            defaults={
                'name': 'エアコン',
                'description': 'エアコンタイプ別の施工費用',
                'order': 7
            }
        )
        self.create_fields(ac, [
            ('壁掛けエアコン (¥)', 'ac_wall_mounted_cost', 'number', {
                'help_text': '壁掛けエアコンの施工費用',
                'placeholder': '例: 15000',
                'min_value': 0
            }),
            ('お掃除付きエアコン (¥)', 'ac_self_cleaning_cost', 'number', {
                'help_text': 'お掃除付きエアコンの施工費用',
                'placeholder': '例: 20000',
                'min_value': 0
            }),
            ('天井カセットエアコン (¥)', 'ac_ceiling_cassette_cost', 'number', {
                'help_text': '天井カセットエアコンの施工費用',
                'placeholder': '例: 30000',
                'min_value': 0
            }),
        ])

        # カテゴリ8: リペア
        repair, _ = ContractorFieldCategory.objects.get_or_create(
            slug='repair',
            defaults={
                'name': 'リペア',
                'description': '対応可能なリペア項目',
                'order': 8
            }
        )
        self.create_fields(repair, [
            ('フローリング', 'repair_flooring', 'checkbox', {}),
            ('ドア枠塗装', 'repair_door_frame_painting', 'checkbox', {}),
            ('金属部分塗装', 'repair_metal_painting', 'checkbox', {}),
            ('陶器（洗面器）', 'repair_sink', 'checkbox', {}),
            ('陶器（トイレ）', 'repair_toilet', 'checkbox', {}),
            ('キッチン扉のシート', 'repair_kitchen_sheet', 'checkbox', {
                'help_text': '表層のダイノック張替え'
            }),
            ('扉', 'repair_door', 'checkbox', {}),
        ])

        # カテゴリ9: 水道
        plumbing, _ = ContractorFieldCategory.objects.get_or_create(
            slug='plumbing',
            defaults={
                'name': '水道',
                'description': '水道関連の施工費用',
                'order': 9
            }
        )
        self.create_fields(plumbing, [
            ('つまり (¥)', 'plumbing_clog_cost', 'number', {
                'help_text': 'つまり修理の費用',
                'placeholder': '例: 10000',
                'min_value': 0
            }),
            ('漏水 (¥)', 'plumbing_leak_cost', 'number', {
                'help_text': '漏水修理の費用',
                'placeholder': '例: 15000',
                'min_value': 0
            }),
            ('配管 (¥)', 'plumbing_piping_cost', 'number', {
                'help_text': '配管工事の費用',
                'placeholder': '例: 20000',
                'min_value': 0
            }),
            ('夜間対応 (¥)', 'plumbing_night_service_cost', 'number', {
                'help_text': '夜間対応の追加費用',
                'placeholder': '例: 5000',
                'min_value': 0
            }),
        ])

        # カテゴリ10: 電気
        electrical, _ = ContractorFieldCategory.objects.get_or_create(
            slug='electrical',
            defaults={
                'name': '電気',
                'description': '対応可能な電気工事',
                'order': 10
            }
        )
        self.create_fields(electrical, [
            ('配線', 'electrical_wiring', 'checkbox', {}),
            ('蛍光灯やシーリングライトのひっかけから設置', 'electrical_light_installation', 'checkbox', {}),
            ('コンセントの増設・交換', 'electrical_outlet_work', 'checkbox', {}),
            ('ブレーカー盤の交換', 'electrical_breaker_replacement', 'checkbox', {}),
            ('AOタップの増設・移動・交換', 'electrical_ao_tap_work', 'checkbox', {}),
        ])

        # カテゴリ11: 設備
        equipment, _ = ContractorFieldCategory.objects.get_or_create(
            slug='equipment',
            defaults={
                'name': '設備',
                'description': '対応可能な設備',
                'order': 11
            }
        )
        self.create_fields(equipment, [
            ('対応可能設備', 'available_equipment', 'textarea', {
                'help_text': '対応可能な設備を箇条書きで入力してください',
                'placeholder': '例：\n- 給湯器\n- エアコン\n- 換気扇'
            }),
        ])

        # カテゴリ12: 塗装
        painting, _ = ContractorFieldCategory.objects.get_or_create(
            slug='painting',
            defaults={
                'name': '塗装',
                'description': '塗装関連の施工費用',
                'order': 12
            }
        )
        self.create_fields(painting, [
            ('塗装（外構）金額 (¥)', 'exterior_painting_cost', 'number', {
                'help_text': '外構塗装の費用',
                'placeholder': '例: 100000',
                'min_value': 0
            }),
            ('足場契約あり', 'scaffolding_contract', 'checkbox', {
                'help_text': '足場契約がある場合はチェック'
            }),
            ('家まるごと金額 (¥)', 'scaffolding_whole_house_cost', 'number', {
                'help_text': '足場契約がある場合の家まるごとの金額',
                'placeholder': '例: 500000',
                'min_value': 0
            }),
        ])

        # カテゴリ13: 大工
        carpentry, _ = ContractorFieldCategory.objects.get_or_create(
            slug='carpentry',
            defaults={
                'name': '大工',
                'description': '大工関連の情報',
                'order': 13
            }
        )
        self.create_fields(carpentry, [
            ('対応可能工事タイプ', 'carpentry_type', 'select', {
                'choices': ['新築のみ', 'リノベもできる'],
                'help_text': '対応可能な工事タイプを選択'
            }),
            ('大工備考', 'carpentry_notes', 'textarea', {
                'help_text': '大工関連の備考を入力',
                'placeholder': '例：木造専門、リフォーム経験豊富'
            }),
        ])

        # カテゴリ14: その他の情報
        other_info, _ = ContractorFieldCategory.objects.get_or_create(
            slug='other_info',
            defaults={
                'name': 'その他の情報',
                'description': '業者の特性や注意事項',
                'order': 14
            }
        )
        self.create_fields(other_info, [
            ('時間厳守レベル', 'time_punctuality', 'select', {
                'choices': ['1. 完工までは必ず守ってくれる', '2. 着工の時間を守れる', '3. 守れない'],
                'help_text': '時間厳守のレベルを選択'
            }),
            ('在宅空室可否', 'occupancy_preference', 'multiselect', {
                'choices': ['空室（元請・お客さんと触れない）', '在宅（元請・お客さんと会ってもOK）'],
                'help_text': '対応可能な状況を選択（複数選択可）'
            }),
            ('性格の備考', 'personality_notes', 'textarea', {
                'help_text': '業者の性格や特徴について',
                'placeholder': '例：丁寧、几帳面、コミュニケーション良好'
            }),
            ('注意事項', 'precautions', 'textarea', {
                'help_text': '業者に関する注意事項',
                'placeholder': '例：事前連絡必須、午前中のみ対応可能'
            }),
        ])

        self.stdout.write(self.style.SUCCESS('✅ 業者カスタムフィールドの作成が完了しました'))

    def create_fields(self, category, fields_data):
        """フィールド定義を一括作成"""
        for order, (name, slug, field_type, extra) in enumerate(fields_data, start=1):
            field, created = ContractorFieldDefinition.objects.get_or_create(
                category=category,
                slug=slug,
                defaults={
                    'name': name,
                    'field_type': field_type,
                    'order': order,
                    'is_active': True,
                    **extra
                }
            )
            if created:
                self.stdout.write(f'  ✓ {category.name} - {name}')
            else:
                self.stdout.write(f'  → {category.name} - {name} (既存)')
