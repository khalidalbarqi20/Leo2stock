"""
Scheduler / Continuous Scanner
================================
⚠️ حد صريح مهم: بيئة التطوير هذي ما تقدر تشغّل Process مستمر 24/7 (Container مؤقت).
"الاستمرارية" الفعلية تتحقق بإحدى طريقتين، تختار وحدة منهما وتربطها بـ:
POST /api/cron/scan-all  مع Header: Authorization: Bearer <CRON_SECRET>

  الخيار 1 (مجاني، يناسب Termux/GitHub، وأنت مستخدم GitHub Actions سابقاً):
     GitHub Actions "schedule" (cron) في نفس مستودع المشروع يستدعي الـendpoint كل 5-15 دقيقة.

  الخيار 2 (يحتاج خطة Render مدفوعة تدعم Background Worker أو Cron Job):
     Render Cron Job / Background Worker يشغّل هذا الملف مباشرة على فترات.

هذا الملف نفسه لا "يعمل" شيئاً تلقائياً بمجرد رفعه — لازم شيء خارجي يستدعيه دورياً.
"""
import storage
import scanner as scanner_module
import market_hours


def run_all_active_strategies(fetcher, analyzer):
    """
    يفحص كل استراتيجية Active لكل المستخدمين، لكن يتخطى أي سوق مغلق حالياً
    (لا فائدة من إعادة فحص نفس الشمعة اليومية وقت إغلاق السوق).
    """
    results = []
    saudi_open = market_hours.is_market_open('saudi')
    us_open = market_hours.is_market_open('us')

    all_users = storage.list_users()
    for user in all_users:
        uid = user['user_id']
        for strategy in storage.list_strategies(uid, active_only=True):
            market = strategy['market']
            if market == 'saudi' and not saudi_open:
                results.append({'strategy_id': strategy['id'], 'skipped': 'market_closed_saudi'})
                continue
            if market == 'us' and not us_open:
                results.append({'strategy_id': strategy['id'], 'skipped': 'market_closed_us'})
                continue
            try:
                r = scanner_module.run_scan(strategy, fetcher, analyzer, user_id=uid, with_ai=True)
                results.append(r)
            except Exception as e:
                print(f"scheduler: strategy {strategy['id']} failed: {e}")
                results.append({'strategy_id': strategy['id'], 'error': str(e)})

    return {'saudi_open': saudi_open, 'us_open': us_open, 'strategies_processed': len(results),
            'results': results}
