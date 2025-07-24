# Grim Dawn Resistance Helper
This tool helps you choose the optimal configuration of components and augments to maximize the resistances of your character in [Grim Dawn](https://www.grimdawn.com/).

# Why Should I Use This Tool?
The tool is meant to help the players balance their resistances as they level through the campaign and into the endgame. Balancing resistances has always been an issue with the wealth of options available in the game and only exacerbated by the fact that we players swap out tons of gear as we level into the endgame.

The tool aims to maximize your resistances with the least amount of components and augments used.

##  Here are Some Neat Use Cases For the tool
- Already using components on some gear slots? No problem. Block them out in the calculator.
- Already using augments on some gear slots? No problem. Block them out in the calculator.
- You do not have enough standing with a specific faction? Adjust your standing with the filter so you will not see augments you cannot access.

# How to Use
1. Set your character level
2. Select the Template 
    - One-Hand + Shield
    - One-Hand + Off-Hand
    - Ranged + Off-Hand
    - Two-Hand Weapon
3. Enter the current resistances of your character
4. Select which slots are unavailable for components
5. Select which slots are unavailable for augments
6. Hit the "Run Optimization" button

# How to Self-Host
Just a simple command
```
docker-compose up --build -d
```
You will be able to see the tool running on http://127.0.0.1:5000