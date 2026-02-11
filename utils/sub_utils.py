from utils.db_utils import get_all_channels
from telegram import ChatMember

async def not_subscribed(user_id, bot):
    channels = get_all_channels()
    missing = []
    for ch in channels:
        if ch.startswith("@"):  # faqat @ bilan boshlanadigan kanalni tekshiradi
            try:
                member = await bot.get_chat_member(ch, user_id)
                if member.status in ["left", "kicked"]:
                    missing.append(ch)
            except:
                missing.append(ch)
        # https:// bilan boshlangan kanallar tekshirilmaydi
    return missing
