DOCKER_TAG ?= latest
DOCKER_BASE = camptocamp/c2cwsgiutils

#Get the docker version (must use the same version for acceptance tests)
DOCKER_VERSION_ACTUAL := $(shell docker version --format '{{.Server.Version}}')
ifeq ($(DOCKER_VERSION_ACTUAL),)
DOCKER_VERSION := 1.12.0
else
DOCKER_VERSION := $(DOCKER_VERSION_ACTUAL)
endif

#Get the docker-compose version (must use the same version for acceptance tests)
DOCKER_COMPOSE_VERSION_ACTUAL := $(shell docker-compose version --short)
ifeq ($(DOCKER_COMPOSE_VERSION_ACTUAL),)
DOCKER_COMPOSE_VERSION := 1.10.0
else
DOCKER_COMPOSE_VERSION := $(DOCKER_COMPOSE_VERSION_ACTUAL)
endif

.PHONY: all
all: lint acceptance

.PHONY: lint
lint: lint_code lint_test_app lint_acceptance

.PHONY: lint_code
lint_code: build_test_app
	docker run --rm $(DOCKER_BASE)_test_app:$(DOCKER_TAG) flake8 /app/c2cwsgiutils

.PHONY: lint_test_app
lint_test_app: build_test_app
	docker run --rm $(DOCKER_BASE)_test_app:$(DOCKER_TAG) flake8 /app/c2cwsgiutils_app

.PHONY: lint_acceptance
lint_acceptance: build_acceptance
	docker run --rm $(DOCKER_BASE)_acceptance:$(DOCKER_TAG) flake8 /acceptance_tests/tests

.PHONY: acceptance
acceptance: build_acceptance build_test_app
	mkdir -p reports
	docker run -e DOCKER_TAG=$(DOCKER_TAG) -v /var/run/docker.sock:/var/run/docker.sock --name c2cwsgiutils_acceptance_$(DOCKER_TAG)_$$PPID $(DOCKER_BASE)_acceptance:$(DOCKER_TAG) py.test -vv --color=yes --junitxml /reports/acceptance.xml $(PYTEST_OPTS) tests; \
	status=$$?; \
	docker cp c2cwsgiutils_acceptance_$(DOCKER_TAG)_$$PPID:/reports/acceptance.xml reports/acceptance.xml; \
	status=$$status$$?; \
	docker rm c2cwsgiutils_acceptance_$(DOCKER_TAG)_$$PPID; \
	exit $$status$$?

.PHONY: build_acceptance
build_acceptance:
	rsync -a c2cwsgiutils setup.cfg acceptance_tests/tests/
	docker build --build-arg DOCKER_VERSION="$(DOCKER_VERSION)" --build-arg DOCKER_COMPOSE_VERSION="$(DOCKER_COMPOSE_VERSION)" -t $(DOCKER_BASE)_acceptance:$(DOCKER_TAG) acceptance_tests/tests

.PHONY: build_test_app
build_test_app:
	rsync -a c2cwsgiutils requirements.txt setup.cfg acceptance_tests/app/
	docker build -t $(DOCKER_BASE)_test_app:$(DOCKER_TAG) acceptance_tests/app
