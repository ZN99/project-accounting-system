"""業者カスタムフィールドの初期データを作成する管理コマンド

このファイルは、業者カスタムフィールドの標準構成を定義しています。
現在の構成: 15カテゴリ、72フィールド（47都道府県対応）
"""
from django.core.management.base import BaseCommand
from subcontract_management.models import ContractorFieldCategory, ContractorFieldDefinition


# 47都道府県の定数
ALL_PREFECTURES = [
    '北海道',
    '青森県', '岩手県', '宮城県', '秋田県', '山形県', '福島県',
    '茨城県', '栃木県', '群馬県', '埼玉県', '千葉県', '東京都', '神奈川県',
    '新潟県', '富山県', '石川県', '福井県', '山梨県', '長野県', '岐阜県', '静岡県', '愛知県',
    '三重県', '滋賀県', '京都府', '大阪府', '兵庫県', '奈良県', '和歌山県',
    '鳥取県', '島根県', '岡山県', '広島県', '山口県',
    '徳島県', '香川県', '愛媛県', '高知県',
    '福岡県', '佐賀県', '長崎県', '熊本県', '大分県', '宮崎県', '鹿児島県', '沖縄県'
]


class Command(BaseCommand):
    help = '業者カスタムフィールドのカテゴリとフィールド定義を作成します（標準構成: 15カテゴリ、72フィールド）'

    def add_arguments(self, parser):
        parser.add_argument(
            '--reset',
            action='store_true',
            help='既存のカテゴリとフィールドを削除してから作成',
        )

    def handle(self, *args, **options):
        self.stdout.write('業者カスタムフィールドを作成中...')

        # リセットオプションが指定された場合は既存データを削除
        if options['reset']:
            self.stdout.write(self.style.WARNING('既存のデータを削除中...'))
            ContractorFieldDefinition.objects.all().delete()
            ContractorFieldCategory.objects.all().delete()
            self.stdout.write(self.style.WARNING('削除完了'))

        # カテゴリとフィールドの作成
        self.create_basic_info_category()
        self.create_wholesale_contract_category()
        self.create_wallpaper_category()
        self.create_flooring_category()
        self.create_house_cleaning_category()
        self.create_air_conditioning_category()
        self.create_repair_category()
        self.create_plumbing_category()
        self.create_electrical_category()
        self.create_equipment_category()
        self.create_painting_category()
        self.create_carpentry_category()
        self.create_supported_services_category()
        self.create_work_style_category()
        self.create_other_info_category()

        self.stdout.write(self.style.SUCCESS('\n✅ 業者カスタムフィールドの作成が完了しました'))
        self.stdout.write(self.style.SUCCESS(f'   カテゴリ数: {ContractorFieldCategory.objects.count()}'))
        self.stdout.write(self.style.SUCCESS(f'   フィールド数: {ContractorFieldDefinition.objects.count()}'))

    def create_field(self, category, name, slug, field_type, order, **kwargs):
        """フィールド定義を作成するヘルパーメソッド"""
        field, created = ContractorFieldDefinition.objects.get_or_create(
            category=category,
            slug=slug,
            defaults={
                'name': name,
                'field_type': field_type,
                'order': order,
                'is_active': True,
                'is_required': kwargs.get('is_required', False),
                'placeholder': kwargs.get('placeholder', ''),
                'help_text': kwargs.get('help_text', ''),
                'choices': kwargs.get('choices', []),
                'min_value': kwargs.get('min_value'),
                'max_value': kwargs.get('max_value'),
            }
        )
        status = '✓' if created else '→'
        self.stdout.write(f'  {status} {category.name} - {name}')
        return field

    def create_basic_info_category(self):
        """カテゴリ0: 基本情報"""
        category, _ = ContractorFieldCategory.objects.get_or_create(
            slug='basic_info',
            defaults={
                'name': '基本情報',
                'description': '',
                'order': 0
            }
        )

        self.create_field(
            category, 'スケジュール確認の速さ', 'schedule_response_speed', 'select', 1,
            help_text='スケジュール確認の対応速度を選択',
            choices=['1. 当日中', '2. 翌日まで', '3. 3〜4日後', '4. 1週間以内', '5. 確認遅い']
        )

        self.create_field(
            category, '業者の人数', 'number_of_workers', 'number', 2,
            help_text='業者の人数を入力',
            min_value=1
        )

        self.create_field(
            category, '年齢', 'age_range', 'select', 4,
            help_text='業者の年齢層を選択',
            choices=['10代後半', '20代前半', '20代後半', '30代前半', '30代後半',
                    '40代前半', '40代後半', '50代前半', '50代後半', '60歳以降']
        )

        self.create_field(
            category, 'インボイス登録番号', 'invoice_number', 'text', 5,
            placeholder='T1234-5678-9012',
            help_text='T####-####-####形式で入力（ハイフンは自動で挿入されます）'
        )

        self.create_field(
            category, '対応可能エリア', 'service_areas', 'multiselect', 6,
            help_text='対応可能なエリアを選択してください（複数選択可）',
            choices=ALL_PREFECTURES
        )

        self.create_field(
            category, '出張費のかかるエリア', 'travel_expense_areas', 'multiselect', 7,
            help_text='出張費が発生するエリアを選択してください（複数選択可）',
            choices=ALL_PREFECTURES
        )

    def create_wholesale_contract_category(self):
        """カテゴリ1: 問屋契約"""
        category, _ = ContractorFieldCategory.objects.get_or_create(
            slug='wholesale_contract',
            defaults={
                'name': '問屋契約',
                'description': '問屋契約の有無と詳細',
                'order': 1
            }
        )

        self.create_field(
            category, '問屋契約の可否', 'has_wholesale_contract', 'select', 1,
            help_text='問屋契約があるか選択',
            choices=['あり', 'なし']
        )

        self.create_field(
            category, '問屋契約詳細', 'wholesale_contract_details', 'textarea', 2,
            placeholder='例：\n- ○○問屋と契約\n- 割引率10%',
            help_text='問屋契約の詳細を箇条書きで入力（問屋契約ありの場合）'
        )

    def create_wallpaper_category(self):
        """カテゴリ2: クロス工事"""
        category, _ = ContractorFieldCategory.objects.get_or_create(
            slug='wallpaper',
            defaults={
                'name': 'クロス工事',
                'description': 'クロス関連の施工費用',
                'order': 2
            }
        )

        self.create_field(
            category, 'クロス張り手間 (¥)', 'wallpaper_labor_cost', 'number', 1,
            placeholder='例: 15000',
            help_text='クロス張りの手間代',
            min_value=0
        )

        self.create_field(
            category, 'クロス材工 (¥)', 'wallpaper_material_labor_cost', 'number', 2,
            placeholder='例: 25000',
            help_text='クロス材工の費用',
            min_value=0
        )

        self.create_field(
            category, 'クロスアクセント手間 (¥)', 'wallpaper_accent_labor_cost', 'number', 3,
            placeholder='例: 18000',
            help_text='クロスアクセントの手間代',
            min_value=0
        )

        self.create_field(
            category, 'クロスアクセント材工 (¥)', 'wallpaper_accent_material_labor_cost', 'number', 4,
            placeholder='例: 28000',
            help_text='クロスアクセント材工の費用',
            min_value=0
        )

    def create_flooring_category(self):
        """カテゴリ3: 床工事"""
        category, _ = ContractorFieldCategory.objects.get_or_create(
            slug='flooring',
            defaults={
                'name': '床工事',
                'description': 'CF・FT関連の施工費用',
                'order': 3
            }
        )

        self.create_field(
            category, 'CF張り手間 (¥)', 'cf_labor_cost', 'number', 1,
            placeholder='例: 12000',
            help_text='CF張りの手間代',
            min_value=0
        )

        self.create_field(
            category, 'CF材工 (¥)', 'cf_material_labor_cost', 'number', 2,
            placeholder='例: 22000',
            help_text='CF材工の費用',
            min_value=0
        )

        self.create_field(
            category, 'FT手間 (¥)', 'ft_labor_cost', 'number', 3,
            placeholder='例: 15000',
            help_text='FTの手間代',
            min_value=0
        )

        self.create_field(
            category, 'FT材工 (¥)', 'ft_material_labor_cost', 'number', 4,
            placeholder='例: 25000',
            help_text='FT材工の費用',
            min_value=0
        )

    def create_house_cleaning_category(self):
        """カテゴリ4: ハウスクリーニング"""
        category, _ = ContractorFieldCategory.objects.get_or_create(
            slug='house_cleaning',
            defaults={
                'name': 'ハウスクリーニング',
                'description': '部屋タイプ別のクリーニング費用',
                'order': 4
            }
        )

        self.create_field(
            category, '1R (¥)', 'cleaning_1r_cost', 'number', 1,
            placeholder='例: 20000',
            help_text='1Rのクリーニング費用',
            min_value=0
        )

        self.create_field(
            category, '1K (¥)', 'cleaning_1k_cost', 'number', 2,
            placeholder='例: 22000',
            help_text='1Kのクリーニング費用',
            min_value=0
        )

        self.create_field(
            category, '1DK (¥)', 'cleaning_1dk_cost', 'number', 3,
            placeholder='例: 25000',
            help_text='1DKのクリーニング費用',
            min_value=0
        )

        self.create_field(
            category, '1LDK (¥)', 'cleaning_1ldk_cost', 'number', 4,
            placeholder='例: 30000',
            help_text='1LDKのクリーニング費用',
            min_value=0
        )

        self.create_field(
            category, '2DK (¥)', 'cleaning_2dk_cost', 'number', 5,
            placeholder='例: 35000',
            help_text='2DKのクリーニング費用',
            min_value=0
        )

        self.create_field(
            category, '2LDK (¥)', 'cleaning_2ldk_cost', 'number', 6,
            placeholder='例: 40000',
            help_text='2LDKのクリーニング費用',
            min_value=0
        )

        self.create_field(
            category, '3LDK (¥)', 'cleaning_3ldk_cost', 'number', 7,
            placeholder='例: 50000',
            help_text='3LDKのクリーニング費用',
            min_value=0
        )

        self.create_field(
            category, '在宅対応可能', 'occupied_cleaning_available', 'checkbox', 8,
            help_text='在宅でのクリーニングに対応可能'
        )

    def create_air_conditioning_category(self):
        """カテゴリ5: エアコン"""
        category, _ = ContractorFieldCategory.objects.get_or_create(
            slug='air_conditioning',
            defaults={
                'name': 'エアコン',
                'description': 'エアコンタイプ別の施工費用',
                'order': 5
            }
        )

        self.create_field(
            category, '壁掛けエアコン (¥)', 'ac_wall_mounted_cost', 'number', 1,
            placeholder='例: 15000',
            help_text='壁掛けエアコンの施工費用',
            min_value=0
        )

        self.create_field(
            category, 'お掃除付きエアコン (¥)', 'ac_self_cleaning_cost', 'number', 2,
            placeholder='例: 20000',
            help_text='お掃除付きエアコンの施工費用',
            min_value=0
        )

        self.create_field(
            category, '天井カセットエアコン (¥)', 'ac_ceiling_cassette_cost', 'number', 3,
            placeholder='例: 30000',
            help_text='天井カセットエアコンの施工費用',
            min_value=0
        )

    def create_repair_category(self):
        """カテゴリ6: リペア"""
        category, _ = ContractorFieldCategory.objects.get_or_create(
            slug='repair',
            defaults={
                'name': 'リペア',
                'description': '対応可能なリペア項目',
                'order': 6
            }
        )

        self.create_field(category, 'フローリング', 'repair_flooring', 'checkbox', 1)
        self.create_field(category, 'ドア枠塗装', 'repair_door_frame_painting', 'checkbox', 2)
        self.create_field(category, '金属部分塗装', 'repair_metal_painting', 'checkbox', 3)
        self.create_field(category, '陶器（洗面器）', 'repair_sink', 'checkbox', 4)
        self.create_field(category, '陶器（トイレ）', 'repair_toilet', 'checkbox', 5)
        self.create_field(
            category, 'キッチン扉のシート', 'repair_kitchen_sheet', 'checkbox', 6,
            help_text='表層のダイノック張替え'
        )
        self.create_field(category, '扉', 'repair_door', 'checkbox', 7)

    def create_plumbing_category(self):
        """カテゴリ7: 水道"""
        category, _ = ContractorFieldCategory.objects.get_or_create(
            slug='plumbing',
            defaults={
                'name': '水道',
                'description': '水道関連の施工費用',
                'order': 7
            }
        )

        self.create_field(
            category, 'つまり (¥)', 'plumbing_clog_cost', 'number', 1,
            placeholder='例: 10000',
            help_text='つまり修理の費用',
            min_value=0
        )

        self.create_field(
            category, '漏水 (¥)', 'plumbing_leak_cost', 'number', 2,
            placeholder='例: 15000',
            help_text='漏水修理の費用',
            min_value=0
        )

        self.create_field(
            category, '配管 (¥)', 'plumbing_piping_cost', 'number', 3,
            placeholder='例: 20000',
            help_text='配管工事の費用',
            min_value=0
        )

        self.create_field(
            category, '夜間対応 (¥)', 'plumbing_night_service_cost', 'number', 4,
            placeholder='例: 5000',
            help_text='夜間対応の追加費用',
            min_value=0
        )

    def create_electrical_category(self):
        """カテゴリ8: 電気"""
        category, _ = ContractorFieldCategory.objects.get_or_create(
            slug='electrical',
            defaults={
                'name': '電気',
                'description': '対応可能な電気工事',
                'order': 8
            }
        )

        self.create_field(category, '配線', 'electrical_wiring', 'checkbox', 1)
        self.create_field(
            category, '蛍光灯やシーリングライトのひっかけから設置',
            'electrical_light_installation', 'checkbox', 2
        )
        self.create_field(
            category, 'コンセントの増設・交換',
            'electrical_outlet_work', 'checkbox', 3
        )
        self.create_field(
            category, 'ブレーカー盤の交換',
            'electrical_breaker_replacement', 'checkbox', 4
        )
        self.create_field(
            category, 'AOタップの増設・移動・交換',
            'electrical_ao_tap_work', 'checkbox', 5
        )

    def create_equipment_category(self):
        """カテゴリ9: 設備"""
        category, _ = ContractorFieldCategory.objects.get_or_create(
            slug='equipment',
            defaults={
                'name': '設備',
                'description': '対応可能な設備',
                'order': 9
            }
        )

        self.create_field(
            category, '対応可能設備', 'available_equipment', 'textarea', 1,
            placeholder='例：\n- 給湯器\n- エアコン\n- 換気扇',
            help_text='対応可能な設備を箇条書きで入力してください'
        )

    def create_painting_category(self):
        """カテゴリ10: 塗装"""
        category, _ = ContractorFieldCategory.objects.get_or_create(
            slug='painting',
            defaults={
                'name': '塗装',
                'description': '塗装関連の施工費用',
                'order': 10
            }
        )

        self.create_field(
            category, '塗装（外構）金額 (¥)', 'exterior_painting_cost', 'number', 1,
            placeholder='例: 100000',
            help_text='外構塗装の費用',
            min_value=0
        )

        self.create_field(
            category, '足場契約あり', 'scaffolding_contract', 'checkbox', 2,
            help_text='足場契約がある場合はチェック'
        )

        self.create_field(
            category, '家まるごと金額 (¥)', 'scaffolding_whole_house_cost', 'number', 3,
            placeholder='例: 500000',
            help_text='足場契約がある場合の家まるごとの金額',
            min_value=0
        )

    def create_carpentry_category(self):
        """カテゴリ11: 大工"""
        category, _ = ContractorFieldCategory.objects.get_or_create(
            slug='carpentry',
            defaults={
                'name': '大工',
                'description': '大工関連の情報',
                'order': 11
            }
        )

        self.create_field(
            category, '対応可能工事タイプ', 'carpentry_type', 'select', 1,
            help_text='対応可能な工事タイプを選択',
            choices=['新築のみ', 'リノベもできる']
        )

        self.create_field(
            category, '大工備考', 'carpentry_notes', 'textarea', 2,
            placeholder='例：木造専門、リフォーム経験豊富',
            help_text='大工関連の備考を入力'
        )

    def create_supported_services_category(self):
        """カテゴリ13: 対応可能なこと"""
        category, _ = ContractorFieldCategory.objects.get_or_create(
            slug='supported_services',
            defaults={
                'name': '対応可能なこと',
                'description': '',
                'order': 13
            }
        )

        self.create_field(
            category, '給湯器', 'supports_water_heater', 'checkbox', 1,
            help_text='給湯器の取り扱い可否'
        )
        self.create_field(
            category, 'エアコン', 'supports_aircon', 'checkbox', 2,
            help_text='エアコンの取り扱い可否'
        )
        self.create_field(
            category, '洗面化粧台', 'supports_vanity', 'checkbox', 3,
            help_text='洗面化粧台の取り扱い可否'
        )
        self.create_field(
            category, 'トイレ', 'supports_toilet', 'checkbox', 4,
            help_text='トイレの取り扱い可否'
        )
        self.create_field(
            category, 'キッチン', 'supports_kitchen', 'checkbox', 5,
            help_text='キッチンの取り扱い可否'
        )
        self.create_field(
            category, '浴室', 'supports_bathroom', 'checkbox', 6,
            help_text='浴室の取り扱い可否'
        )
        self.create_field(
            category, '換気扇', 'supports_ventilation', 'checkbox', 7,
            help_text='換気扇の取り扱い可否'
        )
        self.create_field(
            category, '食洗機', 'supports_dishwasher', 'checkbox', 8,
            help_text='食洗機の取り扱い可否'
        )
        self.create_field(
            category, 'IH', 'supports_ih', 'checkbox', 9,
            help_text='IHコンロの取り扱い可否'
        )
        self.create_field(
            category, '解体', 'supports_demolition', 'checkbox', 10,
            help_text='解体作業の対応可否'
        )
        self.create_field(
            category, '産廃', 'supports_waste_disposal', 'checkbox', 11,
            help_text='産業廃棄物処理の対応可否'
        )

    def create_work_style_category(self):
        """カテゴリ14: 仕事のスタイル"""
        category, _ = ContractorFieldCategory.objects.get_or_create(
            slug='work_style',
            defaults={
                'name': '仕事のスタイル',
                'description': '',
                'order': 14
            }
        )

        self.create_field(
            category, 'CL下請け可否', 'accepts_cl_subcontract', 'select', 1,
            help_text='CL（元請）の下請けとして働く意思',
            choices=['○', '×', '△']
        )

        self.create_field(
            category, '直接施工可否', 'direct_construction', 'select', 2,
            help_text='直接施工（元請として）の対応可否',
            choices=['○', '×', '△']
        )

        self.create_field(
            category, '協力会社タイプ', 'cooperation_type', 'select', 3,
            help_text='協力体制のタイプ',
            choices=['常時協力', '案件ベース', '繁忙期のみ']
        )

        self.create_field(
            category, '緊急対応可否', 'emergency_support', 'checkbox', 4,
            help_text='緊急案件への対応可否'
        )

        self.create_field(
            category, '休日対応可否', 'weekend_work', 'checkbox', 5,
            help_text='休日作業の対応可否'
        )

    def create_other_info_category(self):
        """カテゴリ15: その他の情報"""
        category, _ = ContractorFieldCategory.objects.get_or_create(
            slug='other_info',
            defaults={
                'name': 'その他の情報',
                'description': '業者の特性や注意事項',
                'order': 15
            }
        )

        self.create_field(
            category, '時間厳守レベル', 'time_punctuality', 'select', 1,
            help_text='時間厳守のレベルを選択',
            choices=['1. 完工までは必ず守ってくれる', '2. 着工の時間を守れる', '3. 守れない']
        )

        self.create_field(
            category, '在宅空室可否', 'occupancy_preference', 'multiselect', 2,
            help_text='対応可能な状況を選択（複数選択可）',
            choices=['空室（元請・お客さんと触れない）', '在宅（元請・お客さんと会ってもOK）']
        )

        self.create_field(
            category, '性格の備考', 'personality_notes', 'textarea', 3,
            placeholder='例：丁寧、几帳面、コミュニケーション良好',
            help_text='業者の性格や特徴について'
        )

        self.create_field(
            category, '注意事項', 'precautions', 'textarea', 4,
            placeholder='例：事前連絡必須、午前中のみ対応可能',
            help_text='業者に関する注意事項'
        )
