# AbsBox 
a structured finance cashflow engine wrapper for structured credit professionals:

* transparency -> open source for both wrapper and backend engine.
* human readable waterfall -> no more coding/scripting, just *lists* and *maps* in Python !
* easy interaction with Python numeric libraries as well as databases/Excel to accomodate daily work.

[![PyPI version](https://badge.fury.io/py/absbox.svg)](https://badge.fury.io/py/absbox)
[![PyPI download](https://img.shields.io/pypi/dm/absbox)](https://img.shields.io/pypi/dm/absbox)

## installation

    pip install absbox

## Documentation
* English -> https://absbox-doc.readthedocs.io
* Chinese -> https://absbox.readthedocs.io

## Goal
* Structuring
  * Easy way to create different pool assets/deal capital structures and waterfalls
  * User can tell how key variables(service fee/bond WAL/bond cashflow etc) changes in different structure of transaction.
* Investor
  * Given powerful modeling language to build cashflow model , user can price bonds of transaction after setting pool performance assumption

## What it does
* Provide building blocks to create cashflow models for ABS/MBS
* Adapt to multiple asset classes
    * Residential Mortgage / AdjustRateMortgage / Auto Loans
    * Corp Loans
    * Consumer Credit
    * Lease
    * Fix Asset
* Features
  * Sensitivity Analysis on different scenarios or deal structures
    * sensitivity analysis on pool performance assumptions
    * sensitivity analysis on capital structures or any deal components
  * Bond Cashflow/Pool Cashflow Forecast, Pricing

## Data flow

<img src="https://absbox-doc.readthedocs.io/en/latest/_images/Intergration.png" width="600" height="347"/>


## Community & Support

* [Discussion](https://github.com/yellowbean/AbsBox/discussions)


## Misc
#### Proposed Rule regarding Asset-Backed Securities: File No. S7-08-10

