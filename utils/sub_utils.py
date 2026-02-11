# Obuna tekshirish funksiyasi
async def not_subscribed(user_id, bot):
    from utils.db_utils import get_all_channels
    
    channels = get_all_channels()
    not_joined = []
    
    for ch in channels:
        if ch.startswith("@"):  # faqat @ tekshiramiz
            try:
                member = await bot.get_chat_member(ch, user_id)
                if member.status in ["left", "kicked"]:
                    not_joined.append(ch)
            except:
                not_joined.append(ch)
        # https:// kanallar tekshirilmaydi
    return not_joined
