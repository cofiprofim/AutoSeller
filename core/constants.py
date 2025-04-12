import re

VERSION = "1.2.3"

SIGNATURE = f"Limiteds Seller Tool v{VERSION}"
TITLE = r"""  ___        _        _____      _ _           
 / _ \      | |      /  ___|    | | |          
/ /_\ \_   _| |_ ___ \ `--.  ___| | | ___ _ __ 
|  _  | | | | __/ _ \ `--. \/ _ \ | |/ _ \ '__|
| | | | |_| | || (_) /\__/ /  __/ | |  __/ |   
\_| |_/\__,_|\__\___/\____/ \___|_|_|\___|_|    

"""

FAILED_IMAGE_URL = "https://i.ibb.co/Cs3Wvgb/7189017466763a9ed8874824aceba073.png"
RAW_CODE_URL = "https://raw.githubusercontent.com/cofiprofim/AutoSeller/refs/heads/main/main.py"

WEBHOOK_PATTERN = re.compile(r"https?://discord.com/api/webhooks/\d+/\w{11}_\w{56}")
COLOR_CODE_PATTERN = re.compile(r"\033\[[0-9;]*m")

ITEM_TYPES = {8: "Hat", 41: "HairAccessory", 42: "FaceAccessory", 43: "NeckAccessory",
              44: "ShoulderAccessory", 45: "FrontAccessory", 46: "BackAccessory",
              47: "WaistAccessory", 64: "TShirtAccessory", 65: "ShirtAccessory",
              66: "PantsAccessory", 67: "JacketAccessory", 68: "SweaterAccessory",
              69: "ShortsAccessory", 72: "DressSkirtAccessory"}
