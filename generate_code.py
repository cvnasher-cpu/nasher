"""
ناشر — مولّد رموز التفعيل
Run: python generate_code.py
"""

import json
import random
import os
import sys
import shutil
from datetime import datetime

BASE_DIR   = os.path.dirname(os.path.abspath(__file__))
DATA_PATH  = os.environ.get('DATA_PATH', os.path.join(BASE_DIR, 'data'))
CODES_FILE = os.path.join(DATA_PATH, 'codes.json')
_SEED_FILE = os.path.join(BASE_DIR, 'codes.json')

os.makedirs(DATA_PATH, exist_ok=True)

# On first run, bootstrap from the root-level seed file if the data one doesn't exist yet
if not os.path.exists(CODES_FILE) and os.path.exists(_SEED_FILE):
    shutil.copy(_SEED_FILE, CODES_FILE)

PACKAGES = [500, 1000, 1500, 2000, 2500]


def generate_code():
    return str(random.randint(100000, 999999))


def load_codes():
    if not os.path.exists(CODES_FILE):
        return {}
    with open(CODES_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)


def save_codes(codes):
    with open(CODES_FILE, 'w', encoding='utf-8') as f:
        json.dump(codes, f, indent=2, ensure_ascii=False)


def list_codes():
    codes = load_codes()
    if not codes:
        print('لا توجد رموز بعد.')
        return
    print(f'\n{"الرمز":<20} {"الباقة":>8} {"الحالة":>10} {"تاريخ الإنشاء":>22}')
    print('-' * 65)
    for code, data in codes.items():
        status = 'مستخدم ✗' if data.get('used') else 'متاح  ✓'
        created = data.get('created_at', '')[:10]
        print(f'{code:<20} {data["package"]:>8} {status:>12} {created:>20}')
    total = len(codes)
    used = sum(1 for d in codes.values() if d.get('used'))
    print(f'\nالإجمالي: {total} | مستخدم: {used} | متاح: {total - used}')


def main():
    print('\n' + '═' * 45)
    print('       ناشر — مولّد رموز التفعيل')
    print('═' * 45)
    print('\nما الذي تريد فعله؟')
    print('  1. إنشاء رموز جديدة')
    print('  2. عرض جميع الرموز')
    print('  3. خروج')

    choice = input('\nاختر (1-3): ').strip()

    if choice == '3':
        sys.exit(0)

    if choice == '2':
        list_codes()
        return

    if choice != '1':
        print('اختيار غير صحيح')
        return

    print('\nاختر حجم الباقة:')
    for i, p in enumerate(PACKAGES, 1):
        price_map = {500: '49', 1000: '89', 1500: '129', 2000: '169', 2500: '199'}
        print(f'  {i}. {p:>5} شركة')

    while True:
        try:
            pkg_choice = int(input('\nرقم الباقة (1-5): ').strip())
            if 1 <= pkg_choice <= 5:
                package = PACKAGES[pkg_choice - 1]
                break
            print('أدخل رقماً بين 1 و 5')
        except ValueError:
            print('يرجى إدخال رقم صحيح')

    while True:
        try:
            count = int(input('كم رمزاً تريد إنشاء؟ ').strip())
            if count > 0:
                break
            print('يجب أن يكون العدد أكبر من صفر')
        except ValueError:
            print('يرجى إدخال رقم صحيح')

    codes = load_codes()
    new_codes = []

    for _ in range(count):
        attempts = 0
        while True:
            code = generate_code()
            if code not in codes:
                break
            attempts += 1
            if attempts > 1000:
                print('خطأ: لم يتمكن من إنشاء رمز فريد')
                sys.exit(1)

        codes[code] = {
            'package': package,
            'used': False,
            'created_at': datetime.now().isoformat()
        }
        new_codes.append(code)

    save_codes(codes)

    print(f'\n✓ تم إنشاء {count} رمز لباقة {package} شركة:\n')
    for code in new_codes:
        print(f'  {code}')

    print(f'\nتم الحفظ في: {CODES_FILE}\n')


if __name__ == '__main__':
    main()
