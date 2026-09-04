# 🚀 FlowTikTok — Telegram TikTok Automation Bot

بوت Telegram مكتوب بـ Python لإدارة وجدولة ونشر المحتوى على TikTok عبر **TikTok Login Kit + Content Posting API الرسمي فقط**.

> لا Selenium، لا Scraping، لا Cookies، لا Browser Automation.

## مهم قبل التشغيل

TikTok Direct Post يحتاج أن يكون تطبيقك مسجّلًا ومضافًا له Content Posting API، وأن تكون صلاحية `video.publish` معتمدة. العملاء غير المدققين قد تكون منشوراتهم مقيدة للـprivate حسب سياسة TikTok.

**الصور مختلفة عن الفيديو:** Direct Photo Post يعتمد على `PULL_FROM_URL`، لذلك لازم `PUBLIC_BASE_URL` يكون HTTPS ودومين/URL Prefix متحقق في TikTok Developer.

## الملفات

- `bot.py` — FastAPI + Telegram lifecycle + OAuth callback
- `config.py` — إعدادات `.env`
- `database.py` — SQLite/SQLAlchemy
- `scheduler.py` — APScheduler واستعادة الـpending بعد restart
- `handlers/` — واجهة Telegram
- `services/` — TikTok API/OAuth/Storage/Publisher/Tokens
- `utils/` — Emoji/Logging/Validation/Console

## 1) إنشاء مفاتيح البيئة

انسخ:

```bash
cp .env.example .env
```

ولّد Fernet key:

```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

ضع الناتج في:

```env
TOKEN_ENCRYPTION_KEY=...
```

ولا تضع Bot Token أو TikTok Secret داخل الكود.

## 2) TikTok Developer

أنشئ/استخدم تطبيق TikTok Developer ثم فعّل Login Kit وContent Posting API حسب ما يظهر في حساب المطور.

سجّل Redirect URI ثابتًا، مثل:

```text
https://YOUR-DOMAIN.example.com/oauth/callback
```

ويجب أن يطابق `TIKTOK_REDIRECT_URI` حرفيًا.

للـDirect Post تحتاج scope `video.publish`. المستخدم لازم يوافق على الصلاحية أيضًا.

## 3) تثبيت

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Windows:

```powershell
.venv\Scripts\activate
pip install -r requirements.txt
```

## 4) التشغيل

```bash
python bot.py
```

المفروض تشوف Console فيها FlowTikTok وTelegram ONLINE وScheduler RUNNING.

## 5) KataBump

لو KataBump يعطيك خدمة Python/Worker مع Port عام:

1. ارفع المشروع.
2. ضع المتغيرات في Environment Variables.
3. ثبّت dependencies من `requirements.txt`.
4. Start command:
   `python bot.py`
5. استخدم الـHTTPS domain الذي توفره الاستضافة في:
   `TIKTOK_REDIRECT_URI`
   و`PUBLIC_BASE_URL`.
6. افتح:
   `/health`
   للتأكد أن الخدمة شغالة.
7. سجّل نفس Redirect URI داخل TikTok Developer.

لو KataBump لا يوفر HTTPS public web endpoint ثابت، فلن يعمل OAuth callback أو Direct Photo URL بشكل صحيح. وقتها تحتاج Web Service/HTTPS endpoint مناسب، وليس مجرد process داخلي.

## الاشتراك الإجباري

`REQUIRED_CHANNELS` في `.env` يمكن أن يحتوي IDs، لكن الإدارة الأفضل تكون من Admin Panel في النسخة التالية. لكي يعمل فحص العضوية، يجب أن يكون البوت قادرًا على رؤية العضوية في القناة، وغالبًا يحتاج أن يكون Admin في القناة.

## Admin

`ADMIN_ID` يحمي أوامر الإدارة. الواجهة الأساسية موجودة، ويمكن توسيع `handlers/admin.py` لإدارة القنوات والبث والحظر.

## الاختبارات

```bash
pytest -q
```

## ملاحظات TikTok مهمة

- Access Token قصير العمر ويجب تجديده عبر Refresh Token.
- Refresh Token قد يتغير؛ الكود يحفظ القيمة الجديدة عند إرجاعها.
- لا تسجّل tokens في الـlogs.
- لا تعتبر HTTP 200 وحدها نجاحًا؛ الكود يفحص `error.code == "ok"`.
- نجاح init/upload يعيد `publish_id`، وبعدها TikTok يعالج المحتوى بشكل غير متزامن.
- عند الحاجة لتأكيد الحالة النهائية، استخدم Get Post Status.

## اللغة والـUX

كل رسائل المستخدم مصممة بالمصري والحماس، والـCustom Emoji IDs كلها في:

`utils/emojis.py`

لو ID فاضي، يظهر Emoji عادي.

## تطوير مستقبلي

- PostgreSQL عبر تغيير `DATABASE_URL`.
- Redis/Celery عند الأحمال الكبيرة.
- Admin broadcast كامل.
- Pagination متقدمة.
- Dashboard.
- Webhooks/status polling متقدم.


## أوامر الأدمن السريعة

- `/admin` — لوحة الأدمن
- `/addchannel chat_id | اسم القناة | رابط الاشتراك` — إضافة قناة
- `/ban USER_ID` — حظر
- `/unban USER_ID` — فك الحظر

من لوحة الأدمن تقدر تشغّل/تقفل الاشتراك الإجباري، تشوف الإحصائيات، وتعمل Broadcast مع Preview قبل الإرسال.

## نشر الرسائل العامة

زر Broadcast داخل لوحة الأدمن يخليك تبعت رسالة واحدة لكل المستخدمين غير المحظورين، وبعد التأكيد يحسب لك اللي وصل واللي فشل.

## تنبيه مهم عن كلمة "تم النشر"

FlowTikTok لا يعتبر عملية TikTok ناجحة لمجرد أن TikTok رجّع `publish_id`. البوت يستعلم عن حالة النشر حتى يحصل على `PUBLISH_COMPLETE`؛ فقط وقتها يرسل للمستخدم رسالة نجاح. هذا متوافق مع دورة النشر غير المتزامنة في TikTok Content Posting API.


## UI update
النسخة الحالية تحتوي واجهة Inline جديدة، زر فيديو شرح، لوحة Admin موسعة، ودعم Custom Emoji IDs.
فيديو الشرح يرفعه الأدمن من `/admin` ثم زر `🎬 فيديو الشرح`.
تعديل الإيموجيات: `/setemoji KEY EMOJI_ID`.
حذف فيديو الشرح: `/cleartutorial`.

> `.env` المرفق منظف بدون أسرار. ضع BOT_TOKEN وTIKTOK_CLIENT_SECRET وباقي بياناتك قبل التشغيل.
