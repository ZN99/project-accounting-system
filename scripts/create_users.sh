#!/bin/bash

# ユーザー作成スクリプト
# Usage: ./scripts/create_users.sh

echo "=========================================="
echo "  ユーザー作成スクリプト"
echo "=========================================="
echo ""

# Djangoシェルコマンドを実行
python manage.py shell << 'EOF'
from django.contrib.auth.models import User
from order_management.models import UserProfile

# 作成するユーザーのリスト
users_data = [
    {
        'username': 'ikuta',
        'password': 'kA3jJMXi',
        'last_name': '生田',
        'first_name': '',
    },
    {
        'username': 'taki',
        'password': 'B7rCa8Jg',
        'last_name': '瀧',
        'first_name': '',
    },
    {
        'username': 'satou',
        'password': 'Pj2ukcRd',
        'last_name': '佐藤',
        'first_name': '',
    },
    {
        'username': 'miyoshi',
        'password': 'Mv4LCt2k',
        'last_name': '三好',
        'first_name': '',
    },
]

print("\n👥 ユーザー作成を開始します...\n")

for user_data in users_data:
    username = user_data['username']

    # 既存ユーザーをチェック
    if User.objects.filter(username=username).exists():
        print(f"⚠️  {username} は既に存在します - スキップ")
        continue

    # ユーザーを作成
    user = User.objects.create_user(
        username=username,
        password=user_data['password'],
        last_name=user_data['last_name'],
        first_name=user_data['first_name'],
    )

    # UserProfileを作成（ロールは後で管理画面から設定）
    profile, created = UserProfile.objects.get_or_create(user=user)

    print(f"✅ {username} ({user_data['last_name']}) を作成しました")

print("\n========================================")
print("  作成完了！")
print("========================================")
print("\n📝 次のステップ:")
print("  1. 管理画面 (http://localhost:8000/admin/) にアクセス")
print("  2. 各ユーザーにロール（営業/配車/経理/役員）を設定")
print("\nまたは以下のコマンドでロールを設定:")
print("  python manage.py manage_user_roles --user ikuta --add 営業")
print("  python manage.py manage_user_roles --user taki --add 配車")
print("  python manage.py manage_user_roles --user satou --add 経理")
print("  python manage.py manage_user_roles --user miyoshi --add 役員")
print("")

EOF

echo ""
echo "✨ スクリプト実行完了"
