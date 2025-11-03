# Generated migration for Phase 0: 用語統一とステータス体系変更

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('order_management', '0012_invoice_invoiceitem'),
    ]

    operations = [
        # フィールド名変更: order_status → project_status
        migrations.RenameField(
            model_name='project',
            old_name='order_status',
            new_name='project_status',
        ),

        # フィールド名変更: estimate_amount → order_amount
        migrations.RenameField(
            model_name='project',
            old_name='estimate_amount',
            new_name='order_amount',
        ),

        # フィールド名変更: contractor_name → client_name
        migrations.RenameField(
            model_name='project',
            old_name='contractor_name',
            new_name='client_name',
        ),

        # フィールド名変更: contractor_address → client_address
        migrations.RenameField(
            model_name='project',
            old_name='contractor_address',
            new_name='client_address',
        ),

        # project_status の max_length を拡張（「施工日待ち」対応）
        migrations.AlterField(
            model_name='project',
            name='project_status',
            field=models.CharField(
                choices=[
                    ('ネタ', 'ネタ'),
                    ('施工日待ち', '施工日待ち'),
                    ('進行中', '進行中'),
                    ('完工', '完工'),
                    ('NG', 'NG'),
                ],
                default='ネタ',
                max_length=20,
                verbose_name='案件進捗'
            ),
        ),

        # order_amount の verbose_name 変更
        migrations.AlterField(
            model_name='project',
            name='order_amount',
            field=models.DecimalField(
                decimal_places=0,
                default=0,
                max_digits=10,
                verbose_name='受注金額(税込)'
            ),
        ),

        # client_name の verbose_name 変更
        migrations.AlterField(
            model_name='project',
            name='client_name',
            field=models.CharField(max_length=100, verbose_name='元請名'),
        ),

        # client_address の verbose_name 変更と blank=True 追加
        migrations.AlterField(
            model_name='project',
            name='client_address',
            field=models.TextField(verbose_name='元請住所', blank=True),
        ),

        # site_address を任意項目に変更
        migrations.AlterField(
            model_name='project',
            name='site_address',
            field=models.TextField(verbose_name='現場住所', blank=True),
        ),

        # work_type の verbose_name 変更
        migrations.AlterField(
            model_name='project',
            name='work_type',
            field=models.CharField(max_length=50, verbose_name='施工種別'),
        ),
    ]
