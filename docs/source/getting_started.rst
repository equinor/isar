Getting started
===============

Installation
------------

.. py:currentmodule:: isar

Install the latest version with pip::

    $ pip install git+https://github.com/equinor/isar.git@main

Run ISAR::

    $ python -m flask run

.. _development:

Development
-----------

For local development, please fork the repository. Clone your fork and install it locally::

    $ git clone https://github.com/your-username/isar
    $ cd isar
    $ pip install -e ".[dev]"

Next, set your environment to :code:`local`::

    $ export ENVIRONMENT=local

Finally, verify that you can run the tests::

    $ pytest .

Robot intergration
------------------

In order to connect the state machine module to a robot defined in a separate repository, it is required that the robot implements the ISAR :ref:`robot-interface` class.

For a robot which implements the interface, for instance the `isar robot`_, first install it locally::

    $ pip install git+https://github.com/equinor/isar-robot.git@main

Then, set an environment variable to the name of the package you installed::

    $ export ROBOT_DIRECTORY=isar_robot

.. note::

   If the repository exists locally, it can simply be installed through::

       $ pip install -e /path/to/robot/repo

Running tests
-------------

After following the steps in :ref:`development`, you can run the tests::

    $ pytest . -n 10


.. _`wheel`: https://pypi.org/project/wheel/
.. _`isar robot`: https://github.com/equinor/isar-robot