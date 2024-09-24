from typing import List, Iterable, Union

from .utils import slice_list, Auth


FAILED_IMAGE_URL = "https://t4.rbxcdn.com/7189017466763a9ed8874824aceba073"


async def get_recent_sales(auth: Auth) -> List[dict]:
    async with auth.session.get(
        f"https://economy.roblox.com/v2/users/{auth.user_id}/transactions?"
        "cursor=&limit=10&transactionType=Sale&itemPricingType=PaidAndLimited",
        ssl=False
    ) as response:
            if response.status != 200:
                return None
        
            return (await response.json()).get("data")


async def get_users_thumbnails(user_ids: Iterable[str], auth: Auth) -> Union[List[str], None]:
    thumbnails = []

    for chunk in slice_list(user_ids, 100):
        async with auth.session.get(
            "https://thumbnails.roblox.com/v1/users/avatar-headshot?"
            f"userIds={','.join(chunk)}&size=50x50&format=Png&isCircular=false",
            ssl=False
        ) as response:
            data = (await response.json()).get("data")

            if data is None:
                return thumbnails

            thumbnails_with_ids = {str(img["targetId"]): img["imageUrl"] if img["state"] == "Completed" else FAILED_IMAGE_URL for img in data}

            for user_id in user_ids:
                if user_id in thumbnails_with_ids:
                        thumbnails.append(thumbnails_with_ids[user_id])

    return thumbnails


async def get_assets_thumbnails(asset_ids: Iterable[str], auth: Auth) -> Union[List[str], None]:
    thumbnails = []

    for chunk in slice_list(asset_ids, 100):
        async with auth.session.get(
            "https://thumbnails.roblox.com/v1/assets?"
            f"assetIds={','.join(chunk)}&returnPolicy=PlaceHolder&size=50x50&format=Png&isCircular=false",
            ssl=False
        ) as response:
            data = (await response.json()).get("data")

            if data is None:
                return thumbnails

            thumbnails_with_ids = {str(img["targetId"]): img["imageUrl"] if img["state"] == "Completed" else FAILED_IMAGE_URL for img in data}

            for item_id in asset_ids:
                if item_id in thumbnails_with_ids:
                    thumbnails.append(thumbnails_with_ids[item_id])

    return thumbnails

async def get_items_details(item_ids: List[Union[int, str]], auth: Auth) -> List[dict]:
    items = []

    for chunk in slice_list(item_ids, 120):
        payload = {"items": [{"itemType": 1, "id": str(_id)} for _id in chunk]}

        async with auth.session.post(
            "https://catalog.roblox.com/v1/catalog/items/details",
            json=payload
        ) as response:
            data = (await response.json()).get("data")

            if data is None:
                return items

            items_with_ids = {str(details["id"]): details for details in data}

            for item_id in item_ids:
                if item_id in items_with_ids:
                    items.append(items_with_ids[item_id])

    return items

async def get_user_inventory(item_type: int, auth: Auth) -> List[dict]:
    assets = []
    cursor = ""

    while True:
        async with auth.session.get(
            f"https://inventory.roblox.com/v2/users/{auth.user_id}/inventory/{item_type}?"
            f"limit=100&cursor={cursor}&sortOrder=Desc",
            ssl=False
        ) as response:
            if response.status != 200:
                return assets

            data = await response.json()

            cursor = data.get("nextPageCursor")
            assets.extend(
                    [asset for asset in data.get("data") if asset.get("collectibleItemId") is not None])

            if not cursor:
                return assets

async def get_current_cap(auth: Auth) -> Union[dict, None]:
    async with auth.session.get(
        "https://itemconfiguration.roblox.com/v1/collectibles/metadata",
        ssl=False
    ) as response:
        return (await response.json()).get("limitedItemPriceFloors")
