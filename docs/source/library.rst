Deal Library
===============

.. versionadded:: 0.43.1

What is a Library?
---------------------

``Deal Library`` is a seperate web serivce component which offers:

* user authentication
* deal tag-based search
* run analytics on deals hosted on the platform

User can access the ``Deal Library`` through the component from ``absbox``.

Self host & Cloud host
^^^^^^^^^^^^^^^^^^^^^^^^^^
There is a public ``Deal Library`` instance hosted on the cloud. 
User can also host his/her own instance of the ``Deal Library`` on own server with commerial terms ( check with :ref:`Email & Slack`).


Tutorial
---------------



Connect to the ``Deal Library``
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: python

    from absbox import LIBRARY

    library = LIBRARY("http://localhost:8082/api")


.. note::

    User can setup his/her own library in-house or use the public one hosted on the cloud.
    The public one is available at ``LibraryPath``
    
    .. code-block:: python

        from absbox import LibraryPath


Confirm the connection
""""""""""""""""""""""""

.. code-block:: python

    library.libraryInfo

Login
"""""""""

.. code-block:: python

    library.login("username","password")
    library.safeLogin("trial_1")"


Query a deal
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

3 types of query are supported:

* query by id , return a single deal
* query by tag ( return a list of deals found)
* query by name , return a most recent deal with matching name

.. code-block:: python

    library.query(("id",1))

    library.query(("tag","test"))

    library.query(("name",r"MM"))


Run analytics
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^


Run Input
""""""""""""

User can initiate a run request sending to server. The server will find ``Hastructure`` engine by "default" or the one overrided by user.

.. code-block:: python

    (i,r) = library.run(<Deal Selector>
                    ,runAssump = <Run Assumption>
                    ,poolAssump = <Pool Assumption>
                    ,runType = <Run Type>
                    ,read=True
                    ,engine="ldn-dev"
                )

<Deal Selector>
    Can be either :
        * ("id",1)
        * ("name",<Deal Name>)

<Run Type>
    Can be either :
        * "S" -> Default,single run (Default)
        * "MC" -> Multiple pool assumption
        * "MRS" -> Multiple run assumption
        * "CS" -> Combo (multiple pool and run assumption)

Run Output
""""""""""""

The ``run()`` will return a tuple of two elements:

* Left value -> the run information (engine used, deal used)
* Right value -> exact the same output as the one in ``absbox`` API instance.

Notebook
""""""""""""

.. seealso::

    :ref:`Library Example`