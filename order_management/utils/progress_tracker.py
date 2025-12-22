"""
CSV Import Progress Tracker

ファイルベースの進捗トラッキングシステム
バックグラウンドで実行されるインポートコマンドの進捗状況を追跡します。
"""

import json
import os
from pathlib import Path
from typing import Optional


class ProgressTracker:
    """
    進捗状況をJSON形式でファイルに保存するトラッカー

    複数プロセス間で進捗状況を共有するための軽量な実装。
    """

    def __init__(self, progress_file: str):
        """
        Args:
            progress_file: 進捗状況を保存するJSONファイルパス
        """
        self.progress_file = progress_file
        self._ensure_directory()
        self._initialize()

    def _ensure_directory(self):
        """ディレクトリが存在することを確認"""
        directory = os.path.dirname(self.progress_file)
        if directory:
            Path(directory).mkdir(parents=True, exist_ok=True)

    def _initialize(self):
        """初期状態を設定"""
        self.update(
            status='starting',
            progress=0,
            message='初期化中...',
            step='initialization',
            logs=[]
        )

    def update(self, status: str, progress: int, message: str, step: str, **extra_data):
        """
        進捗状況を更新

        Args:
            status: 処理状態 ('starting', 'processing', 'completed', 'error')
            progress: 進捗率 (0-100)
            message: 現在の処理内容
            step: 処理ステップID
            **extra_data: 追加データ（結果の統計など）
        """
        data = {
            'status': status,
            'progress': progress,
            'message': message,
            'step': step
        }

        # 追加データをマージ
        data.update(extra_data)

        try:
            with open(self.progress_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            # ファイル書き込みエラーは無視（進捗トラッキングは必須ではない）
            pass

    @classmethod
    def read_progress(cls, progress_file: str) -> Optional[dict]:
        """
        進捗状況を読み込む

        Args:
            progress_file: 進捗ファイルパス

        Returns:
            進捗状況の辞書、またはNone
        """
        try:
            if not os.path.exists(progress_file):
                return {
                    'status': 'idle',
                    'progress': 0,
                    'message': '',
                    'step': ''
                }

            with open(progress_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            return {
                'status': 'idle',
                'progress': 0,
                'message': '',
                'step': ''
            }

    def complete(self, message: str = 'インポート完了', **extra_data):
        """処理完了を記録"""
        self.update(
            status='completed',
            progress=100,
            message=message,
            step='completed',
            **extra_data
        )

    def error(self, message: str):
        """エラーを記録"""
        self.update(
            status='error',
            progress=0,
            message=message,
            step='error'
        )

    def cleanup(self):
        """進捗ファイルを削除"""
        try:
            if os.path.exists(self.progress_file):
                os.remove(self.progress_file)
        except Exception:
            pass

    def is_cancelled(self) -> bool:
        """
        キャンセルがリクエストされているかチェック

        Returns:
            bool: キャンセルされている場合True
        """
        try:
            if not os.path.exists(self.progress_file):
                return False

            with open(self.progress_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data.get('cancel_requested', False)
        except Exception:
            return False

    def cancel(self):
        """キャンセルをリクエスト"""
        try:
            if os.path.exists(self.progress_file):
                with open(self.progress_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                data['cancel_requested'] = True
                data['status'] = 'cancelled'
                data['message'] = 'キャンセルされました'

                with open(self.progress_file, 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def add_log(self, log_message: str, log_type: str = 'info'):
        """
        ログメッセージを追加

        Args:
            log_message: ログメッセージ
            log_type: ログタイプ ('info', 'success', 'warning', 'error')
        """
        try:
            if not os.path.exists(self.progress_file):
                return

            with open(self.progress_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # ログ配列を取得（なければ作成）
            logs = data.get('logs', [])

            # タイムスタンプ付きログを追加
            from datetime import datetime
            timestamp = datetime.now().strftime('%H:%M:%S')

            logs.append({
                'timestamp': timestamp,
                'message': log_message,
                'type': log_type
            })

            data['logs'] = logs

            with open(self.progress_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception:
            pass
