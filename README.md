# Data Resource Directory (DERD) GCPedia Page Generator

This repository contains the Python script and Jinja2 template used to generate the Data Resource
Directory's GCPedia page.

```
usage: gen_drd.py [-h] [-o OUTPUT] input

Generate Wikitext source for the Data Resource Directory GCpedia page.

positional arguments:
  input       Input file containing entity data.

optional arguments:
  -h, --help  show this help message and exit
  -o OUTPUT   Destination file to write to. Defaults to txt file.

Required in folder: file containing translations from French to English for French version of DERD.

```

Notes: 
- Entry containing link to Password Guidance doc will crash the site update if left in list of entries for the English DERD page. Remove entry before updating GCpedia page.

