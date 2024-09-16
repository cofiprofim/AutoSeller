# AutoSeller

#### A roblox tool to sell UGC Limiteds

## Setup

```json
{
    "Cookie": "", Your roblox cookie from where all the items will sell (instruction below)

    "Discord_Bot": {
        "Enabled": false, If you have this enabled, you will get more features to this tool
        "Token": "", Paste here an auth token of your discord appliction (instruction below)
        "Prefix": "!", You can set your prefix to the commands, but this tool also supports slash commands
        "Owner_IDs": [] Paste a user IDs of people who can have a presmission to the commands (empty for everyone)
    },
    "Webhook": {
        "On_Sale": {
            "Enabled": false, This webhook will be send when you will send any item through this tool
            "Url": "" A url of your webhook to get recent sales
        },
        "On_Buy": {
            "Enabled": false, This webhook will be send when someone buys any of your limited
            "Url": "" A url of your webhook to get recent buys
        },
        "User_To_Ping": 0 A user ID of of the user who will get mentioned (0 to not get pings)
    },
    "Under_Cut": {
        "Type": "robux", If you have this "robux" the LRP of the limited will dicrease by a robux, if "percent" will discrease by percent
        "Value": 1 Amount of how much limited LRP should go (0 to sell for the same price)
    },
    "Auto_Sell": {
        "Ask_Before_Sell": true, If you have this enabled, tool will sell everything by itself
        "Hide_OnSale": {
            "Enabled": false, [NOT WORKING YET] If you will try to sell item which is already on sale when you have this option enabled, it will be ignored
            "Save_Items": false If you have this enabled all the items that you "sold" or "skiped" an ID of this item will be saved in items/seen.json file and will be ingored next time
        },
        "Keep_Serials": 0, Any item serial which will be under this number will be skipped (0 to include all)
        "Keep_Copy": 0 [NOT WORKING YET] Any item which amount of dublicates will be under this number will be skipped (0 to include all)
    }
}
```

<details>
<summary><strong>How to get roblox cookie (click to expand)</strong></summary>

#### Open a [roblox](https://www.roblox.com/home) in browser and press `ctrl + shift + i` (`command + option + i` in mac OS)

#### Go to `Application` tab

![image](https://github.com/user-attachments/assets/d4f85137-7d19-447f-91a4-0e87195934ae)

#### Click `https://www.roblox.com` in `Cookies` tab

![image](https://github.com/user-attachments/assets/a35ae91c-38c1-4ec6-8212-cfa4432b3876)

#### Copy a value of `.ROBLOSECURITY` cookie

![image](https://github.com/user-attachments/assets/9bb77223-d34f-4ba0-9c5f-60f1bb11ffe7)

</details>

<details>
<summary><strong>How to get application's token</strong></summary>

    
#### Create a new [application](https://discord.com/developers/applications)

![image](https://github.com/user-attachments/assets/85bb1cad-1ad8-4c1b-b723-b466613c16b8)

#### Enable these 3 intents

![image](https://github.com/user-attachments/assets/2cdcdd78-3f0c-4c64-9cc1-bbbd9f34ef36)

#### Click "Reset Token" button and enter your password

![image](https://github.com/user-attachments/assets/74df637a-957b-4d2e-8023-dba4b6d9ebbc)

#### Get the token by clicking "Copy" button

![image](https://github.com/user-attachments/assets/690264f4-2bad-4ab8-b57d-55ebffa2e571)

#### To invite your application, mark these sections and press "Copy" button below and paste it in your browser

![image](https://github.com/user-attachments/assets/b72d486e-27a0-4e45-aea5-6950665a74bb)
![image](https://github.com/user-attachments/assets/64a61427-ebfd-474e-99fa-eaf6439d190d)

</details>

### Preview

![image](https://github.com/user-attachments/assets/ce1872b6-96ac-4787-a2a6-4725d921d026)

### Help

Contanct me on discord for any quastions: [deadlysilence._](https://discord.com/channels/)
