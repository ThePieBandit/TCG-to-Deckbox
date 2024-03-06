import configparser
import csv
import json
import os
import os.path
import re
import sys
import time
import traceback
import urllib.parse
from csv import DictWriter, DictReader
from typing import TextIO

import requests

# Constants
MULTI_NAMES_FILE = "multiple_names.json"
BAB_FILE = "bab.json"
SCRYFALL_BASE_URL = "https://api.scryfall.com/cards/search?order=cmc&q="
# noinspection SpellCheckingInspection
SCRYFALL_DFC_URL = SCRYFALL_BASE_URL + "%28is%3Adoublesided%20OR%20is%3Asplit%20OR%20is%3Aadventure%29%20AND%20game" \
                                       "%3Apaper%20AND%20-is%3Atoken%20AND%20-set%3ACMB1%20AND%20-is%3Aextra "
# noinspection SpellCheckingInspection
SCRYFALL_BAB_URL = SCRYFALL_BASE_URL + "is%3Abab+AND+game%3Apaper"
DECKBOX_URL = "https://deckbox.org/mtg/"

SKIP_COLUMNS = [
    "Simple Name",
    "Set Code",
    "Rarity",
    "Product ID",
    "SKU",
    "Price",
    "Price Each",
]
OUTPUT_FILE = "deckbox_import.csv"

# Global Data
scryfall_data = {}
scryfall_bab_data = {}

# So as not to hammer scryfall with unnecessary requests, we check to see if our cached data is older than a week.
now = time.time()
last_week = now - 60 * 60 * 24 * 7


def get_path_prefix() -> str:
    """
    Returns the path where all files except the input csv are located. This includes the replacements.config, as well as
    the output deckbox_import.csv. This is a holdover from when this was packaged as an executable. In that, it needed
    a different variable to be told to look inside the bundled program. Now it will always return the current directory.
    :rtype: str
    :return: the current directory the script is run from.
    """
    prefix: str = os.path.abspath(".")
    return prefix


# Utility function to replace strings in the csv from the replacements.config file.
def replace_strings(dictionary, config_parser, replacement_section, column_name):
    if dictionary[column_name].lower() in config_parser[replacement_section].keys():
        dictionary[column_name] = config_parser[replacement_section][dictionary[column_name].lower()]


def scryfall_data_func(raw_data: dict):
    scryfall_data[raw_data["card_faces"][0]["name"]] = raw_data["name"]


def scryfall_bab_data_func(raw_data: dict):
    scryfall_bab_data[raw_data["name"]] = raw_data["set_name"]


# Queries scryfall to build a list of cards that have multiple names.
def fetch_scryfall_data(uri, mapper, page=1):
    print(
        "Begin: Download '%s', page %s of results" % (urllib.parse.unquote(uri), page)
    )
    try:
        with requests.get(uri) as scryfall_response:
            tmp_scryfall_data = scryfall_response.json()

            for x in tmp_scryfall_data["data"]:
                mapper(x)
            if "next_page" in tmp_scryfall_data:
                fetch_scryfall_data(tmp_scryfall_data["next_page"], mapper, page + 1)
    except requests.exceptions.JSONDecodeError:
        print("Exception: Was unable to download %s, page %s of results" % (uri, page))
        traceback.print_exc()


def load_scryfall_data(filename: str, query_url: str, mapper_function, data_dict: dict):
    try:
        file_last_updated: float = os.path.getmtime(filename)
        print(
            "%s last modified: %s"
            % (filename, time.ctime(file_last_updated))
        )

        # Refresh the multiple names file if it's a week old, else use the cached version
        if file_last_updated < last_week:
            print("File %s is stale - updating..." % filename)
            fetch_scryfall_data(query_url, mapper_function)
            with open(filename, "w") as file:
                json.dump(data_dict, file)
            print("Done!")
        else:
            print("Using existing %s file..." % filename)
            with open(filename) as file:
                data_dict.update(json.load(file))
            print("Done!")
    # If the file isn't found, create it
    except OSError:
        print("File %s not found - creating..." % filename)
        fetch_scryfall_data(query_url, mapper_function)
        with open(filename, "w") as file:
            json.dump(data_dict, file)
        print("Done!")


def process_row(row, writer, config_parser):
    skip_scryfall_names = False

    # Don't bother with columns that are going to be ignored
    skipped_column: str
    for skipped_column in SKIP_COLUMNS:
        row.pop(skipped_column, "")

    # Map the printing column to the Foil column
    if row["Foil"] == "Normal":
        row["Foil"] = ""

    # Map Card Condition
    replace_strings(row, config_parser, "CONDITIONS", "Condition")

    # Map Chinese Languages
    replace_strings(row, config_parser, "LANGUAGES", "Language")

    ####################################################################
    # Map Specific Card Conditions
    ####################################################################

    # For BFZ lands...there's no differentiator from the full arts and the non-full arts.
    row["Name"] = row["Name"].replace(" - Full Art", "")

    # War of the Spark Alternate Arts handled differently
    if "(JP Alternate Art)" in row["Name"] and row["Edition"] == "War of the Spark":
        row["Edition"] = "War of the Spark Japanese Alternate Art"
        row["Name"] = row["Name"].replace(" (JP Alternate Art)", "")

    if row["Name"] in scryfall_bab_data and row["Edition"] == "Buy-A-Box Promos":
        if "Promos" in scryfall_bab_data[row["Name"]]:
            row["Edition"] = "Media Inserts"
        else:
            row["Edition"] = scryfall_bab_data[row["Name"]]

    # Handle Mystery Booster Test Cards, the 2021 release differentiates by Edition
    # on deckbox, while tcg player differentiates by name appending '(No PW Symbol)'
    if (
            "(No PW Symbol)" in row["Name"]
            and row["Edition"] == "Mystery Booster: Convention Edition Exclusives"
    ):
        row["Edition"] = "Mystery Booster Playtest Cards 2021"

    ####################################################################
    # Handle General Card Conversions
    ####################################################################

    # TODO split collector number on -, TCGPlayer started prefixing list cards with a set code
    # TODO The List Reprints -> The List
    # TODO remove "- Thick Stock"

    # Remove all Parentheses at the end of cards
    row["Name"] = re.sub(r" \(.*\)", "", row["Name"])
    replace_strings(row, config_parser, "NAMES", "Name")

    # We need to do a little extra work on dual faced cards, because deckbox is inconsistent with whether it
    # refers to cards by both names or just the front face.
    if row["Name"] in scryfall_data:
        deckbox_request_url = DECKBOX_URL + urllib.parse.quote(
            scryfall_data[row["Name"]]
        )
        with requests.get(deckbox_request_url) as deckbox_response:

            # If we are not redirected to a new page, then we should only use the front face name
            deckbox_response_url_parts = urllib.parse.urlparse(deckbox_response.url)
            deckbox_response_url = deckbox_response_url_parts._replace(fragment="")._replace(query="").geturl()

            if deckbox_request_url == deckbox_response_url \
                    or deckbox_request_url.replace("//", "/") == deckbox_response_url.replace("//", "/"):
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
        if not skip_scryfall_names:
            row["Name"] = scryfall_data[row["Name"]]

    # Move commander from edition to the end
    if "Commander: " in row["Edition"]:
        row["Edition"] = re.sub(r"Commander: (.*)$", r"\1 Commander", row["Edition"])

    # Remove Universes Beyond modifier
    if "Universes Beyond: " in row["Edition"]:
        row["Edition"] = re.sub(r"Universes Beyond: ", "", row["Edition"])

    # remove weird symbols from card numbers
    row["Card Number"] = re.sub(r"[*★]", "", row["Card Number"])

    # move Promo Pack to the end if it's not in replacements.config (some old ones actually do have the prefix
    if "Promo Pack: " in row["Edition"] and not row["Edition"] in config_parser["EDITIONS"].keys():
        row["Edition"] = re.sub(r"Promo Pack: (.*)$", r"\1 Promo Pack", row["Edition"])

    # Map Specific Edition Names
    replace_strings(row, config_parser, "EDITIONS", "Edition")

    # write the converted output
    writer.writerow(row)


def validate_input_csv(tcg_csv_file: TextIO):
    try:
        csv.Sniffer().sniff(tcg_csv_file.read(4096), delimiters=",")
        tcg_csv_file.seek(0)
    except UnicodeDecodeError:
        print("The file passed does not appear to be a valid CSV file.")
        sys.exit()


def convert():
    load_scryfall_data(MULTI_NAMES_FILE, SCRYFALL_DFC_URL, scryfall_data_func, scryfall_data)
    load_scryfall_data(BAB_FILE, SCRYFALL_BAB_URL, scryfall_bab_data_func, scryfall_bab_data)

    # Get our input
    input_file = sys.argv[1]

    config_parser = configparser.ConfigParser(delimiters="=")
    config_parser.read(os.path.join(get_path_prefix(), "replacements.config"))

    with open(input_file, newline="") as tcg_csv_file, open(
            OUTPUT_FILE, "w", newline=""
    ) as deckbox_csv_file:
        tcg_csv_file: TextIO
        deckbox_csv_file: TextIO
        validate_input_csv(tcg_csv_file=tcg_csv_file)

        csvreader: DictReader = csv.DictReader(tcg_csv_file)

        # Adjust column names
        tcg_headers = csvreader.fieldnames
        for index, header in enumerate(tcg_headers):
            if header.lower() in config_parser["COLUMNS"].keys():
                tcg_headers[index] = config_parser["COLUMNS"][header.lower()]

        # Unnecessary Columns: Simple Name,Set Code,Printing,Rarity,Product ID,SKU,Price,Price Each.
        deckbox_headers: list[str] = [x for x in tcg_headers if x not in SKIP_COLUMNS]

        csvwriter: DictWriter = csv.DictWriter(
            deckbox_csv_file, quoting=csv.QUOTE_ALL, fieldnames=deckbox_headers
        )
        csvwriter.writeheader()
        csv_row: dict
        for csv_row in csvreader:
            process_row(row=csv_row, writer=csvwriter, config_parser=config_parser)
    # All Done!
    success_msg = "Your import file for deckbox.org is available here: %s" % os.path.abspath(
        OUTPUT_FILE
    )
    print(success_msg)


convert()
