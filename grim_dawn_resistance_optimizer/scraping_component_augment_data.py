import re

import pandas as pd
from bs4 import BeautifulSoup
from icecream import ic
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

# Setup Chrome options for headless browsing (optional)
chrome_options = Options()
chrome_options.add_argument("--headless")

# Make sure you have chromedriver installed and is in your PATH
driver = webdriver.Chrome(options=chrome_options)

component_df: pd.DataFrame = pd.DataFrame()
# category_to_scrape = "components"  # Change to "augments" if needed
category_to_scrape = "augments"  # Change to "augments" if needed

def convert_to_df(processed_item_info: dict) -> None:
    global component_df
    # Convert dict to DataFrame row and append
    component_df = pd.concat([component_df, pd.DataFrame([processed_item_info])], ignore_index=True)
    # ic(component_df.head())


def process_item_info(item_info_dict) -> None:
    # ic(item_info_dict)

    processed_item_info = {
        "Item": "",
        "ID": 0,
        "Rarity": "Common",
        "Required Player Level": 1,
        "Item Level": 1,
        "Fire Resistance": 0,
        "Cold Resistance": 0,
        "Lightning Resistance": 0,
        "Poison & Acid Resistance": 0,
        "Pierce Resistance": 0,
        "Bleeding Resistance": 0,
        "Vitality Resistance": 0,
        "Aether Resistance": 0,
        "Chaos Resistance": 0,
        'Helm': False,
        'Chest': False,
        'Shoulders': False,
        'Gloves': False,
        'Pants': False,
        'Boots': False,
        'Amulet': False,
        'Ring1': False,
        'Ring2': False,
        'Belt': False,
        'Medal': False,
        'One-Handed': False,
        'Two-Handed': False,
        'Off-Hand': False,
        'Shield': False,
        'Ranged': False,
    }

    # Keywords for each gear slot
    gear_keywords = {
        'Helm': ['all armor', 'head'],
        'Chest': ['all armor', 'chest'],
        'Shoulders': ['all armor', 'shoulder'],
        'Gloves': ['all armor', r'\bhand\b'],
        'Pants': ['all armor', 'leg'],
        'Boots': ['all armor', 'boots'],
        'Belt': ['all armor'],
        'Amulet': ['amulets'],
        'Ring1': ['rings'],
        'Ring2': ['rings'],
        'Medal': ['medals'],
        'One-Handed': ['all weapons', 'one-handed'],
        'Two-Handed': ['all weapons', 'two-handed'],
        'Off-Hand': ['all weapons', 'caster off-hands'],
        'Shield': ['all weapons', 'shields'],
        'Ranged': ['all weapons', 'guns', 'crossbows'],
    }

    # Copy over the basic item details 
    processed_item_info["Item"] = item_info_dict["Item"]
    processed_item_info["ID"] = item_info_dict["ID"]
    processed_item_info["Rarity"] = item_info_dict["Rarity"]
    processed_item_info["Required Player Level"] = item_info_dict["Required Player Level"]
    processed_item_info["Item Level"] = item_info_dict["Item Level"]

    if category_to_scrape == "augments":
        processed_item_info["Faction"] = item_info_dict["Faction"]

    # Extract resistance values from the item tooltips
    list_of_resistances = [key for key in processed_item_info.keys() if "Resistance" in key]
    list_of_resistances.append("Elemental Resistance")
    for tip in item_info_dict.get('Tooltip', []):
        for resistance in list_of_resistances:
            if resistance in tip:
                m = re.search(r'^(\d+)%\s*([A-Za-z &]+) Resistance', tip)
                if m:
                    value = int(m.group(1))
                    # Special rule for elemental resistance
                    if resistance == "Elemental Resistance":
                        processed_item_info["Fire Resistance"] = value
                        processed_item_info["Cold Resistance"] = value
                        processed_item_info["Lightning Resistance"] = value
                    else:
                        processed_item_info[resistance] = value
    
    # Extract appropriate gear that the item can be applied to
    item_desc = item_info_dict["Item Description"]
    start = item_desc.find('(')
    end = item_desc.find(')', start)
    gear_usage_str = item_desc[start+1:end]

    for gear, keywords in gear_keywords.items():
        if any(re.search(kw, gear_usage_str) for kw in keywords):
            processed_item_info[gear] = True

    # ic(processed_item_info)
    convert_to_df(processed_item_info)


def extract_info(item):

    item_info_dict = {
        "ID": "",
        "Item": "",
        "Item Description": "",
        "Item Level": 1,
        "Rarity": "",
        "Required Player Level": 1,
        "Tooltip": [],
    }

    # Extract the id and name of item
    req_div = item.select_one('.item-name')
    if req_div:
        item_info_dict["Item"] = req_div.text.strip()
        item_info_dict["ID"] = int(req_div.get('href').split("/")[-1])

    # Extract the item description
    req_div = item.select_one('.item-description-text')
    if req_div:
        item_info_dict["Item Description"] = req_div.text

    # Extract the rarity of the item
    req_div = item.select_one('.item-type')
    if req_div:
        rarity_str = req_div.text.strip()
        # This is necessary since common components aren't defined as common component, just component
        if len(rarity_str.split()) > 1:
            item_info_dict["Rarity"] = req_div.text.strip().split()[0]
        else:
            item_info_dict["Rarity"] = "Common"

    # Extract the item description
    if category_to_scrape == "augments":
        item_info_dict["Faction"] = "   "
        req_div = item.select_one('.faction-row')
        if req_div:
            faction_str = req_div.text.strip()
            item_info_dict["Faction"] = faction_str.split(':')[-1].strip()


    # Extract required player level and item level
    req_div = item.select_one('.item-req')
    if req_div:
        for div in req_div.find_all('div'):
            if "Required Player Level" in div.text:
                parts = div.text.split(':')
                if len(parts) == 2:
                    item_info_dict["Required Player Level"] = int(parts[1].strip())
            if "Item Level" in div.text:
                parts = div.text.split(':')
                if len(parts) == 2:
                    item_info_dict["Item Level"] = int(parts[1].strip())

    # Extract tooltip
    for block in item.select('.tooltip-skill-params.item-padded-v'):
        for div in block.find_all('div', recursive=False):
            # Collect plain text content, stripping sub-tags
            param_text = div.get_text(separator=' ', strip=True)
            # If an item grants resistances through active skills, we ignore those tooltips
            if 'Energy Cost' in param_text or 'Skill Recharge' in param_text:
                break
            item_info_dict["Tooltip"].append(param_text)
    
    # ic(item_info_dict)
    process_item_info(item_info_dict)


if __name__ == "__main__":
    # global component_df
    try:
        if category_to_scrape == "components":
            # Open the Grimtools Components page
            driver.get('https://www.grimtools.com/db/category/components/items')
        elif category_to_scrape == "augments":
            # Open the Grimtools Components page
            driver.get('https://www.grimtools.com/db/category/augments/items')

        # Wait until at least one component's name element is present (adjust timeout as needed)
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, '.item-list'))
        )

        # Now grab the fully rendered HTML
        html = driver.page_source

        # Parse with BeautifulSoup
        soup = BeautifulSoup(html, 'html.parser')
        item_list = soup.select_one('.item-list')
        for group in item_list.select('.item-list-group'):

            group_name = ".item-card.item-component" if category_to_scrape == "components" else ".item-card.item-enchant"
            
            for item in group.select(group_name):
                extract_info(item)
                # break

    finally:
        if category_to_scrape == "components":
            component_df.to_csv("data/component_data.csv", index=False)
        elif category_to_scrape == "augments":
            component_df.to_csv("data/augment_data.csv", index=False)
        driver.quit()
