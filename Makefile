DOCKER_BASE = camptocamp/c2cwsgiutils
export DOCKER_BUILDKIT=1
VERSION = $(strip $(shell poetry version --short))

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
	docker run --rm --detach \
	--volume=$(shell pwd)/results:/results \
	--volume=$(shell pwd)/c2cwsgiutils:/opt/c2cwsgiutils/c2cwsgiutils \
	--volume=$(shell pwd)/tests:/opt/c2cwsgiutils/tests \
	$(DOCKER_BASE):tests pytest -vv --color=yes tests

.PHONY: acceptance
acceptance: tests build_acceptance build_redis_sentinal ## Run the acceptance tests
	docker run --rm --volume=/var/run/docker.sock:/var/run/docker.sock \
		--volume=$(shell pwd)/reports:/reports \
		--env=WAITRESS $(DOCKER_BASE)_acceptance py.test -vv --color=yes $(PYTEST_OPTS) tests

.PHONY: build_docker
build_docker:
	docker build --build-arg=VERSION=$(VERSION) --tag=$(DOCKER_BASE) --target=standard .

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
	.venv/bin/poetry install --with=dev
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
	-vv --color=yes --junitxml=reports/acceptance.xml --html=reports/acceptance.html \
	--self-contained-html $(PYTEST_OPTS) acceptance_tests/tests
