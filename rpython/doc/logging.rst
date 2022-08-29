Logging environment variables
=============================

PyPy, and all other RPython programs, support some special environment
variables used to tweak various advanced parameters.


Garbage collector
-----------------

Right now the default GC is (an incremental version of) MiniMark__.
It has :ref:`a number of environment variables
<minimark-environment-variables>` that can be tweaked.  Their default
value should be ok for most usages.

.. __: garbage_collection.html#minimark-gc


PYPYLOG
-------

The ``PYPYLOG`` environment variable enables debugging output.  For
example::

   PYPYLOG=gc:log

means enabling all debugging output from the GC, and writing to a
file called ``log``.  Note that is possible to use several prefixes.

The filename can be given as ``-`` to dump the log to stderr.

As a special case, the value ``PYPYLOG=+filename`` means that only
the section markers are written (for any section).  This is mostly
only useful for ``rpython/tool/logparser.py``.


PYPYSTM
-------

Only available in ``pypy-stm``.  Names a log file into which the
PyPy-STM will output contention information.  Can be read with
``pypy/stm/print_stm_log.py``.
