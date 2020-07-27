import sys
import csv
import configparser

def replace_strings(dict, replacementSection, columnName):
    if dict[columnName].lower() in configParser[replacementSection].keys():
        dict[columnName]=configParser[replacementSection][dict[columnName].lower()]

if len(sys.argv) < 2:
    print('You must pass the csv export file to this program.')
    sys.exit()

FILE=sys.argv[1]

skipcolumns=['Simple Name','Set Code','Rarity','Product ID','SKU','Price','Price Each']


configParser = configparser.ConfigParser(delimiters='=')
configParser.read('replacements.config')

with open(FILE, newline='') as tcgcsvfile,open('deckbox_import.csv', 'w', newline='') as deckboxcsvfile:
    csvreader = csv.DictReader(tcgcsvfile)
    # Adjust column names
    headerstcg = csvreader.fieldnames
    for index, header in enumerate(headerstcg):
        if header.lower() in configParser['COLUMNS'].keys():
            headerstcg[index]=configParser['COLUMNS'][header.lower()]

    # Unnecessary Columns: Simple Name,Set Code,Printing,Rarity,Product ID,SKU,Price,Price Each.
    headersdeckbox=[x for x in headerstcg if x not in skipcolumns]

    csvwriter  = csv.DictWriter(deckboxcsvfile, quoting=csv.QUOTE_ALL, fieldnames=headersdeckbox)
    csvwriter.writeheader()
    for row in csvreader:
        # Don't bother with columns that are going to be ignored anyways
        for skippable in skipcolumns:
            row.pop(skippable)

        # Map the printing column to the Foil column
        if row['Foil'] == 'Normal':
            row['Foil']=''

        # Map Card Condition
        replace_strings(row, 'CONDITIONS', 'Condition')

        # Map Chinese Languages
        replace_strings(row, 'LANGUAGES', 'Language')

        # Map Specific Card Names, and drop extras in parenthesis
        row['Name']=row['Name'].replace(" (Extended Art)","")
        row['Name']=row['Name'].replace(" (Showcase)","")
        replace_strings(row, 'NAMES', 'Name')

        # Map Specific Edition Names
        replace_strings(row, 'EDITONS', 'Edition')

        # write the converted output
        csvwriter.writerow(row)
