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
