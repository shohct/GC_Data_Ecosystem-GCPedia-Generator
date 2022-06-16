# !/usr/bin/env python3
from collections import namedtuple
from jinja2 import Environment, FileSystemLoader, select_autoescape
import pandas as pd
from urllib import parse
import argparse

# A namedtuple consists of ("Type", ["SubTypes", "Entity Name", "Url", "Short Description"])
Element = namedtuple("Element", ["subtype", "name", "url", "desc"])  # contains all needed info about each table entry

# List of Categories from Airtable
# Sub-categories are categories that are listed in Airtable
CATEGORIES = {
    "Communities": {"Committees", "Communities","Working Groups"},
    "Data Glossaries": {"Data Glossaries", "Other", "Top-20 Data terms"},
    "Learning Resources": {"Data Glossaries", "Documents", "Learning Resources", },
    "Organizations and Teams": {"Organizations", "Teams"},
    "Projects/Initiatives": {"Projects/Initiatives"},
    "Policy Instruments": {"Policy Instruments"},  
}


# Convert entries in the data frame into the "Element" type and return them as a list of "Elements"
def df_to_elem(group) -> list:

    # Nested Function / Helper function - creates an element as long as the url is not na
    def make_elem(r):
        url = r["URL"] if not pd.isna(r["URL"]) else None  # Add a url if the url field is not empty
        description = r["Description"] if not pd.isna(r["Description"]) else None
        element = Element(r["Sub-Type"], r["Entity Name"], url, description)
        return element  # Return an element with the name from dictionary and url

    list_elems = [make_elem(r) for _, r in group.iterrows()]
    
    return list_elems   # Return a list of elements from the dataframe


# Takes in given csv file and converts it to a dictionary containing necessary elements
def load_data(path) -> dict:
    # Initialize dataframe
    df = (
        pd.read_csv(path, usecols=["Label", "Type", "SubType", "URL", "Not4DERD", "Description"])  # read in columns from file
        .dropna(subset=["Label", "SubType", "Type"])  # Discard Columns with NA values at Entity full name or Type
        .reset_index(drop=True)  # Discard Airtable indexing
    )

    df = df[df.Not4DERD != "checked"]  # Discard entries that are Not4DERD
    df.drop("Not4DERD", axis=1, inplace=True)  # Remove column "Entity Full Name"
    # Clean names and remove unwanted chars
    df["Type"] = df["Type"].str.strip()
    df["Entity Name"] = df["Label"].str.strip()
    df["Sub-Type"] = df["SubType"].str.strip()
    df["Description"] = df["Description"].str.strip()
    df["Description"] = df["Description"].str.replace('\n', '')
    df["URL"] = df["URL"].str.strip()

    # Remove column "Entity Full Name" and column "Entity sub-type"
    df.drop("Label", axis=1, inplace=True)
    df.drop("SubType", axis=1, inplace=True)

    df.sort_values(by=['Type', 'Sub-Type', 'Entity Name'], inplace=True)  # Sort alphabetically by type, then sub-type, then name
    df.reset_index(drop=True, inplace=True)  # Reset dataframe indices
    
    # Use split & explode
    # df_long = (df.set_index(['Type', 'Description', 'URL', 'Entity Name'])
    #            .apply(lambda x: x.str.split(',').explode())
    #            .reset_index())
    
    new_rows = {"Type": [],  "URL": [], "Entity Name": [], "Sub-Type": [], "Description": []}  # Create dict entry with type, subtype, description, url, and entity name

    # Fix the issue that some items have more than none sub-type and should be listed twice
    for i, row in df.iterrows():  # Go through each row in the dataframe
        current = row["Sub-Type"]

        if isinstance(current, str):
            types = [t.strip() for t in current.split(",")]  # Get a copy of every type in current row

            for extra_type in types[1:]:  # Go through each type and add a new entry for each type
                new_rows["Type"].append(row["Type"])  # Add a new row with the Type, Sub-Type, Url, and Entity
                new_rows["URL"].append(row["URL"])
                new_rows["Entity Name"].append(row["Entity Name"])
                new_rows["Description"].append(row["Description"])
                new_rows["Sub-Type"].append(extra_type)

            df.iloc[i]["Sub-Type"] = types[0]  # Add to dataframe the index of the current entry

    # Combine old dataframe with newly generated one and reset indices
    df_long = pd.concat((df, pd.DataFrame.from_dict(new_rows))).reset_index(drop=True)

    df_long.sort_values(by=['Type', 'Sub-Type', 'Entity Name'], inplace=True)  # Sort alphabetically by type, then sub-type, then name
    df_long.reset_index(drop=True, inplace=True)  # Reset dataframe indices
    
    # Group each element in dataframe by Type and Sub-Type
    grouped_df = df_long.groupby(["Type"])

    # break down each entity into an element and create a dictionary of elements to use
    element_dictionary = {tpl[0]: df_to_elem(tpl[1]) for tpl in grouped_df}

    
    # Return a dictionary containing Elements from the original data frame
    return element_dictionary


# Given full dictionary data, recategorize and select on the CATEGORIES we need
def recategorize(data: dict) -> dict:

    out = {k: [] for k in CATEGORIES.keys()}  # Resulting placeholder dictionary
    for k, subcats in CATEGORIES.items():  # k = categories, subcats = sub elements of each category
        for subc in subcats:  # Go through each sub category
            if elems := data.get(subc):  # Extract from dictionary only categories and subcategories we want
                out[k] += elems  # Also renames category to what is specified in CATEGORIES

    return out  # Returns dictionary with shortened list of elements


# Replaces characters so items are usable by Jinja
def format_link_text(item) -> str:
    return item.replace("/", f"/{chr(0x200b)}")


# Puts urls into correct format for Jinja
def gen_url(item) -> str:
    if "/" in item:
        return f"#{item.replace('/', '.2F')}"
    return f"#{parse.quote(item.replace(' ', '_'), safe='')}"


#  Creates and initializes parser
def make_parser() -> argparse.ArgumentParser:

    # Create and describe the parser
    parser = argparse.ArgumentParser(
        description="Generate Wikitext source for the Data Resource Directory GCpedia page."
    )

    # Add argument to parser, FileType reader that encodes given csv file to 'utf-8'
    parser.add_argument(
        "input",
        nargs='?',
        type=argparse.FileType("r", encoding='utf-8'),
        help="Input file containing entity data.",
    )

    # Add argument to parser, FileType writer that will print the code to stdout by default
    # ** Might be more useful to default output to an HTML or txt file to be copies into GCPedia
    parser.add_argument(
        "-o",
        dest="output",
        type=argparse.FileType('w', encoding='UTF-8'),
        default="output_template.txt",
        help="Destination file to write to. Defaults to stdout.",
    )

    return parser


def main():

    # Read and categorize data
    args = make_parser().parse_args()  # Create parser to make I/O easier
    data = recategorize(load_data(args.input))  # Load data from csv Airtable file and extract necessary data

    # Incorporate Jinja2
    env = Environment(loader=FileSystemLoader("."), autoescape=select_autoescape())  # Create Jinja2 environment

    # Import data and clean it up for Jinja
    env.globals.update(format_link_text=format_link_text, gen_url=gen_url, data=data)

    template = env.get_template("drd_two_col.j2")  # Load the Jinja2 template with loader and return it

    # Print template to text file which can then be copied into GCPedia
    args.output.write(template.render())

    print("\nCompleted Successfully \n")


if __name__ == "__main__":
    main()
