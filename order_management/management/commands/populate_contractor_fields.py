"""
業者カスタムフィールドの初期データを投入する管理コマンド
"""
from django.core.management.base import BaseCommand
from subcontract_management.models import ContractorFieldCategory, ContractorFieldDefinition


class Command(BaseCommand):
    help = '業者カスタムフィールドの初期データを投入'

    def handle(self, *args, **options):
        self.stdout.write('業者カスタムフィールドの初期データを投入します...')

        # カテゴリとフィールドの定義
        categories_data = [
            {
                'name': '基本情報',
                'slug': 'basic_info',
                'order': 1,
                'fields': [
                    {
                        'name': '年齢',
                        'slug': 'age',
                        'field_type': 'number',
                        'placeholder': '例: 45',
                        'help_text': '業者の年齢または代表者の年齢',
                        'min_value': 18,
                        'max_value': 100,
                    },
                    {
                        'name': '対応エリア',
                        'slug': 'service_areas',
                        'field_type': 'textarea',
                        'placeholder': '例: 東京23区、神奈川県全域',
                        'help_text': '対応可能な地域を入力',
                    },
                    {
                        'name': '納品書番号',
                        'slug': 'delivery_note_number',
                        'field_type': 'text',
                        'placeholder': '例: DN-2025-001',
                        'help_text': '納品書の管理番号',
                    },
                ]
            },
            {
                'name': '問屋契約',
                'slug': 'wholesale_contracts',
                'order': 2,
                'fields': [
                    {
                        'name': 'アサヒ衛陶',
                        'slug': 'asahi_sanitaryware',
                        'field_type': 'checkbox',
                        'help_text': 'アサヒ衛陶との契約有無',
                    },
                    {
                        'name': 'Panasonic',
                        'slug': 'panasonic',
                        'field_type': 'checkbox',
                        'help_text': 'Panasonicとの契約有無',
                    },
                    {
                        'name': 'クリナップ',
                        'slug': 'cleanup',
                        'field_type': 'checkbox',
                        'help_text': 'クリナップとの契約有無',
                    },
                    {
                        'name': 'ノーリツ',
                        'slug': 'noritz',
                        'field_type': 'checkbox',
                        'help_text': 'ノーリツとの契約有無',
                    },
                    {
                        'name': 'リンナイ',
                        'slug': 'rinnai',
                        'field_type': 'checkbox',
                        'help_text': 'リンナイとの契約有無',
                    },
                    {
                        'name': 'TOTO',
                        'slug': 'toto',
                        'field_type': 'checkbox',
                        'help_text': 'TOTOとの契約有無',
                    },
                    {
                        'name': 'LIXIL',
                        'slug': 'lixil',
                        'field_type': 'checkbox',
                        'help_text': 'LIXILとの契約有無',
                    },
                    {
                        'name': 'タカラスタンダード',
                        'slug': 'takara_standard',
                        'field_type': 'checkbox',
                        'help_text': 'タカラスタンダードとの契約有無',
                    },
                ]
            },
            {
                'name': '金額の融通',
                'slug': 'price_flexibility',
                'order': 3,
                'fields': [
                    {
                        'name': '給湯器',
                        'slug': 'water_heater_discount',
                        'field_type': 'select',
                        'choices': ['○', '×', '△'],
                        'help_text': '給湯器の金額調整可否',
                    },
                    {
                        'name': 'エアコン',
                        'slug': 'aircon_discount',
                        'field_type': 'select',
                        'choices': ['○', '×', '△'],
                        'help_text': 'エアコンの金額調整可否',
                    },
                    {
                        'name': '洗面化粧台',
                        'slug': 'vanity_discount',
                        'field_type': 'select',
                        'choices': ['○', '×', '△'],
                        'help_text': '洗面化粧台の金額調整可否',
                    },
                    {
                        'name': 'トイレ',
                        'slug': 'toilet_discount',
                        'field_type': 'select',
                        'choices': ['○', '×', '△'],
                        'help_text': 'トイレの金額調整可否',
                    },
                    {
                        'name': 'キッチン',
                        'slug': 'kitchen_discount',
                        'field_type': 'select',
                        'choices': ['○', '×', '△'],
                        'help_text': 'キッチンの金額調整可否',
                    },
                    {
                        'name': '浴室',
                        'slug': 'bathroom_discount',
                        'field_type': 'select',
                        'choices': ['○', '×', '△'],
                        'help_text': '浴室の金額調整可否',
                    },
                    {
                        'name': '換気扇',
                        'slug': 'ventilation_discount',
                        'field_type': 'select',
                        'choices': ['○', '×', '△'],
                        'help_text': '換気扇の金額調整可否',
                    },
                    {
                        'name': '食洗機',
                        'slug': 'dishwasher_discount',
                        'field_type': 'select',
                        'choices': ['○', '×', '△'],
                        'help_text': '食洗機の金額調整可否',
                    },
                    {
                        'name': 'IH',
                        'slug': 'ih_discount',
                        'field_type': 'select',
                        'choices': ['○', '×', '△'],
                        'help_text': 'IHコンロの金額調整可否',
                    },
                ]
            },
            {
                'name': '対応可能なこと',
                'slug': 'supported_services',
                'order': 4,
                'fields': [
                    {
                        'name': '給湯器',
                        'slug': 'supports_water_heater',
                        'field_type': 'checkbox',
                        'help_text': '給湯器の取り扱い可否',
                    },
                    {
                        'name': 'エアコン',
                        'slug': 'supports_aircon',
                        'field_type': 'checkbox',
                        'help_text': 'エアコンの取り扱い可否',
                    },
                    {
                        'name': '洗面化粧台',
                        'slug': 'supports_vanity',
                        'field_type': 'checkbox',
                        'help_text': '洗面化粧台の取り扱い可否',
                    },
                    {
                        'name': 'トイレ',
                        'slug': 'supports_toilet',
                        'field_type': 'checkbox',
                        'help_text': 'トイレの取り扱い可否',
                    },
                    {
                        'name': 'キッチン',
                        'slug': 'supports_kitchen',
                        'field_type': 'checkbox',
                        'help_text': 'キッチンの取り扱い可否',
                    },
                    {
                        'name': '浴室',
                        'slug': 'supports_bathroom',
                        'field_type': 'checkbox',
                        'help_text': '浴室の取り扱い可否',
                    },
                    {
                        'name': '換気扇',
                        'slug': 'supports_ventilation',
                        'field_type': 'checkbox',
                        'help_text': '換気扇の取り扱い可否',
                    },
                    {
                        'name': '食洗機',
                        'slug': 'supports_dishwasher',
                        'field_type': 'checkbox',
                        'help_text': '食洗機の取り扱い可否',
                    },
                    {
                        'name': 'IH',
                        'slug': 'supports_ih',
                        'field_type': 'checkbox',
                        'help_text': 'IHコンロの取り扱い可否',
                    },
                    {
                        'name': '解体',
                        'slug': 'supports_demolition',
                        'field_type': 'checkbox',
                        'help_text': '解体作業の対応可否',
                    },
                    {
                        'name': '産廃',
                        'slug': 'supports_waste_disposal',
                        'field_type': 'checkbox',
                        'help_text': '産業廃棄物処理の対応可否',
                    },
                ]
            },
            {
                'name': '仕事のスタイル',
                'slug': 'work_style',
                'order': 5,
                'fields': [
                    {
                        'name': 'CL下請け可否',
                        'slug': 'accepts_cl_subcontract',
                        'field_type': 'select',
                        'choices': ['○', '×', '△'],
                        'help_text': 'CL（元請）の下請けとして働く意思',
                    },
                    {
                        'name': '直接施工可否',
                        'slug': 'direct_construction',
                        'field_type': 'select',
                        'choices': ['○', '×', '△'],
                        'help_text': '直接施工（元請として）の対応可否',
                    },
                    {
                        'name': '協力会社タイプ',
                        'slug': 'cooperation_type',
                        'field_type': 'select',
                        'choices': ['常時協力', '案件ベース', '繁忙期のみ'],
                        'help_text': '協力体制のタイプ',
                    },
                    {
                        'name': '緊急対応可否',
                        'slug': 'emergency_support',
                        'field_type': 'checkbox',
                        'help_text': '緊急案件への対応可否',
                    },
                    {
                        'name': '休日対応可否',
                        'slug': 'weekend_work',
                        'field_type': 'checkbox',
                        'help_text': '休日作業の対応可否',
                    },
                ]
            },
            {
                'name': 'その他',
                'slug': 'others',
                'order': 6,
                'fields': [
                    {
                        'name': '特記事項',
                        'slug': 'special_notes',
                        'field_type': 'textarea',
                        'placeholder': 'その他特記すべき事項を入力',
                        'help_text': '業者に関する特別な情報やメモ',
                    },
                    {
                        'name': '評価',
                        'slug': 'rating',
                        'field_type': 'select',
                        'choices': ['S', 'A', 'B', 'C'],
                        'help_text': '業者の総合評価（S:最高 ～ C:要改善）',
                    },
                    {
                        'name': '最終取引日',
                        'slug': 'last_transaction_date',
                        'field_type': 'date',
                        'help_text': '最後に取引した日付',
                    },
                ]
            },
        ]

        created_categories = 0
        created_fields = 0

        for cat_data in categories_data:
            # カテゴリ作成
            category, created = ContractorFieldCategory.objects.get_or_create(
                slug=cat_data['slug'],
                defaults={
                    'name': cat_data['name'],
                    'order': cat_data['order'],
                    'is_active': True,
                }
            )

            if created:
                created_categories += 1
                self.stdout.write(f'  ✓ カテゴリ作成: {category.name}')
            else:
                self.stdout.write(f'  - カテゴリ既存: {category.name}')

            # フィールド作成
            for idx, field_data in enumerate(cat_data['fields'], start=1):
                field_def, created = ContractorFieldDefinition.objects.get_or_create(
                    category=category,
                    slug=field_data['slug'],
                    defaults={
                        'name': field_data['name'],
                        'field_type': field_data['field_type'],
                        'placeholder': field_data.get('placeholder', ''),
                        'help_text': field_data.get('help_text', ''),
                        'choices': field_data.get('choices', []),
                        'min_value': field_data.get('min_value'),
                        'max_value': field_data.get('max_value'),
                        'order': idx,
                        'is_active': True,
                    }
                )

                if created:
                    created_fields += 1
                    self.stdout.write(f'    ✓ フィールド作成: {field_def.name}')

        self.stdout.write(self.style.SUCCESS(
            f'\n完了: {created_categories}個のカテゴリと{created_fields}個のフィールドを作成しました'
        ))
