# AutoSeller
### A #1 roblox tool to sell UGC Limiteds

# Setup
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
        "OnSale": {
            "Enabled": false, This webhook will be send when you will send any item through this tool
            "Url": "" A url of your webhook to get things that you put one sale
        },
        "OnBuy": {
            "Enabled": false, This webhook will be send once someone buys your item
            "Url": "" A url of your webhook to get known once someone buys your item
        },
        "User_To_Ping": 0 A user ID of of the user who will get mentioned (0 to not get pings)
    },
    "Auto_Sell": {
        "Ask_Before_Sell": true, If you have this enabled, tool will ask you each item to sell
        "Save_Progress": true, If you have this enabled all the items that you "sold" or "skiped" an ID of this item will be saved in items/seen.json file and ingored next time you open program
        "Hide_OnSale": false, If you will try to sell item which is already on sale when you have this option enabled, it will be ignored
        "Skip_If_Cheapest": false, If you have this enabled and item that you are selling is already the lowest in resale it will be skipped
        "Keep_Serials": 0, Any item serial which will be under this number will be skipped (0 to include all)
        "Keep_Copy": 0 Any item which amount of dublicates will be under this number will be skipped (0 to include all)
        "Under_Cut": {
            "Type": "percent", If you have this set at "robux" the LRP of the limited will dicrease by a robux, if "percent" will decrease by percent
            "Value": 5 Amount of how much limited LRP should decrease (0 to sell for the same price)
        }
    }
}
```

# Preview
![image](https://github.com/user-attachments/assets/eeaa7337-bf2d-4fcd-a2ac-5502549599f3)

# Help
Contact me on discord for any questions or ideas: [deadlysilence._](https://discord.com/channels/)
