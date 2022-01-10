# TCG-to-Deckbox
Python script to convert TCGPlayer app's export file into the proper format for deckbox.org's import. Tested with python 3.6.9

## Why this is useful

https://deckbox.org/ is a popular tool for cataloging one's [Magic: the Gathering](https://magic.wizards.com/en) collection. Card entry can be tedious, which is why many users are turning to scanning apps, such as [TCGplayer's card scanning app](https://app.tcgplayer.com/). However, the export format of TCGplayer's app is incompatible with deckbox.org's import format. This tool is designed to reformat the TCGplayer csv export into a valid deckbox csv import.

## How to use.

The script has two modes: CLI and GUI. To use the CLI, provide the path to your TCGplayer csv file:

    python3 tcg-to-deckbox.py ~/bin/sample_input.csv

To start it in GUI mode, just launch the program without any arguments

    python3 tcg-to-deckbox.py

In both cases, it will give you a new csv, named `deckbox_import.csv` in the directory from which the script was run.

## Limitations

1. Card names - I found some card names that are just formatted differently between the two. I manually adjust these card names in my replacements file, however, this was limited to the cards I hit. Of particular note were the Throne of Eldraine Adventure cards, which only used the Creature's name. Another oddity was Tamiyo's journal, which could have different flavor text. If you hit any of these in your collection, you don't need to be a programmer to fix it, just add another entry in `src/replacements.config` and rerun the script. Be sure to let me know so I can add it here too!

2. Showcase and extended art cards - TCGplayer suffixes these with `(Extended Art)` or `(Showcase)`. If the script finds these terms, it just deletes them. They're unnecessary as they have different collector's numbers.

3. Odd sets from Magic's history - I did my best here, but some of the older sets didn't quite line up. Some I just didn't have enough information on, some looked like categories of multiple sets, and some actually look like they map to multiple different sets in deckbox. If you hit some of these, manual correction is probably the best bet for now, but if you have a solution, feel free to share!

## Contributing
When making pull requests please format Python code using Black [black](https://github.com/psf/black)

```sh
# installing black
pip install black
```

```sh
# running black
black tcg-to-deckbox.py
```
