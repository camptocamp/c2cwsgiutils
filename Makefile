DOCKER_BASE = camptocamp/c2cwsgiutils
export DOCKER_BUILDKIT=1

GIT_HASH := $(shell git rev-parse HEAD)

DOCKER_TTY := $(shell [ -t 0 ] && echo -ti)

.PHONY: help
help: ## Display this help message
	@echo "Usage: make <target>"
	@echo
	@echo "Available targets:"
	@grep --extended-regexp --no-filename '^[a-zA-Z_-]+:.*## ' $(MAKEFILE_LIST) | sort | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "	%-20s%s\n", $$1, $$2}'

.PHONY: all
all: build checks acceptance ## Build checks and acceptance tests

.PHONY: build
build: build_docker build_acceptance build_test_app ## Build all Docker images

.PHONY: tests
tests: build_test_app ## Run the unit tests
	@docker run --rm $(DOCKER_BASE):tests pytest --version
	docker stop c2cwsgiutils_tests || true
	docker run --rm --detach --name=c2cwsgiutils_tests --volume=$(shell pwd):/opt/c2cwsgiutils $(DOCKER_BASE):tests tail -f /dev/null
	docker exec c2cwsgiutils_tests pytest -vv --cov=c2cwsgiutils --color=yes tests
	rm -rf reports/coverage/api reports/acceptance.xml
	mkdir -p reports/coverage/api
	# Get the UT reports
	docker cp c2cwsgiutils_tests:/opt/c2cwsgiutils/.coverage reports/coverage/api/coverage.ut.1
	docker stop c2cwsgiutils_tests

.PHONY: acceptance
acceptance: tests build_acceptance build_redis_sentinal ## Run the acceptance tests
	docker stop c2cwsgiutils-acceptance || true
	docker run --rm --detach --name=c2cwsgiutils-acceptance --volume=/var/run/docker.sock:/var/run/docker.sock \
		--env=WAITRESS $(DOCKER_BASE)_acceptance tail -f /dev/null
	docker exec c2cwsgiutils-acceptance py.test -vv --color=yes --junitxml /reports/acceptance.xml --html /reports/acceptance.html \
			--self-contained-html $(PYTEST_OPTS) tests
	# Copy the reports locally
	docker cp c2cwsgiutils-acceptance:/reports ./
	docker stop c2cwsgiutils-acceptance
	# Generate the HTML report for code coverage
	docker stop c2cwsgiutils-acceptance-reports || true
	docker run --rm --detach --volume=$(shell pwd)/reports/coverage/api:/reports/coverage/api:ro --name=c2cwsgiutils-acceptance-reports $(DOCKER_BASE)_test_app tail -f /dev/null
	docker exec c2cwsgiutils-acceptance-reports c2cwsgiutils-coverage-report c2cwsgiutils c2cwsgiutils_app
	# Copy the HTML locally
	docker cp c2cwsgiutils-acceptance-reports:/tmp/coverage/api reports/coverage
	docker stop c2cwsgiutils-acceptance-reports
	# Fix code path in the cobertura XML file
	sed -ie 's%>/app/c2cwsgiutils_app<%>$(shell pwd)/acceptance_tests/app/c2cwsgiutils_app<%' reports/coverage/api/coverage.xml
	sed -ie 's%filename="/opt/c2cwsgiutils/c2cwsgiutils/%filename="c2cwsgiutils/%' reports/coverage/api/coverage.xml
	sed -ie 's%</sources>%<source>$(shell pwd)</source></sources>%' reports/coverage/api/coverage.xml
	sed -ie 's%file="tests/%file="acceptance_tests/tests/tests/%' reports/acceptance.xml

.PHONY: build_docker
build_docker:
	docker build --tag=$(DOCKER_BASE) --target=standard .

.PHONY: build_docker_test
build_docker_test:
	docker build --tag=$(DOCKER_BASE):tests --target=tests .

.PHONY: build_acceptance
build_acceptance: build_docker_test
	docker build --tag=$(DOCKER_BASE)_acceptance acceptance_tests/tests

.PHONY: build_test_app
build_test_app: build_docker
	docker build --tag=$(DOCKER_BASE)_test_app --build-arg="GIT_HASH=$(GIT_HASH)" acceptance_tests/app

.PHONY: build_redis_sentinal
build_redis_sentinal:
	docker build --tag=$(DOCKER_BASE)-redis-sentinel:6 acceptance_tests/tests/redis/

.PHONY: checks
checks: prospector ## Run the checks

.PHONY: prospector
prospector: build_docker_test ## Run the prospector checker
	@docker run --rm $(DOCKER_BASE):tests prospector --version
	@docker run --rm $(DOCKER_BASE):tests mypy --version
	@docker run --rm $(DOCKER_BASE):tests pylint --version --rcfile=/dev/null
	@docker run --rm $(DOCKER_BASE):tests pyflakes --version
	docker run --rm --volume=$(shell pwd):/opt/c2cwsgiutils $(DOCKER_BASE):tests prospector --output-format=pylint --die-on-tool-error

.venv/timestamp: requirements.txt ci/requirements.txt pyproject.toml poetry.lock
	/usr/bin/virtualenv --python=/usr/bin/python3 .venv
	.venv/bin/pip3 install --upgrade -r requirements.txt -r ci/requirements.txt
	.venv/bin/poetry install --dev
	.venv/bin/pip install --editable=.
	touch $@

.PHONY: pull
pull: ## Pull the Docker images
	for image in `find -name "Dockerfile*" | xargs grep --no-filename FROM | awk '{print $$2}' | sort -u | grep -v c2cwsgiutils`; do docker pull $$image; done
	for image in `find -name "docker-compose*.yaml" | xargs grep --no-filename "image:" | awk '{print $$2}' | sort -u | grep -v $(DOCKER_BASE) | grep -v rancher`; do docker pull $$image; done

.PHONY: run
run: build_test_app ## Run the test application
	# cp acceptance_tests/tests/docker-compose.override.sample.yaml acceptance_tests/tests/docker-compose.override.yaml
	cd acceptance_tests/tests/; TEST_IP=172.17.0.1 docker-compose up

.PHONY: mypy_local
mypy_local: .venv/timestamp
	.venv/bin/mypy --ignore-missing-imports --strict-optional --strict c2cwsgiutils

.PHONY: clean
clean:
	rm -rf dist c2cwsgiutils.egg-info .venv .mypy_cache

.PHONY: c2cciutils
c2cciutils: .venv/timestamp
	.venv/bin/poetry run .venv/bin/c2cciutils-checks --fix

.PHONY: acceptance_local
acceptance_local: .venv/timestamp
	DOCKER_RUN=0 ./.venv/bin/pytest \
	-vv --color=yes --junitxml reports/acceptance.xml --html reports/acceptance.html \
	--self-contained-html $(PYTEST_OPTS) acceptance_tests/tests
