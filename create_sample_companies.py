"""
Run this script once to create a sample companies.xlsx for testing.
Replace with real company emails before going live.
"""

import openpyxl

SAMPLE_EMAILS = [
    "hr@aramco.com.sa",
    "recruitment@sabic.com",
    "careers@stc.com.sa",
    "jobs@mobily.com.sa",
    "hr@almarai.com",
    "recruitment@samba.com.sa",
    "careers@ncb.com.sa",
    "hr@riyad-bank.com",
    "jobs@alyamamah.com.sa",
    "recruitment@alfanar.com.sa",
]

wb = openpyxl.Workbook()
ws = wb.active
ws.title = "Companies"

for email in SAMPLE_EMAILS:
    ws.append([email])

wb.save("companies.xlsx")
print(f"✓ تم إنشاء companies.xlsx بـ {len(SAMPLE_EMAILS)} شركة نموذجية")
print("  استبدل هذه الإيميلات بالإيميلات الحقيقية للشركات")
