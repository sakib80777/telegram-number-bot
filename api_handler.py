import aiohttp
from database import get_setting

class SMSPanelAPI:
    @staticmethod
    async def fetch_number(country_code: str, service: str):
        api_url = await get_setting("api_url")
        api_key = await get_setting("api_key")
        
        if not api_url or not api_key:
            return None, "API কনফিগার করা নেই! এডমিন বট থেকে API যুক্ত করুন।"

        params = {
            "api_key": api_key,
            "action": "getNumber",
            "service": service,
            "country": country_code
        }
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(api_url, params=params, timeout=10) as resp:
                    text = await resp.text()
                    if "ACCESS_NUMBER" in text:
                        parts = text.split(":")
                        return {"id": parts[1], "number": parts[2]}, None
                    return None, f"প্যানেল এরর: {text}"
        except Exception as e:
            return None, f"কানেকশন এরর: {str(e)}"

    @staticmethod
    async def check_otp(activation_id: str):
        api_url = await get_setting("api_url")
        api_key = await get_setting("api_key")
        params = {
            "api_key": api_key,
            "action": "getStatus",
            "id": activation_id
        }
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(api_url, params=params, timeout=10) as resp:
                    text = await resp.text()
                    if "STATUS_OK" in text:
                        return text.split(":")[1]
                    return None
        except:
            return None
