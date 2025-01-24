FAQ 
========

Why `absbox` is a wrapper while `Hastructure` as engine ?
------------------------------------------------------------

It's just a huge burden to model structured products in a dynamic language like `Python` or `Clojure`.
`Haskell` provides extream concise modelling language and high performance calculation engine.


Information leakage on `Hastructure` ?
---------------------------------------

If you send out run request to `Hastructure`, user may raise question whether other privacy information was sent to the engine as well.
Eventhough not many people can read the `Hastructure` code, but:

* it's open-souce 
* it has been verified by a big-name company


Can I use my own engine ?
-------------------------------------

Yes, you can pull docker image and delpoy it in your own server.

Or just use the pre-built binary and run it in your own server.


Why using `list`/`tuple`/`dict` in `absbox` ?
-----------------------------------------------

It's a `Data-Driven` oriented design, it's easy to pull data from any database/local files with variant formats and build inputs for `absbox` easily.

Other packages like `pandas` or `numpy`, `lenses` works fairly well with native data types as well.


Why there is no UI ?
-----------------------

UI is always a huge topic , because it's hard to satisfy everyone's need. `Risk Manger` `Quant` `Trader` `Structurer` all have different requirements on UI to satisfy their own specific needs.

Even some magic happens there are 4 sets of UIs to be developed, the workflows accross differnet companies will create frictions as well.

`absbox` and `Hastructure` would focus on core functionalities and provide `RESTful` service to make it easy to integrate with any UIs.


Why commerial support ? 
---------------------------------------

The `absbox` and `Hastructure` will remains free and open-source, while adopting it and using it in production, user may need some commerial support for the benefits below:

* quick knowledge transfer
* short integration time






