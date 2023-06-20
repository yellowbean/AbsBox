# AbsBox 
a structured finance cashflow engine wrapper for structured credit professionals:

* transparency -> open source for both wrapper and backend engine
* human readable waterfall -> no more coding/scripting, just *lists* and *maps* in Python !
* easy interaction with Python numeric libraries as well as databases/Excel to accomodate daily work.


[![Python version](https://img.shields.io/pypi/pyversions/absbox)](https://img.shields.io/pypi/pyversions/absbox)
[![PyPI version](https://badge.fury.io/py/absbox.svg)](https://badge.fury.io/py/absbox)
[![PyPI download](https://img.shields.io/pypi/dm/absbox)](https://img.shields.io/pypi/dm/absbox)

## installation

    pip install absbox

## Community & Support

* [Discussion](https://github.com/yellowbean/AbsBox/discussions)

## What it does
* Provide building blocks to create cashflow models for ABS/MBS
* Adapt to multiple asset classes
    * Residential Mortgage / AdjustRateMortgage / Auto Loans
    * Corp Loans
    * Consumer Credit
    * Lease
* Features
  * Sensitivity Analysis on different scenarios or deal structures
    * sensitiviy analysis on pool performance assumptions
    * sensitiviy analysis on capital structures or any deal components
  * Bond Cashflow/Pool Cashflow Forecast, Pricing

## Goal
* Structuring
  * Given easy way to create different pool assets/deal capital structure and waterfall, user can tell how key variables(service fee/bond WAL/bond cashflow etc) changes in different structure of transaction.
* Investor
  * Given powerful modelling language to build cashflow model , user can make pricing on bonds of transaction already in the market or make pool performance assumption to perform pricing on the bonds in the portfolio..

## Data flow

<img src="https://absbox-doc.readthedocs.io/en/latest/_images/Intergration.png" width="600" height="347"/>

## Documentation
* English -> https://absbox-doc.readthedocs.io
* Chinese -> https://absbox.readthedocs.io
