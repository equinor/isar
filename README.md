# isar

Integration and Supervisory control of Autonomous Robots

## Components

The system consists of two threads running in parallel.

1. State machine
1. Flask API

### State machine

The state machine handles interaction with the robots API and monitors the execution of missions. It also enables
interacting with the robot before, during and after missions.

The state machine is based on the [transitions](https://github.com/pytransitions/transitions) package for Python. Its
main states are:

- Idle: The robot is in an idle state and ready to perform new missions.
- Send: The state machine has received a mission and is sending the mission to the robot.
- Monitor: The robot has received a mission from the state machine, and the state machine is monitoring the current
  mission.
- Cancel: The state machine has received a request to abort, or an event has occurred which requires the mission to be
  canceled. The cancel state also functions as a wrap-up state when a mission is finished, prior to the state machine
  returning to idle.

### Flask API

The Flask API establishes an interface to the state machine for the user. As the API and state machine are separate
threads, they communicate through python queues. The main flask extension used for the API design is
the [flask-restx](https://github.com/python-restx/flask-restx) package.

## Robot integration

To connect the statemachine to a robot in a seperate repository, pip install the repo, i.e:
`pip install git+https://{GITHUB_TOKEN}@github.com/user/some_repo.git@some_branch --upgrade`
then change the config variable `robot_directory` to the name of the package you installed
If you have the robot repository locally, you can simply install through `pip install -e /path/to/robot/repo/`

## Local development

1. Clone the repository.
1. Add the variable `ENVIRONMENT` to you local environment and set it to `local`. For example, if adding to `.bashrc` in Linux:
   ```shell
   ENVIRONMENT=local
   ```
1. Create a `venv` (Python 3.8) and install package requirements `pip install -r requirements.txt --upgrade`.
1. Run `pip install -e .` to install the packages in the virtual environment in editable mode
1. Run the `populate_environment.py` script to create a .env file which holds required secrets. Note that you must provide a client secret for a service principal with access to the relevant keyvault. This script depends on the `ENVIRONMENT` variable.

```sh
  python populate_environment.py --client-secret INSERT_SECRET_HERE
```

#### For PyCharm:

1. Setup `Black` as a file watcher.
   - The setup will depend on your IDE. If using PyCharm follow
     this [guide](https://black.readthedocs.io/en/stable/integrations/editors.html#pycharm-intellij-idea).
1. Setup Pycharms to run `optimize imports` on save, for autoformatting of imports.
   - In File/Settings/Editor/CodeStyle/Python/Imports checkmark the following:
     - _Sort import statements_
     - _Sort plain and from imports separately within a group_
     - _Join imports with the same source_
   - Install the `Save Action` plugin and checkmark the following
     - _Activate save actions on save_ or _Activate save actions on shortcut_
     - _Optimize imports_

#### For VSCode

1. Install the Python and Pylance extension
1. Add the following lines to you `settings.json`:

```json
    "python.formatting.provider": "black",
    "python.languageServer": "Pylance",
    "[python]": {
        "editor.codeActionsOnSave": {
            "source.organizeImports": true
        }
    },
```

#### For running and debugging

1. Disable Flask debug reloader
   - _In Edit Configurations, Flask (main.py)_:
     - _In additional options type `--no-reload`_
   - This disables Flasks functionality for reloading automatically when changes are made to the code. The side effect of having this active is described [here](https://stackoverflow.com/questions/25504149/why-does-running-the-flask-dev-server-run-itself-twice/25504196) and in this system leads to the state machine thread starting twice.
1. Use multiple cores to run pytest for reduced test execution times
   - - In Edit Configurations (pytest.py)
       - _In Additional Arguments type `-n 10`_ (10 refers to the number of cores and can be replaced with other integers)

### Running MyPy

This project uses [MyPy](https://github.com/python/mypy) to enforce type hinting in Python. The configuration is given
in [mypy.ini](./mypy.ini). There is also an [extension](https://github.com/dropbox/mypy-PyCharm-plugin) which may be
used for PyCharm.

To run MyPy locally in a terminal from the repository root:

```
mypy .
```

If you're using the PyCharm MyPy extension right clik the MyPy terminal window in PyCharm and select `Configure plugin`.
Then set the following values:

```
Mypy command: dmypy run --  ./
PATH suffix: ./venv/bin (your mypy installation path)
```
