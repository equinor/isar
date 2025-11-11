run:
	isar-start

test:
	ENVIRONMENT=local ISAR_ENV=test pytest .

format:
	isort .
	black .
	ruff check . --fix

check:
	mypy .

run-debug: # debug logs
	API_LOG_LEVEL=DEBUG \
	MAIN_LOG_LEVEL=DEBUG \
	MQTT_LOG_LEVEL=DEBUG \
	STATE_MACHINE_LOG_LEVEL=DEBUG \
	UPLOADER_LOG_LEVEL=DEBUG \
	CONSOLE_LOG_LEVEL=DEBUG \
	ISAR_DEBUG_LOG_FORMATTER=True \
	isar-start
