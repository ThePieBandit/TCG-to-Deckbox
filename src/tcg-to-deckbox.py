import sys
import csv
import os
import configparser
import re
from tkinter import filedialog
from tkinter import messagebox
import tkinter as tk

# Get rid of the root TK window, we don't need it.
root = tk.Tk()
root.withdraw()

# Utility function to replace strings in the csv from the replacements.config file.
def replace_strings(dict, replacementSection, columnName):
    if dict[columnName].lower() in configParser[replacementSection].keys():
        dict[columnName]=configParser[replacementSection][dict[columnName].lower()]

def getPathPrefix():
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        prefix = sys._MEIPASS
    except Exception:
        # else, use current directory
        prefix = os.path.abspath(".")
    return prefix

def removePrefix( text, prefix ):
    if text.startswith( prefix ):
        return text[ len(prefix): ]
    return text

# Get our input
GUI=False
if len(sys.argv) < 2:
    GUI=True
    FILE=filedialog.askopenfilename(title="Select your TCGPlayer app export file",filetypes=[("TCGPlayer exports", ".csv"),("All files","*.*")])
    if len(FILE) == 0:
        messagebox.showerror(title="Input file not provided",message="You must pass the TCGPlayer csv export file to this program.")
        sys.exit()
else:
    FILE=sys.argv[1]

skipcolumns=["Simple Name","Set Code","Rarity","Product ID","SKU","Price","Price Each"]
outputFile="deckbox_import.csv"

configParser = configparser.ConfigParser(delimiters="=")
configParser.read(os.path.join(getPathPrefix(),"replacements.config"))

with open(FILE, newline="") as tcgcsvfile,open(outputFile, "w", newline="") as deckboxcsvfile:

    try:
        csv.Sniffer().sniff(tcgcsvfile.read(4096),delimiters=",")
        tcgcsvfile.seek(0)
    except:
        if GUI:
            messagebox.showerror(title="Invalid input file",message="The file selected does not appear to be a valid CSV file.")
        else:
            print("The file passed does not appear to be a valid CSV file.")
        sys.exit()

    csvreader = csv.DictReader(tcgcsvfile)

    # Adjust column names
    headerstcg = csvreader.fieldnames
    for index, header in enumerate(headerstcg):
        if header.lower() in configParser["COLUMNS"].keys():
            headerstcg[index]=configParser["COLUMNS"][header.lower()]

    # Unnecessary Columns: Simple Name,Set Code,Printing,Rarity,Product ID,SKU,Price,Price Each.
    headersdeckbox=[x for x in headerstcg if x not in skipcolumns]

    csvwriter  = csv.DictWriter(deckboxcsvfile, quoting=csv.QUOTE_ALL, fieldnames=headersdeckbox)
    csvwriter.writeheader()
    for row in csvreader:
        # Don't bother with columns that are going to be ignored anyways
        for skippable in skipcolumns:
            row.pop(skippable,'')

        # Map the printing column to the Foil column
        if row["Foil"] == "Normal":
            row["Foil"]=""

        # Map Card Condition
        replace_strings(row, "CONDITIONS", "Condition")

        # Map Chinese Languages
        replace_strings(row, "LANGUAGES", "Language")

        # Map Specific Card Names, and drop extra tidbits
        row["Name"]=row["Name"].replace(" (Alternate Art)","")
        row["Name"]=row["Name"].replace(" (Extended Art)","")
        row["Name"]=row["Name"].replace(" (Showcase)","")
        row["Name"]=row["Name"].replace(" (Borderless)","")
        #For BFZ lands...there's no differentiator from the full arts and the non full arts.
        row["Name"]=row["Name"].replace(" - Full Art","")

        #Very specifc conditons
        if "(JP Alternate Art)" in row["Name"] and row["Edition"] == "War of the Spark":
            row["Edition"] = "War of the Spark Japanese Alternate Art"
            row["Name"]=row["Name"].replace(" (JP Alternate Art)","")


        # Remove numbers, mostly for lands, but for some other special cases (M21 Teferi)
        row["Name"] = re.sub(r" \(\d+\)", "", row["Name"])
        replace_strings(row, "NAMES", "Name")

        # remove weird symbols from card numbers
        row["Card Number"] = re.sub(r"[*★]", "", row["Card Number"])

        # Map Specific Edition Names
        replace_strings(row, "EDITONS", "Edition")

        # Convert 'Commander: ' to append ' Commander' as a suffix
        if row["Edition"].startswith( "Commander: "):
            row["Edition"] = removePrefix( row["Edition"], "Commander: " );
            row["Edition"] = "".join( [row["Edition"], " Commander"] )

        # write the converted output
        csvwriter.writerow(row)

# All Done!
successMsg="Your import file for deckbox.org is available here: %s" % os.path.abspath(outputFile)
if GUI:
    messagebox.showinfo(title="Conversion completed successfully!", message=successMsg)
else:
    print(successMsg)
