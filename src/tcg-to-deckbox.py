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
import ssl
import json


# Constants
MULTI_NAMES_FILE = "multiple_names.json"
SCRYFALL_URL = "https://api.scryfall.com/cards/search?order=cmc&q=%28is%3Adoublesided%20OR%20is%3Asplit%20OR%20is%3Aadventure%29%20%20AND%20game%3Apaper%20AND%20-is%3Atoken%20AND%20-set%3ACMB1"

#global vars
scryfall_data = {}


# Get rid of the root TK window, we don't need it.
root = tk.Tk()
root.withdraw()


def fetch_multiple_names(uri, page=1):
    print('Begin: Download %s, page %s of results' % (uri, page))
    try:
        with requests.get(uri) as response:
            tmp_scryfall_data = response.json()

            for x in tmp_scryfall_data["data"]:
                scryfall_data[x["card_faces"][0]["name"]] = x["name"]
            if "next_page" in tmp_scryfall_data:
                fetch_multiple_names(tmp_scryfall_data["next_page"], page + 1)
    except Exception:
        print('Exception: Was unable to download %s, page %s of results' % (uri, page))
        print(Exception)

# Utility function to replace strings in the csv from the replacements.config file.


def replace_strings(dict, replacementSection, columnName):
    if dict[columnName].lower() in configParser[replacementSection].keys():
        dict[columnName] = configParser[replacementSection][dict[columnName].lower()]


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
    multi_files_last_updated = os.path.getmtime(MULTI_NAMES_FILE)
    print("%s last modified: %s" %
          (MULTI_NAMES_FILE, time.ctime(multi_files_last_updated)))
    now = time.time()
    last_week = now - 60*60*24*7
    if multi_files_last_updated < last_week:
        print("File %s is stale - updating..." % (MULTI_NAMES_FILE))
        fetch_multiple_names(SCRYFALL_URL)
        with open(MULTI_NAMES_FILE, 'w') as multiple_names:
            json.dump(scryfall_data, multiple_names)
        print("Done!")
    else:
        print("Using existing %s file..." % MULTI_NAMES_FILE)
        with open(MULTI_NAMES_FILE) as multiple_names:
            scryfall_data = json.load(multiple_names)
        print("Done!")

except Exception:
    print("File %s not found - creating..." % (MULTI_NAMES_FILE))
    fetch_multiple_names(SCRYFALL_URL)
    with open(MULTI_NAMES_FILE, 'w') as multiple_names:
        json.dump(scryfall_data, multiple_names)
    print("Done!")


# Get our input
GUI = False
if len(sys.argv) < 2:
    GUI = True
    FILE = filedialog.askopenfilename(title="Select your TCGPlayer app export file", filetypes=[
        ("TCGPlayer exports", ".csv"), ("All files", "*.*")])
    if len(FILE) == 0:
        messagebox.showerror(title="Input file not provided",
                             message="You must pass the TCGPlayer csv export file to this program.")
        sys.exit()
else:
    FILE = sys.argv[1]

skipcolumns = ["Simple Name", "Set Code", "Rarity",
               "Product ID", "SKU", "Price", "Price Each"]
outputFile = "deckbox_import.csv"

configParser = configparser.ConfigParser(delimiters="=")
configParser.read(os.path.join(getPathPrefix(), "replacements.config"))

with open(FILE, newline="") as tcgcsvfile, open(outputFile, "w", newline="") as deckboxcsvfile:

    try:
        csv.Sniffer().sniff(tcgcsvfile.read(4096), delimiters=",")
        tcgcsvfile.seek(0)
    except:
        if GUI:
            messagebox.showerror(
                title="Invalid input file", message="The file selected does not appear to be a valid CSV file.")
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
        deckboxcsvfile, quoting=csv.QUOTE_ALL, fieldnames=headersdeckbox)
    csvwriter.writeheader()
    for row in csvreader:
        # Don't bother with columns that are going to be ignored anyways
        for skippable in skipcolumns:
            row.pop(skippable, '')

        # Map the printing column to the Foil column
        if row["Foil"] == "Normal":
            row["Foil"] = ""

        # Map Card Condition
        replace_strings(row, "CONDITIONS", "Condition")

        # Map Chinese Languages
        replace_strings(row, "LANGUAGES", "Language")

        # Map Specific Card Names, and drop extra tidbits
        row["Name"] = row["Name"].replace(" (Alternate Art)", "")
        row["Name"] = row["Name"].replace(" (Extended Art)", "")
        row["Name"] = row["Name"].replace(" (Showcase)", "")
        row["Name"] = row["Name"].replace(" (Borderless)", "")
        row["Name"] = row["Name"].replace(" (Stained Glass)", "")
        row["Name"] = row["Name"].replace(" (Etched Foil)", "")
        # For BFZ lands...there's no differentiator from the full arts and the non full arts.
        row["Name"] = row["Name"].replace(" - Full Art", "")

        # Very specifc conditons
        if "(JP Alternate Art)" in row["Name"] and row["Edition"] == "War of the Spark":
            row["Edition"] = "War of the Spark Japanese Alternate Art"
            row["Name"] = row["Name"].replace(" (JP Alternate Art)", "")

        # Remove numbers, mostly for lands, but for some other special cases (M21 Teferi)
        row["Name"] = re.sub(r" \(\d+\)", "", row["Name"])
        replace_strings(row, "NAMES", "Name")
        if row["Name"] in scryfall_data:
            row["Name"] = scryfall_data[row["Name"]]

        # remove weird symbols from card numbers
        row["Card Number"] = re.sub(r"[*★]", "", row["Card Number"])

        # Map Specific Edition Names
        replace_strings(row, "EDITONS", "Edition")

        # write the converted output
        csvwriter.writerow(row)

# All Done!
successMsg = "Your import file for deckbox.org is available here: %s" % os.path.abspath(
    outputFile)
if GUI:
    messagebox.showinfo(
        title="Conversion completed successfully!", message=successMsg)
else:
    print(successMsg)
