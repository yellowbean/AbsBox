Reference
=================

Slides & Videos
------------------------

Slides 
""""""""""

* Goolge Slide :

  *  `absbox 101 <https://docs.google.com/presentation/d/1mKJsClatZhm7UY-wzNGNgdYpy9D1niUgSJBYAw_7HOg/>`_
  *  `absbox 201 <https://docs.google.com/presentation/d/1k4gQ_9SQblPtlkR-vDDijbj2VFU64anTlViOyD5w4v0/>`_
  *  `absbox 301 <https://docs.google.com/presentation/d/1AQ3Xbxr0Ts_7ojcm1VRDq6Ib57IwitWjbbP-6fjivMY/>`_


Videos
""""""""

.. list-table:: Tutorial Videos
   :header-rows: 1

   * - Title
     - URL
   * - 101 - Introduction
     - https://youtu.be/fb8j96beLGQ
   * - 102 - Account
     - https://youtu.be/uD7MmiIftLs
   * - 103 - Assets
     - TBD
   * - 104 - Bonds
     - TBD
   * - 105 - Waterfall
     - https://youtu.be/TOe2vQRs-oc
   * - 201 - Pool Performance Assumption
     - https://youtu.be/HwcsA_zIKr0
   * - 202 - Term based Assumption
     - https://youtu.be/YHOpgo_gw-8 
   * - 301 - Sensitivity Analysis
     - TBD
   * - 302 - Structuring
     - TBD



Asset Cashflow Projection Document
-----------------------------------

Performing Asset
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Mortgage/Loan/Installment
"""""""""""""""""""""""""""

* determine the ``projection dates``
  
  * ``start date`` -> There is a field in asset present the `origination date` ,which means the date when asset came into existance.
  * ``(original/scheduled) payment dates`` -> Then, cashflow engine will generate a vector of payment dates bases on `origination date` and `payment frequency`
  * ``remaining payment dates`` -> base on the input field `remaining terms`, engine will trancate the `payment dates` to get `remaining payment dates`

* project cashflow with assumptions
  
  * ``projected cashflow`` -> Given `remaining payment dates` and `current balance` , then engine will calculate cashflow with assumption starting from `remaining payment dates`

* truncate the cashflow via `cutoff date`

  * `projected cashflow` was truncated via `cutoff date` ,that's the cashflow of asset which flows into the SPV


How assumption was applied on asset ? 
""""""""""""""""""""""""""""""""""""""

  .. image:: img/assump_balance.png
    :width: 500
    :alt: waterfall_run_loc



Non-Performing Asset(WIP)
""""""""""""""""""""""""""""

Why Mortgage Performance Assumption is so complex ?
--------------------------------------------------------

Before version ``0.21.x`` , pool performance assumption is just a *LIST*, which includes like ``{"CDR":0.05}``

But it is not scalable when more types of assets and assumptions are introduced. for example: when including new assumption on *Delinquency*, what happen if user passes ``[{"CDR":0.05},{"Delinquency":0.05}]`` ? How delinquency interacts with default assumption ? 

It can be solved by introducing "How" via supplying a *Tuple* as below :

.. code-block:: python
  
  ("Mortgage","Delinq",<delinquency assump>,<prepay assump>,<recovery assump>,<extra assump>)

With starting ``("Mortgage","Delinq",...)`` the engine treat this as identifier to logic of how apply pool assumption.

It is scalable if more assumption type comming in.


Deal Run Cycle 
--------------------


.. graphviz::
    :name: sphinx.ext.graphviz
    :caption: deal run cycle
    :alt: deal run cycle
    :align: center
    
    digraph G {

      subgraph cluster_0 {
        style=filled;
        color=lightgrey;
        node [style=filled,color=white];
        PoolCollectionByRule -> DepositToAccounts -> RunTriggers_EndOfCollection -> EndCollecitonAction -> RunTriggers_EndOfCollectionWF;
        label = "Pool Collection #1";
      }
      
      RunTriggers_EndOfCollectionWF -> nextAction;

      subgraph cluster_1 {
        node [style=filled];
        testTriggers_BeforeWaterfall -> RunWaterfallActionsByDealStatus;
        RunWaterfallActionsByDealStatus -> testTriggers_AfterWaterfall -> testCallOptions;
        label = "Run Waterfall #2";
        color=blue
      }
      
      testCallOptions [shape=diamond] 
      
      testCallOptions -> cleanUpActions [label="True"];
      testCallOptions -> nextAction [label="False"];
      
      subgraph cluster_2 {
        node [style=filled];
        cleanUpActions;
        label = "Clean Up Waterfall #3";
        color=blue
      }
      cleanUpActions 
      

      
      start -> PoolCollectionByRule;
      start -> testTriggers_BeforeWaterfall;

      
      cleanUpActions -> end;


      start [shape=Mdiamond];
      
      start -> end [label="No more pool cashflow"];
      start -> end [label="No more action dates"];
      start -> end [label="Reach stated maturity date"];
      
      end [shape=Msquare];
    }



Why so many list tuples and maps in deal model
---------------------------------------------------

* Transparency 
  
  Unlike `Class` , all data were exposed to user via native structure.
  
  `Class` will hide `states` and changing based on behavior of methods, that's dark magic we should avoid.

* Integration
  
  Because native stucture will enable user's own way to build data structure required.
  
  User has his/her own code base, which may have heavily couple with `PyDantic` or `Numpy` or other library, but anyway, all these data structure will provide methods to convert back to Python structure.

* IO friendly
  
  Most of persistent layer supports native structure, like `PyMongo` `redis` etc .

  It's easy to pull from these data and initialized models.

* Flexibility
  
  Isn't making too much keystroke to model a deal ? 

  Don't have to that way ,because `list` `tuple` `maps` are just *DATA* ,user can easily build candy function wrap the generator 

  .. code-block:: python 

    ["payPrin","SourceAccount","A"
            ,{"formula": ("substract"
                            ,("poolBalance",)
                            ,("factor"
                                ,("poolBalance",), 0.12))}]
    # isn't it nice ?
    
    def payBondwithOC(an,bn,oc):
        return ["payPrin",an,bn
                          ,{"formula": ("substract"
                                          ,("poolBalance",)
                                          ,("factor"
                                              ,("poolBalance",),oc))}]
    
    # now you can build your own functions !
    payBondwithOC("SourceAccount","A",0.15)

  .. note::
    If you are typing too much or feel duplication of coding, pls think twice what can be done to perform `abstraction` on your code.
    
    Because `absbox` isn't designed to be used boilerplate code.

JSON Format
--------------

Deal 
"""""""""
A deal object can be converted into json format via a property field `.json`

User can save this string/json object to database or file system, building a ``Deal Library``

.. code-block:: python
   
   #Assuming 

   test.json  

   #{'tag': 'MDeal',
   # 'contents': {'dates': {'tag': 'PreClosingDates',
   #   'contents': ['2021-03-01',
   #    '2021-06-15',
   #    None,
   #    '2030-01-01',
   #    ['2021-06-15', {'tag': 'MonthEnd'}],
   #    ['2021-07-26', {'tag': 'DayOfMonth', 'contents': 20}]]},
   #  'name': 'Multiple Waterfall',
   #  'status': {'tag': 'Amortizing'},
   #  'pool': {'assets': [{'tag': 'Mortgage',
   #     'contents': [{'originBalanc
Run Request 
""""""""""""""""

For user who has a strong curiosity in `Hastructure` webservice interface, user can use `build_run_deal_req()` to get a json request in string.

The string includes: 

* deal objects 
* pool performance assumptions
* deal run assumptions

This trick is useful to understand how `Hastructure` API work and integration with `Hastructure` directly.

.. code-block:: python 

  api.build_run_deal_req(....)


Make the JSON more readable
"""""""""""""""""""""""""""""""

The JSON reprensentation is targeting with `Servant/Aeson` in Haskell.
It's is well design while if you want to protect your eyeball, you can try with read it in Python, there is a built-in function in `absbox` can help you a little built-in.

.. code-block:: python

  from absbox import readAeson

  json_string = api.build_run_deal_req(...)

  readAeson(json_string)



How to evaluate the model built with `Absbox`?
------------------------------------------------

After hours, probably you have built a model (an instance of `Generic` class) without single error message from engine !!

You may wondering wheter the model you have built is `correct` ?

The general sequence to check to assure the quality of cashflow model :

1. Pool cashflow 

    Check if the pool cashflow generated is in line with expected pool cashflow. If pool were not `Correct` ,the rest of cashflow distribution is wrong either.

2. Waterfall 
  
    By inspecting `account trasaction` statement, you can view the waterfall breakdown actions during all the payment dates and compare with the one described in the deal documents.

3. Bond cashflow
   
    In deal documents, there might be `WAL` of bonds, you can price the bond in `absbox` and check the WAL from the pricing is in line with the ones in deal documents.


.. seealso::

    * To view the cashflow :ref:`Getting Results`
    * To debug the cashflow model -> :ref:`Debug the cashflow`



How to inspect ? 
^^^^^^^^^^^^^^^^^^^^^^^


