# ISAR

ISAR - Integration and Supervisory control of Autonomous Robots - is a tool for integrating robot applications into
Equinor systems. Through the ISAR API you can send command to a robot to do missions and collect results from the
missions.

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
- Collect: The state collects data during a mission.
- Cancel: The state machine has received a request to abort, or an event has occurred which requires the mission to be
  canceled. The cancel state also functions as a wrap-up state when a mission is finished, prior to the state machine
  returning to idle.

### Flask API

The Flask API establishes an interface to the state machine for the user. As the API and state machine are separate
threads, they communicate through python queues. The main flask extension used for the API design is
the [flask-restx](https://github.com/python-restx/flask-restx) package.

## Installation

```bash
$ pip install git+https://github.com/equinor/isar.git@main
```

Note, installation might require [wheel](https://pypi.org/project/wheel/).

To run ISAR:

```bash
$ python -m flask run --no-reload
```

Note, running the full system requires that an implementation of a robot has been installed. See
this [section](#robot-integration) for installing a mocked robot.

## Running a robot mission

Once the application has been started the swagger site may be accessed at

```
http://localhost:3000/
```

Execute the `/schedule/start-mission` with `mission_id=1` to run a mission.

In [this](./src/isar/config/pre_defined_missions) folder there are predefined default missions, for example the mission
corresponding to `mission_id=1`. A new mission may be added by adding a new json-file with a mission description. Note,
the mission IDs must be unique.

## <a name="dev"></a>Development

For local development, please fork the repository. Then, clone and install in the repository root folder:

```
$ git clone https://github.com/equinor/isar
$ cd isar
$ pip install -e ".[dev]"
```

Set environment to local:

```
$ export ENVIRONMENT=local
```

Verify that you can run the tests:

```bash
$ pytest .
```

## Robot integration

To connect the state machine to a robot in a separate repository, it is required that the separate repository implements
the [robot interface](https://github.com/equinor/isar/blob/main/src/robot_interfaces/robot_interface.py). Install the
repo, i.e:

```bash
$ pip install git+https://@github.com/equinor/isar-robot.git@main
```

Then, set an environment variable to the name of the package you installed:

```
$ export ROBOT_DIRECTORY=isar_robot
```

If you have the robot repository locally, you can simply install through

```bash
$ pip install -e /path/to/robot/repo/
```

## Running tests

After following the steps in [Development](#dev), you can run the tests:

```bash
$ pytest -n 10
```

## Contributing

We welcome all kinds of contributions, including code, bug reports, issues, feature requests, and documentation. The
preferred way of submitting a contribution is to either make an [issue](https://github.com/equinor/isar/issues) on
github or by forking the project on github and making a pull requests.
