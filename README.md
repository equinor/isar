# ISAR

[![Python package](https://github.com/equinor/isar/actions/workflows/pythonpackage.yml/badge.svg)](https://github.com/equinor/isar/actions/workflows/pythonpackage.yml)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![License](https://img.shields.io/badge/License-EPL_2.0-blue.svg)](https://opensource.org/licenses/EPL-2.0)

ISAR - Integration and Supervisory control of Autonomous Robots - is a tool for integrating robot applications into
operator systems. Through the ISAR API you can send commands to a robot to do missions and collect results from the
missions.

## Getting started

Steps:

- Install
- Integrate a robot
- Run the ISAR server
- Run a robot mission

### Install

For local development, please fork the repository. Then, clone and install in the repository root folder:

```
git clone https://github.com/<path_to_parent>/isar
cd isar
pip install -e .[dev]
```

For `zsh` you might have to type `".[dev]"`

Verify that you can run the tests:

```bash
pytest .
```

The repository contains a configuration file for installing pre-commit hooks. Currently, [black](https://github.com/psf/black) and a mirror of [mypy](https://github.com/pre-commit/mirrors-mypy) are configured hooks. Install with:

```
pre-commit install
```

Verify that pre-commit runs:

```
pre-commit
```

pre-commit will now run the installed hooks before code is commited to git. To turn pre-commit off, run:

```
pre-commit uninstall
```

### Robot integration

To connect the state machine to a robot in a separate repository, it is required that the separate repository implements
the [robot interface](https://github.com/equinor/isar/blob/main/src/robot_interface/robot_interface.py).
The separate repository should also have a settings.env file in a config folder where `CAPABILITIES` and `ROBOT_MODEL` are set.
A mocked robot can be found in [this repository](https://github.com/equinor/isar-robot). Install the repo, i.e:

```bash
pip install isar-robot
```

NB: isar-robot has not been published to PyPi for some time, and needs to be downloaded directly
from git to work.

Then, ensure the `ISAR_ROBOT_PACKAGE` variable in [settings.env](./src/isar/config/settings.env)
is set to the name of the package you installed. `isar_robot` is set by default. See the section
for [configuration](#configuration) for overwriting configuration.

If you have the robot repository locally, you can simply install through

```bash
pip install -e /path/to/robot/repo/
```

#### Running ISAR with a robot simulator

A simulator based on the open source robot Turtlebot3 has been implemented for use with ISAR and may be
found [here](https://github.com/equinor/isar-turtlebot). Follow the installation instructions for the simulator and
install `isar-turtlebot` in the same manner as given in the [robot integration](#robot-integration) section. Overwrite
the following configuration variables:

```bash
ISAR_ROBOT_PACKAGE = isar_turtlebot
ISAR_DEFAULT_MAP = turtleworld
```

### Run ISAR server

To run ISAR:

```bash
python main.py
```

Note, running the full system requires that an implementation of a robot has been installed. See
this [section](#robot-integration) for installing a mocked robot or a Turtlebot3 simulator.

### Running a robot mission

Once the application has been started the swagger site may be accessed at

```
http://localhost:3000/docs
```

Execute the `/schedule/start-mission` endpoint with `mission_id=1` to run a mission.

In [this](./src/isar/config/predefined_missions) folder there are predefined default missions, for example the mission
corresponding to `mission_id=1`. A new mission may be added by adding a new json-file with a mission description. Note,
the mission IDs must be unique.

### Configuration

The system consists of many configuration variables which may alter the functionality. As an example, it is possible to
change mission planners or add multiple storage handlers as described in the [mission planner](#mission-planner)
and [storage](#storage) sections.

There are two methods of specifying configuration.

1. Override the default value by setting an environment variable.

   Every configuration variable is defined in [settings.py](./src/isar/config/settings.py), and they may all be
   overwritten by specifying the variables in the environment instead. Note that the configuration variable must be
   prefixed with `ISAR_` when specified in the environment. So for the `ROBOT_PACKAGE`configuration variable:

   ```shell
   export ISAR_ROBOT_PACKAGE=isar_turtlebot
   ```

   This means ISAR will connect to `isar_turtlebot` robot package.

2. Adding environment variables through [settings.env](./src/isar/config/settings.env).

   By adding environment variables with the prefix `ISAR_` to the [settings.env](./src/isar/config/settings.env) file
   the configuration variables will be overwritten by the values in this file.

### Running tests

After following the steps in [Development](#install), you can run the tests:

```bash
pytest .
```

To create an interface test in your robot repository, use the function `interface_test` from `robot_interface`. The
argument should be an interface object from your robot specific implementation.
See [isar-robot](https://github.com/equinor/isar-robot/blob/main/tests/interfaces/test_robotinterface.py) for example.

#### Integration tests

Integration tests can be found [here](https://github.com/equinor/isar/tree/main/tests/integration) and have been created
with a simulator in mind. The integration tests will not run as part of `pytest .` or as part of the CI/CD pipeline. To
run the integration tests please follow the instructions in [this section](#running-isar-with-a-robot-simulator) for
setting up the `isar-turtlebot` implementation with simulator and run the following command once the simulation has been
launched.

```bash
pytest tests/integration
```

Note that these tests will run towards the actual simulation (you may monitor it through Gazebo and RVIZ) and it will
take a long time.

### Documentation

To build the project documentation, run the following commands:

```bash
cd docs
make docs
```

The documentation can now be viewed at `docs/build/html/index.html`.

## Components

The system consists of two main components.

1. State machine
1. FastAPI

### State machine

The state machine handles interaction with the robots API and monitors the execution of missions. It also enables
interacting with the robot before, during and after missions.

The state machine is based on the [transitions](https://github.com/pytransitions/transitions) package for Python. The following are some visualizations of the state machine:

Mission behavior without the robot status changed transition that enable the resting states to transition between each other if the robot status changes:
![State Machine extended](./docs/extended_state_machine_diagram.png)

Robot status changed transition:
![State Machine robot status changed](./docs/robot_status_state_machine_diagram.png)

Full state machine:
![State Machine full](./docs/full_state_machine_diagram.png)

In general the states

```
States.Stopping,
States.Monitor,
States.Paused,
```

indicates that the state machine is already running. For running a mission the state machine need to be in the states

```
States.Home, States.RobotStandingStill, States.AwaitNextMission or States.ReturningHome
```

### FastAPI

The FastAPI establishes an interface to the state machine for the user. As the API and state machine are separate
threads, they communicate through python queues. FastAPI runs on an ASGI-server, specifically uvicorn. The
FastAPI-framework is split into routers where the endpoint operations are defined.

## Mission planner

The mission planner that is currently in use is a local mission planner, where missions are specified in a json file. You can create your own mission planner by implementing
the [mission planner interface](./src/isar/mission_planner/mission_planner_interface.py) and adding your planner to the
selection [here](./src/isar/modules.py). Note that you must add your module as an option in the dictionary.

## Storage

The storage modules that are used is defined by the `ISAR_STORAGE` configuration variable. This can be changed by
overriding the configuration through an environment variable. It accepts a json encoded list and will use each element
in the list to retrieve the corresponding handler. The current options are

```
ISAR_STORAGE = '["local", "blob", "slimm"]'
```

Note that the `blob` and `slimm` options require special configuration to authenticate to these endpoints.

### Implement your own storage module

You can create your own storage module by implementing the [storage interface](./src/isar/storage/storage_interface.py)
and adding your storage module to the selection [here](./src/isar/modules.py). Note that you must add your module as an
option in the dictionary.

## Task selection

The tasks of a mission are selected based on a task selector module, defined by the `TASK_SELECTOR` configuration variable. The default task selector is `sequential`. When using the default module, tasks are executed in sequential order defined by the current input mission.

### Implement you own task selector module

Custom task selector modules may be added by implementing additional versions of the [task selector interface](./src/isar/mission_planner/task_selector_interface.py).

For every custom module, the interface function `next_task()` must be implemented. All interface implementations by default have access to the list of tasks in the current mission through the member `self.tasks`, however additional variables may be supplied by adding arguments to `next_task()`. To comply with the interface definition, the function should return the next task upon every call, and raise the `TaskSelectorStop` exception when all tasks in the current mission have been completed:

```python
class CustomTaskSelector(TaskSelectorInterface):
    ...
    def next_task(...) -> Task:

        # Add code here
        ...

        # Raise `TaskSelectorStop` when all tasks have been completed
        ...
```

Optionally, the `initialize()` function may be extended by supplementing the parameter list or function body:

```python
class CustomTaskSelector(TaskSelectorInterface):
    ...
    def initialize(self, tasks: List[Task], ...) -> None:
        super.initialize(tasks=tasks)

        # Add supplementary code here
        ...
```

A custom task selector may be made available during [module selection](./src/isar/modules.py) by adding it to the series of options in the dictionary of injector modules. It can then be activated by overriding the task selector configuration variable:

```python
# Add custom task selector module to `modules.py`

class CustomTaskSelectorModule(Module):
    @provider
    @singleton
    def provide_task_selector(self) -> TaskSelectorInterface:
        return CustomTaskSelector()

...

# Make it available to select during injector instantiation

modules: dict[str, tuple[Module, Union[str, bool]]] = {
    ...
    "task_selector": (
        {
            "sequential": SequentialTaskSelectorModule,
            "custom": CustomTaskSelectorModule
        }
        ...
    )
    ...
}
```

## API authentication

The API has an option to include user authentication. This can be enabled by setting the environment variable

```
ISAR_AUTHENTICATION_ENABLED = true
```

By default, the `local` storage module is used and API authentication is disabled. If using Azure Blob Storage a set of
environment variables must be available which gives access to an app registration that may use the storage account.
Enabling API authentication also requires the same environment variables. The required variables are

```
AZURE_CLIENT_ID
AZURE_TENANT_ID
AZURE_CLIENT_SECRET
```

## MQTT communication

ISAR is able to publish parts of its internal state to topics on an MQTT broker whenever they change. This is by default
turned off but may be activated by setting the environment variable

```
ISAR_MQTT_ENABLED = true
```

The connection to the broker will be determined by the following configuration values in `settings.py`

```
ISAR_MQTT_USERNAME
ISAR_MQTT_HOST
ISAR_MQTT_PORT
```

The default values of these are overwritten by the environment in `settings.env`.

To specify broker password, add the following environment variable to a .env file in the root of the repository:

```
ISAR_MQTT_PASSWORD
```

If not specified the password will default to an empty string.

## Running several ISAR instances locally

To run several ISAR instances in parallel locally:

1. Generate a guid: https://www.guidgenerator.com/
2. Open a new terminal in the isar folder
3. Run the following command before running main.py:

```
export ISAR_API_PORT=port_name_higher_than_1024 ISAR_ISAR_ID=guid ISAR_ROBOT_NAME=random_robot_name
```

# Dependencies

The dependencies used for this package are listed in `pyproject.toml` and pinned in `requirements.txt`. This ensures our builds are predictable and deterministic. This project uses `pip-compile` (from [`pip-tools`](https://github.com/jazzband/pip-tools)) for this:

```
pip-compile --output-file=requirements.txt pyproject.toml
```

To update the requirements to the latest versions, run the same command with the `--upgrade` flag:

```
pip-compile --output-file=requirements.txt pyproject.toml --upgrade
```

# Contributions

Equinor welcomes all kinds of contributions, including code, bug reports, issues, feature requests, and documentation
Please initiate your contribution by creating an [issue](https://github.com/equinor/isar/issues) or by forking the
project and making a pull requests. Commit messages shall be written according to [this guide](https://cbea.msgit-commit/).
