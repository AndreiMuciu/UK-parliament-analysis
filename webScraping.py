import sys
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from datetime import datetime
from selenium.webdriver.remote.webelement import WebElement
import undetected_chromedriver as uc
import pandas as pd

# Verifică argumentele din linia de comandă
if len(sys.argv) < 4:
    print("Usage: python webScraping.py <HOUSE> <DATE FROM: YYYY-MM-DD> <DATE TO: YYYY-MM-DD>")
    sys.exit(1)

house = sys.argv[1].lower()
if house not in ['commons', 'lords']:
    print("Invalid house name. Please choose from: commons, lords.")
    sys.exit(1)

date_str_from = sys.argv[2]
date_str_to = sys.argv[3]

try:
    date_from = datetime.strptime(date_str_from, "%Y-%m-%d")
    date_to = datetime.strptime(date_str_to, "%Y-%m-%d")
except ValueError:
    print("Date must be in format YYYY-MM-DD")
    sys.exit(1)

# Setări pentru Chrome
options = uc.ChromeOptions()
options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0 Safari/537.36")
driver = uc.Chrome(options=options)

# Ascunde navigator.webdriver
driver.execute_cdp_cmd(
    "Page.addScriptToEvaluateOnNewDocument",
    {"source": "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"}
)

# Navigare la site
url = f"https://hansard.parliament.uk/"
print(f"Navigating to {url}")
driver.get(url)
time.sleep(3)

# Selectare camera (House)
houseToGo = driver.find_element(By.XPATH, f'//a[@href="/search/Debates?house={house}"]')
houseToGo.click()
time.sleep(5)

# Setare interval de dată
try:
    actions = driver.find_elements(By.CLASS_NAME, "actions")
    datepicker = driver.find_elements(By.CLASS_NAME, "datepicker")

    input_field = datepicker[0].find_element(By.TAG_NAME, "input")
    input_field.clear()
    input_field.send_keys(date_from.strftime("%d/%m/%Y"))
    input_field.send_keys(Keys.ENTER)

    input_field = datepicker[1].find_element(By.TAG_NAME, "input")
    input_field.clear()
    input_field.send_keys(date_to.strftime("%d/%m/%Y"))
    input_field.send_keys(Keys.ENTER)

    search_button = actions[1].find_element(By.CLASS_NAME, "btn-primary")
    search_button.click()
except Exception as e:
    print("Error setting date:", e)
    driver.quit()
    sys.exit(1)

time.sleep(5)

def get_direct_text(element: WebElement) -> str:
    return element.get_attribute("innerHTML").split('<')[0].strip()

def gender_from_name(name: str) -> str:
    male_titles = ["lord", "sir", "mr", "viscount", "duke", "earl", "baron", "prince", "king", "count", "baronet"]
    female_titles = ["lady", "ms", "mrs", "madame", "baroness", "duchess", "countess", "princess", "queen"]
    male_names = ["andrew", "james", "john", "robert", "michael", "david", "richard", "charles", "thomas", "daniel",
                  "george", "william", "joseph", "edward", "henry", "christopher", "anthony", "paul", "mark", "steven",
                  "kevin", "brian", "jason", "gary", "timothy", "jeffrey", "scott", "eric", "stephen", "larry", "justin"]
    female_names = ["sarah", "emma", "jessica", "emily", "samantha", "laura", "rebecca", "charlotte", "hannah",
                    "elizabeth", "victoria", "lucy", "alice", "grace", "lily", "sophie", "isabella", "mia", "olivia",
                    "ava", "sophia", "ella", "chloe", "amelia", "zoe"]

    first = name.split()[0].lower()
    second = name.split()[1].lower() if len(name.split()) > 1 else ""

    if first in male_titles or first in male_names or second in male_names:
        return "male"
    elif first in female_titles or first in female_names or second in female_names:
        return "female"
    elif second in male_titles:
        return "male"
    elif second in female_titles:
        return "female"
    else:
        return "unknown"
    
debate_links = []
while True:
    try:
        card_list = driver.find_element(By.CLASS_NAME, "card-list")
        links = card_list.find_elements(By.TAG_NAME, "a")
    except Exception as e:
        print("Error finding card list or links:", e)
        
    for link in links:
        href = link.get_attribute("href")
        if href:
            debate_links.append(href)
    next_page_anchors = driver.find_elements(By.XPATH, '//a[@title="Go to next page"]')
    if next_page_anchors:
        next_page_anchors[0].click()
        time.sleep(5)
    else:
        break


results = []
politicians = []

for i, debate_link in enumerate(debate_links):
    print(f"Processing debate {i + 1}/{len(debate_links)}: {debate_link}")
    driver.get(debate_link)
    time.sleep(3)
    try:
        contributions = driver.find_elements(By.CLASS_NAME, "debate-item-contributiondebateitem")
        if not contributions:
            print("No contributions found for this debate.")
            continue
        texts = []
        for contribution in contributions:
            try:
                content = contribution.find_element(By.CLASS_NAME, "content")
                if content: 
                    texts.append(content.text)
            except Exception as e:
                print("Error extracting contribution content:", e)
                continue
        title = driver.find_element(By.CLASS_NAME, "hero-banner").find_element(By.TAG_NAME, "h1").text
        date = driver.find_element(By.CLASS_NAME, "hero-banner").find_element(By.TAG_NAME, "h2").text.split(" on ")[1]
    except Exception as e:
        print("Error extracting title or date:", e)
        continue
    try:
        primary_content = driver.find_element(By.CLASS_NAME, "primary-content")
        politician_links = primary_content.find_elements(By.CLASS_NAME, "attributed-to-details")
        extracted_links = []
        for politician_link in politician_links:
            try:
                href = politician_link.get_attribute("href")
                if href:
                    extracted_links.append(href)
            except Exception as e:
                print("Error extracting politician link:", e)
                continue
        text = primary_content.text
    except Exception as e:
        print("Error extracting primary content:", e)
        continue

    try:
        results.append({
            "date": date,
            "title": title,
            "text": "\n".join(texts)
        })
    except Exception as e:
        print("Error extracting results for debate:", e)
    try:
        for i, extracted_link in enumerate(extracted_links):
            try:
                driver.get(extracted_link)
                time.sleep(2)
                card_member = driver.find_element(By.CLASS_NAME, "card-member")
                name = card_member.find_element(By.CLASS_NAME, "primary-info").text
                party = card_member.find_element(By.CLASS_NAME, "secondary-info").text
                sex = gender_from_name(name)
                politicians.append({
                    "name": name,
                    "party": party,
                    "sex": sex,
                    "contribution": texts[i]
                })
            except Exception as e:
                print(f"Error extracting politician {i + 1} info:", e)
                continue
    except Exception as e:
        print("Error extracting politicians:", e)

# Extrage dezbateri și politicieni
#try:
#    while True:
#        try:
#            card_list = driver.find_element(By.CLASS_NAME, "card-list")
#            card_inner = card_list.find_elements(By.CLASS_NAME, "card-inner")
#        except Exception as e:
#            print("Error finding card list or card inner elements:", e)
#            break
#
#        for card in card_inner:
#            try:
#                title = get_direct_text(card.find_element(By.CLASS_NAME, "primary-info"))
#                date = card.find_element(By.CLASS_NAME, "secondary-info").text
#                card.click()
#                time.sleep(3)
#            except Exception as e:
#                print("Error processing card (title/date/click):", e)
#                continue
#
#            try:
#                primary_content = driver.find_element(By.CLASS_NAME, "primary-content")
#                contributions = primary_content.find_elements(By.CLASS_NAME, "debate-item-contributiondebateitem")
#            except Exception as e:
#                print("Error finding primary content or contributions:", e)
#                driver.back()
#                time.sleep(3)
#                continue
#
#            text = ""
#            for contribution in contributions:
#                try:
#                    header = contribution.find_element(By.CLASS_NAME, "header")
#                    speaker = header.find_elements(By.CLASS_NAME, "attributed-to-details")
#
#                    if speaker:
#                        try:
#                            speaker[0].click()
#                            time.sleep(2)
#                            card_member = driver.find_element(By.CLASS_NAME, "card-member")
#                            name = card_member.find_element(By.CLASS_NAME, "primary-info").text
#                            sex = gender_from_name(name)
#                            party = card_member.find_element(By.CLASS_NAME, "secondary-info").text
#                            driver.back()
#                            time.sleep(2)
#                        except Exception as e:
#                            print("Error extracting speaker info:", e)
#                            driver.back()
#                            time.sleep(2)
#                            continue

#                    text_intermediate = contribution.find_element(By.CLASS_NAME, "content").text

#                    if speaker:
#                        politicians.append({
#                            "name": name,
#                            "party": party,
#                            "sex": sex,
#                            "contribution": text_intermediate
#                        })

#                    text += text_intermediate + "\n"

#                except Exception as e:
#                    print("Error processing a single contribution:", e)
#                    continue
#
#            if text != "":
#                results.append({
#                    "date": date,
#                    "title": title,
#                    "text": text
#                })

#            try:
#                driver.back()
#                time.sleep(3)
#            except Exception as e:
#                print("Error going back after processing debate:", e)
#                break
#
#        try:
#            next_page_anchors = driver.find_elements(By.XPATH, '//a[@title="Go to next page"]')
#            if next_page_anchors:
#                next_page_anchors[0].click()
#                time.sleep(5)
#            else:
#                break
#        except Exception as e:
#            print("Error going to next page:", e)
#            break

#except Exception as e:
#    print("Error extracting debates and politicians:", e)

# Salvare date
df = pd.DataFrame(results)
df_politicians = pd.DataFrame(politicians)

print(df.head())
print(df_politicians)

driver.quit()

df.to_csv("debates.csv", index=False)
df_politicians.to_csv("politicians.csv", index=False)
