# AbsBox 
a structured finance cashflow engine wrapper for structured credit professionals:

* transparency -> open source for both wrapper and backend engine, great variable inspection support.
* human readable waterfall -> no more coding/scripting, just *lists* and *maps* in Python !
* easy interaction with Python numeric libraries as well as databases/Excel to accomodate daily work.

[![PyPI version](https://badge.fury.io/py/absbox.svg)](https://badge.fury.io/py/absbox)
[![PyPI download](https://img.shields.io/pypi/dm/absbox)](https://img.shields.io/pypi/dm/absbox)

## installation

    pip install absbox

## Documentation
* English -> https://absbox-doc.readthedocs.io
* Chinese(inactive) -> https://absbox.readthedocs.io

## Goal
* Structuring
  * Easy way to create different pool assets/deal capital structures and waterfalls
  * User can tell how key variables(service fee/bond WAL/bond cashflow etc) changes in different structure of transactions.
* Investor
  * Given powerful modelling language to build cashflow model , user can price bonds of transaction with pool performance assumption

## What it does
* Provide building blocks to create cashflow models for ABS/MBS
* Adapt to multiple asset classes
    * Residential Mortgage / AdjustRateMortgage/ IO,PO,Balloon Mortgages / Auto Loans
    * Corp Loans
    * Consumer Credit
    * Lease (For CMBS)
    * Fix Asset (Solar Panel/Hotel)
    * Receivable
    * SRT/Siginificant Risk Transfer
    * Master Trust
* Features
  * Sensitivity Analysis on different scenarios or deal structures
    * sensitivity analysis on pool performance assumptions
    * sensitivity analysis on capital structures or any deal components
  * Bond Cashflow/Pool Cashflow Forecast, Pricing

## What it takes to master
* Python syntax, nice to have knowledge of functional programming ,or exposure to package `toolz`/`lenses`
* Patience & Persistence, but remember , there is a slack community and responsive support !

## Missing Features ? 

Raise issues or disucssion with the prospectus or spreadsheet how asset cashflow should be projected.


## Data flow

<img src="https://absbox-doc.readthedocs.io/en/latest/_images/Intergration.png" width="600" height="347"/>

## Data Privacy

User can have option to connect to a private calculation engine in his/her own environment

![Screenshot_2024-08-19_15-09-10](https://github.com/user-attachments/assets/d4d7d6da-db38-46bd-96ed-524c92c1aa27)


## Community & Support

* [Discussion](https://github.com/yellowbean/AbsBox/discussions)
* [Slack](https://absboxhastructure.slack.com)

## Misc
#### Proposed Rule regarding Asset-Backed Securities: File No. S7-08-10

