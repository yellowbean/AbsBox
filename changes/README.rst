Changelog fragments
===================

This directory holds `towncrier <https://towncrier.readthedocs.io/>`_ news
fragments for the next release. They are folded into ``CHANGELOG.rst`` by
``just changelog-build <version>`` and rendered on the docs changelog page.

Add one file per change, named ``<issue>.<type>.rst``, directly in this
directory, for example::

    changes/92.feature.rst
    changes/101.enhance.rst
    changes/105.bug.rst

Valid types (see ``[tool.towncrier]`` in ``pyproject.toml``):
``feature``, ``enhance``, ``bug``.

Preview the assembled changelog with ``just changelog-draft <version>``.
