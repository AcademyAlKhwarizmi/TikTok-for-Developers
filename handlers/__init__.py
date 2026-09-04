from .start import register as register_start
from .subscription import register as register_subscription
from .tiktok import register as register_tiktok
from .schedule import register as register_schedule
from .posts import register as register_posts
from .admin import register as register_admin

def register_handlers(app):
    for fn in (register_start, register_subscription, register_tiktok, register_schedule, register_posts, register_admin):
        fn(app)
