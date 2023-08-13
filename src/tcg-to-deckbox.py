import sys
import csv
import time
import os
import os.path
import configparser
import re
from tkinter import filedialog
from tkinter import messagebox
import tkinter as tk
import requests
import urllib.parse
import ssl
import json
import traceback

# Constants
MULTI_NAMES_FILE = "multiple_names.json"
BAB_FILE = "bab.json"
SCRYFALL_BASE_URL = "https://api.scryfall.com/cards/search?order=cmc&q="
SCRYFALL_DFC_URL = SCRYFALL_BASE_URL + "%28is%3Adoublesided%20OR%20is%3Asplit%20OR%20is%3Aadventure%29%20AND%20game%3Apaper%20AND%20-is%3Atoken%20AND%20-set%3ACMB1%20AND%20-is%3Aextra"
SCRYFALL_BAB_URL = SCRYFALL_BASE_URL + "is%3Abab+AND+game%3Apaper"
DECKBOX_URL = "https://deckbox.org/mtg/"

# Global Data
scryfall_data = {}
scryfall_bab_data = {}

# Global replacement helpers
ixalan_bab = [
    "Legion's Landing",
    "Search for Azcanta",
    "Arguel's Blood Fast",
    "Vance's Blasting Cannons",
    "Growing Rites of Itlimoc",
    "Conqueror's Galleon",
    "Dowsing Dagger",
    "Primal Amulet",
    "Thaumatic Compass",
    "Treasure Map",
]

bab_mapping = {
    "Impervious Greatwurm": "Guilds of Ravnica",
    "Kenrith, the Returned King": "Throne of Eldraine",
    "Realmwalker": "Kaldheim",
    "Vorpal Sword": "Adventures in the Forgotten Realms",
}

# Get rid of the root TK window, we don't need it.
root = tk.Tk()
root.withdraw()

# Queries scryfall to build a list of cards that have multiple names.
def fetch_multiple_names(uri, page=1):
    print(
        "Begin: Download '%s', page %s of results" % (urllib.parse.unquote(uri), page)
    )
    try:
        with requests.get(uri) as scryfall_response:
            tmp_scryfall_data = scryfall_response.json()

            for x in tmp_scryfall_data["data"]:
                scryfall_data[x["card_faces"][0]["name"]] = x["name"]
            if "next_page" in tmp_scryfall_data:
                fetch_multiple_names(tmp_scryfall_data["next_page"], page + 1)
    except Exception:
        print("Exception: Was unable to download %s, page %s of results" % (uri, page))
        print(str(Exception))        
        
# Queries scryfall to build a list of cards that were buy a box promos.
def fetch_bab_names(uri, page=1):
    print(
        "Begin: Download '%s', page %s of results" % (urllib.parse.unquote(uri), page)
    )
    try:
        with requests.get(uri) as scryfall_response:
            tmp_scryfall_data = scryfall_response.json()

            for x in tmp_scryfall_data["data"]:
                scryfall_bab_data[x["name"]] = x["set_name"]
            if "next_page" in tmp_scryfall_data:
                fetch_bab_names(tmp_scryfall_data["next_page"], page + 1)
    except Exception:
        print("Exception: Was unable to download %s, page %s of results" % (uri, page))
        traceback.print_exc()
        
# Utility function to replace strings in the csv from the replacements.config file.
def replace_strings(dict, replacementSection, columnName):
    if dict[columnName].lower() in configParser[replacementSection].keys():
        dict[columnName] = configParser[replacementSection][dict[columnName].lower()]


# Utility function to handle differences in lookup path if there's a UI involved.
def getPathPrefix():
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        prefix = sys._MEIPASS
    except Exception:
        # else, use current directory
        prefix = os.path.abspath(".")
    return prefix


# Check to see if we have DFC/Split/etc card names from scryfall and if it is up to date
try:
    multi_names_file_last_updated = os.path.getmtime(MULTI_NAMES_FILE)
    print(
        "%s last modified: %s"
        % (MULTI_NAMES_FILE, time.ctime(multi_names_file_last_updated))
    )
    now = time.time()
    last_week = now - 60 * 60 * 24 * 7

    # Refresh the multiple names file if it's a week old, else use the cached version
    if multi_names_file_last_updated < last_week:
        print("File %s is stale - updating..." % (MULTI_NAMES_FILE))
        fetch_multiple_names(SCRYFALL_DFC_URL)
        with open(MULTI_NAMES_FILE, "w") as multiple_names:
            json.dump(scryfall_data, multiple_names)
        print("Done!")
    else:
        print("Using existing %s file..." % MULTI_NAMES_FILE)
        with open(MULTI_NAMES_FILE) as multiple_names:
            scryfall_data = json.load(multiple_names)
        print("Done!")
# If the file isn't found, create it
except Exception:
    print("File %s not found - creating..." % (MULTI_NAMES_FILE))
    fetch_multiple_names(SCRYFALL_DFC_URL)
    with open(MULTI_NAMES_FILE, "w") as multiple_names:
        json.dump(scryfall_data, multiple_names)
    print("Done!")


# Check to see if we have Buy a Box card names from scryfall and if it is up to date
try:
    bab_file_last_updated = os.path.getmtime(BAB_FILE)
    print(
        "%s last modified: %s"
        % (BAB_FILE, time.ctime(bab_file_last_updated))
    )
    now = time.time()
    last_week = now - 60 * 60 * 24 * 7

    # Refresh the multiple names file if it's a week old, else use the cached version
    if bab_file_last_updated < last_week:
        print("File %s is stale - updating..." % (BAB_FILE))
        fetch_bab_names(SCRYFALL_BAB_URL)
        with open(BAB_FILE, "w") as multiple_names:
            json.dump(scryfall_bab_data, multiple_names)
        print("Done!")
    else:
        print("Using existing %s file..." % BAB_FILE)
        with open(BAB_FILE) as multiple_names:
            scryfall_bab_data = json.load(multiple_names)
        print("Done!")
# If the file isn't found, create it
except Exception:
    print("File %s not found - creating..." % (BAB_FILE))
    fetch_bab_names(SCRYFALL_BAB_URL)
    with open(BAB_FILE, "w") as multiple_names:
        json.dump(scryfall_bab_data, multiple_names)
    print("Done!")


# Get our input
GUI = False
if len(sys.argv) < 2:
    GUI = True
    FILE = filedialog.askopenfilename(
        title="Select your TCGPlayer app export file",
        filetypes=[("TCGPlayer exports", ".csv"), ("All files", "*.*")],
    )
    if len(FILE) == 0:
        messagebox.showerror(
            title="Input file not provided",
            message="You must pass the TCGPlayer csv export file to this program.",
        )
        sys.exit()
else:
    FILE = sys.argv[1]

skipcolumns = [
    "Simple Name",
    "Set Code",
    "Rarity",
    "Product ID",
    "SKU",
    "Price",
    "Price Each",
]
outputFile = "deckbox_import.csv"

configParser = configparser.ConfigParser(delimiters="=")
configParser.read(os.path.join(getPathPrefix(), "replacements.config"))

with open(FILE, newline="") as tcgcsvfile, open(
    outputFile, "w", newline=""
) as deckboxcsvfile:

    try:
        csv.Sniffer().sniff(tcgcsvfile.read(4096), delimiters=",")
        tcgcsvfile.seek(0)
    except:
        if GUI:
            messagebox.showerror(
                title="Invalid input file",
                message="The file selected does not appear to be a valid CSV file.",
            )
        else:
            print("The file passed does not appear to be a valid CSV file.")
        sys.exit()

    csvreader = csv.DictReader(tcgcsvfile)

    # Adjust column names
    headerstcg = csvreader.fieldnames
    for index, header in enumerate(headerstcg):
        if header.lower() in configParser["COLUMNS"].keys():
            headerstcg[index] = configParser["COLUMNS"][header.lower()]

    # Unnecessary Columns: Simple Name,Set Code,Printing,Rarity,Product ID,SKU,Price,Price Each.
    headersdeckbox = [x for x in headerstcg if x not in skipcolumns]

    csvwriter = csv.DictWriter(
        deckboxcsvfile, quoting=csv.QUOTE_ALL, fieldnames=headersdeckbox
    )
    csvwriter.writeheader()
    for row in csvreader:
        skip_scryfall_names = False

        # Don't bother with columns that are going to be ignored anyways
        for skippable in skipcolumns:
            row.pop(skippable, "")

        # Map the printing column to the Foil column
        if row["Foil"] == "Normal":
            row["Foil"] = ""

        # Map Card Condition
        replace_strings(row, "CONDITIONS", "Condition")

        # Map Chinese Languages
        replace_strings(row, "LANGUAGES", "Language")

        ####################################################################
        # Map Specific Card Conditions
        ####################################################################

        # For BFZ lands...there's no differentiator from the full arts and the non full arts.
        row["Name"] = row["Name"].replace(" - Full Art", "")
        
        # War of the Spark Alternate Arts handled differently
        if "(JP Alternate Art)" in row["Name"] and row["Edition"] == "War of the Spark":
            row["Edition"] = "War of the Spark Japanese Alternate Art"
            row["Name"] = row["Name"].replace(" (JP Alternate Art)", "")

        # Buy a Box Promos worked a little differently with Ixalan
        if row["Name"] in ixalan_bab and row["Edition"] == "Buy-A-Box Promos":
            row["Edition"] = "Black Friday Treasure Chest Promos"
            skip_scryfall_names = True
            
        # TODO Merge this with above
        if row["Name"] in scryfall_bab_data and row["Edition"] == "Buy-A-Box Promos":
            if "Promos" in scryfall_bab_data[row["Name"]]:
                row["Edition"] = "Media Inserts"
            else:
                row["Edition"] = scryfall_bab_data[row["Name"]]

        # Handle Mystery Booster Test Cards, the 2021 release differentiates by Edition
        # on deckbox, while tcgplayer differentiates by name appending '(No PW Symbol)'
        if (
            "(No PW Symbol)" in row["Name"]
            and row["Edition"] == "Mystery Booster: Convention Edition Exclusives"
        ):
            row["Edition"] = "Mystery Booster Playtest Cards 2021"

        ####################################################################
        # Handle General Card Conversions
        ####################################################################

        # Remove all Parentheses at the end of cards
        row["Name"] = re.sub(r" \(.*\)", "", row["Name"])
        replace_strings(row, "NAMES", "Name")
        
        # We need to do a little extra work on dual faced cards, because deckbox is inconsistent with whether it refers to cards by both names or just the front face.
        if row["Name"] in scryfall_data:
            deckbox_request_url = DECKBOX_URL + urllib.parse.quote(
                scryfall_data[row["Name"]]
            )
            with requests.get(deckbox_request_url) as deckbox_response:

                # If we are not redirected to a new page, then we should only use the front face name
                deckbox_response_url_parts = urllib.parse.urlparse(deckbox_response.url)
                deckbox_response_url = deckbox_response_url_parts._replace(fragment="")._replace(query="").geturl()
                
                if deckbox_request_url == deckbox_response_url or deckbox_request_url.replace("//", "/") == deckbox_response_url.replace("//", "/"):
                    print(
                        "Dual name for '%s' found on deckbox, the dual name will be used for the import."
                        % (scryfall_data[row["Name"]])
                    )
                else:
                    print(
                        "Dual name not found for '%s' on deckbox, front face name '%s' will be used."
                        % (scryfall_data[row["Name"]], row["Name"])
                    )
                    skip_scryfall_names = True
            if skip_scryfall_names == False:
                row["Name"] = scryfall_data[row["Name"]]
                
        # Fix edition for Buy-A-Box Promos
        if row["Name"] in bab_mapping and row["Edition"] == "Buy-A-Box Promos":
            row["Edition"] = bab_mapping[row["Name"]]
            
        # Move commander from edition to the end
        if "Commander: " in row["Edition"]:
            row["Edition"] = re.sub(r"Commander: (.*)$", r"\1 Commander", row["Edition"])
        
        # Remove Universes Beyond modifier
        if "Universes Beyond: " in row["Edition"]:
            row["Edition"] = re.sub(r"Universes Beyond: ", "", row["Edition"])

        # remove weird symbols from card numbers
        row["Card Number"] = re.sub(r"[*★]", "", row["Card Number"])
        
        # move Promo Pack to the end if it's not in replacements.config (some old ones actually do have the prefix
        if "Promo Pack: " in row["Edition"] and not row["Edition"] in configParser["EDITONS"].keys():
            row["Edition"] = re.sub(r"Promo Pack: (.*)$", r"\1 Promo Pack", row["Edition"])   

        # Map Specific Edition Names
        replace_strings(row, "EDITONS", "Edition")     

        # write the converted output
        csvwriter.writerow(row)

# All Done!
successMsg = "Your import file for deckbox.org is available here: %s" % os.path.abspath(
    outputFile
)
if GUI:
    messagebox.showinfo(title="Conversion completed successfully!", message=successMsg)
else:
    print(successMsg)
