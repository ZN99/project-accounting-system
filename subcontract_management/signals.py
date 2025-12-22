"""
Signals for recalculating project profits when related models change.
"""
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from .models import Subcontract
from order_management.models import MaterialOrder


@receiver(post_save, sender=Subcontract)
def recalculate_project_profit_on_subcontract_save(sender, instance, created, **kwargs):
    """下請作業保存時にプロジェクトの利益を再計算"""
    if instance.project:
        try:
            # ProjectProgressStepの同期処理と同様に、再帰防止のため
            # update()ではなくsave()を使う（ただし無限ループに注意）
            instance.project._update_profit_cache()
            # update()で利益フィールドのみ更新（save()シグナルを発火させない）
            from order_management.models import Project
            Project.objects.filter(pk=instance.project.pk).update(
                gross_profit=instance.project.gross_profit,
                profit_margin=instance.project.profit_margin
            )
        except Exception as e:
            print(f"⚠ Warning: Failed to recalculate profit for project {instance.project.pk}: {e}")


@receiver(post_delete, sender=Subcontract)
def recalculate_project_profit_on_subcontract_delete(sender, instance, **kwargs):
    """下請作業削除時にプロジェクトの利益を再計算"""
    if instance.project:
        try:
            instance.project._update_profit_cache()
            from order_management.models import Project
            Project.objects.filter(pk=instance.project.pk).update(
                gross_profit=instance.project.gross_profit,
                profit_margin=instance.project.profit_margin
            )
        except Exception as e:
            print(f"⚠ Warning: Failed to recalculate profit for project {instance.project.pk}: {e}")


@receiver(post_save, sender=MaterialOrder)
def recalculate_project_profit_on_material_order_save(sender, instance, created, **kwargs):
    """資材発注保存時にプロジェクトの利益を再計算"""
    if instance.project:
        try:
            instance.project._update_profit_cache()
            from order_management.models import Project
            Project.objects.filter(pk=instance.project.pk).update(
                gross_profit=instance.project.gross_profit,
                profit_margin=instance.project.profit_margin
            )
        except Exception as e:
            print(f"⚠ Warning: Failed to recalculate profit for project {instance.project.pk}: {e}")


@receiver(post_delete, sender=MaterialOrder)
def recalculate_project_profit_on_material_order_delete(sender, instance, **kwargs):
    """資材発注削除時にプロジェクトの利益を再計算"""
    if instance.project:
        try:
            instance.project._update_profit_cache()
            from order_management.models import Project
            Project.objects.filter(pk=instance.project.pk).update(
                gross_profit=instance.project.gross_profit,
                profit_margin=instance.project.profit_margin
            )
        except Exception as e:
            print(f"⚠ Warning: Failed to recalculate profit for project {instance.project.pk}: {e}")
