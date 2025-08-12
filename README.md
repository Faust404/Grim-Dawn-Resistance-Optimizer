# Grim Dawn Resistance Helper
This tool helps you choose the optimal configuration of components and augments to maximize the resistances of your character in [Grim Dawn](https://www.grimdawn.com/).

### The tool can be accessed [here](https://gdhelper.hreddy.in/).

# Why Should I Use This Tool?
The tool is meant to help the players balance their resistances as they level through the campaign and into the endgame. Balancing resistances has always been an issue with the wealth of options available in the game and only exacerbated by the fact that we players swap out tons of gear as we level into the endgame.

The tool aims to maximize your resistances with the least amount of components and augments used.

##  Here are Some Neat Use Cases For the tool
- Already using components on some gear slots? No problem. Block them out in the calculator.
- Already using augments on some gear slots? No problem. Block them out in the calculator.
- You wish to overcap some resists? No problem. Change the target resistance values from the default 80 to whatever you like.
- You do not have enough standing with a specific faction? Adjust your standing with the filter so you will not see augments you cannot access.

# How to Use
1. Set your character level.
2. Select the weapon template:
    - One-Handed Melee-Caster Weapon + Shield
    - One-Handed Melee-Caster Weapon + Off-Hand
    - One-Handed Melee-Caster Weapon + One-Handed Melee-Caster Weapon
    - One-Handed Ranged Weapon + Off-Hand
    - One-Handed Ranged Weapon + One-Handed Ranged Weapon
    - Two-Handed Melee Weapon
    - Two-Handed Ranged Weapon
3. Enter the current resistances of your character.
4. Select which slots are unavailable for components.
5. Select which slots are unavailable for augments.
6. Select the target resistances needed for your character in the advanced tab.
7. Select your character's standing with various factions for better suggestions in the advanced tab.
8. Hit the "Run Optimization" button

## How to Add Other Languages
1. Use `web/static/js/web/example.js` as a template and translate it into your desired language.  
2. Provide the language pack from your game (if Grimtools already supports your language, you can skip this step).  
3. Submit an issue in [Issues](../../issues) and attach the above files.

# How to Self-Host
You can use this docker-compose.yml to pull the image and deploy the container
```
services:
  gd-helper:
    image: index.docker.io/himavanth19/gd-helper
    container_name: gd-helper
    ports:
      - "5000:5000"
    restart: always
```
You will be able to see the tool running on http://127.0.0.1:5000