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

GIT_HASH := $(shell git rev-parse HEAD)
THIS_MAKEFILE_PATH := $(word $(words $(MAKEFILE_LIST)),$(MAKEFILE_LIST))
THIS_DIR := $(shell cd $(dir $(THIS_MAKEFILE_PATH));pwd)

DOCKER_TTY := $(shell [ -t 0 ] && echo -ti)

.PHONY: all
all: mypy acceptance

.PHONY: build
build: build_acceptance build_test_app

.PHONY: acceptance
acceptance: build_acceptance build_test_app
	rm -rf reports/coverage/api reports/acceptance$(PYTHON_VERSION).xml
	mkdir -p reports/coverage/api
	#run the tests
	docker run $(DOCKER_TTY) -v /var/run/docker.sock:/var/run/docker.sock --name c2cwsgiutils_acceptance_$$PPID $(DOCKER_BASE)_acceptance:latest \
	    bash -c "py.test -vv --color=yes --junitxml /reports/acceptance$(PYTHON_VERSION).xml $(PYTEST_OPTS) tests; status=\$$?; junit2html /reports/acceptance$(PYTHON_VERSION).xml /reports/acceptance$(PYTHON_VERSION).html; exit \$$status\$$?"; \
	status=$$?; \
	#copy the reports locally \
	docker cp c2cwsgiutils_acceptance_$$PPID:/reports ./; \
	status=$$status$$?; \
	docker rm c2cwsgiutils_acceptance_$$PPID; \
	status=$$status$$?; \
	#generate the HTML report for code coverage \
	docker run -v $(THIS_DIR)/reports/coverage/api:/reports/coverage/api:ro --name c2cwsgiutils_acceptance_reports_$$PPID $(DOCKER_BASE)_test_app:latest c2cwsgiutils_coverage_report.py c2cwsgiutils c2cwsgiutils_app; \
	status=$$status$$?; \
	#copy the HTML locally \
	docker cp c2cwsgiutils_acceptance_reports_$$PPID:/tmp/coverage/api reports/coverage; \
	status=$$status$$?; \
	#fix code path in the cobertura XML file \
	sed -ie 's%>/app/c2cwsgiutils_app<%>$(THIS_DIR)/acceptance_tests/app/c2cwsgiutils_app<%' reports/coverage/api/coverage.xml; \
	sed -ie 's%filename="/opt/c2cwsgiutils/c2cwsgiutils/%filename="c2cwsgiutils/%' reports/coverage/api/coverage.xml; \
	sed -ie 's%</sources>%<source>$(THIS_DIR)/c2cwsgiutils</source></sources>%' reports/coverage/api/coverage.xml; \
	docker rm c2cwsgiutils_acceptance_reports_$$PPID; \
	exit $$status$$?

.PHONY: send-coverage
send_coverage: build_docker
	docker run --rm -v $(THIS_DIR):$(THIS_DIR) -e CODACY_PROJECT_TOKEN=$(CODACY_PROJECT_TOKEN) $(DOCKER_BASE):latest bash -c "cd $(THIS_DIR) && python-codacy-coverage -r reports/coverage/api/coverage.xml" || true

.PHONY: build_docker
build_docker:
	docker build -t $(DOCKER_BASE):latest .

.PHONY: build_acceptance
build_acceptance: build_docker$(PYTHON_VERSION)
	docker build --build-arg DOCKER_VERSION="$(DOCKER_VERSION)" --build-arg DOCKER_COMPOSE_VERSION="$(DOCKER_COMPOSE_VERSION)" -t $(DOCKER_BASE)_acceptance:latest acceptance_tests/tests

.PHONY: build_test_app
build_test_app: build_docker$(PYTHON_VERSION)
	docker build -t $(DOCKER_BASE)_test_app:latest --build-arg "GIT_HASH=$(GIT_HASH)" acceptance_tests/app

.venv/timestamp: requirements.txt Makefile
	/usr/bin/virtualenv --python=/usr/bin/python3 .venv
	.venv/bin/pip install --upgrade -r requirements.txt twine==1.9.1
	touch $@

.PHONY: pull
pull:
	for image in `find -name "Dockerfile*" | xargs grep --no-filename FROM | awk '{print $$2}' | sort -u | grep -v c2cwsgiutils`; do docker pull $$image; done
	for image in `find -name "docker-compose*.yml" | xargs grep --no-filename "image:" | awk '{print $$2}' | sort -u | grep -v $(DOCKER_BASE) | grep -v rancher`; do docker pull $$image; done

.PHONY: dist
dist: .venv/timestamp
	rm -rf build dist
	.venv/bin/python setup.py bdist_wheel

.PHONY: release
release: mypy acceptance dist
	.venv/bin/twine upload dist/*.whl

.PHONY: run
run: build_test_app
	docker-compose -f acceptance_tests/tests/docker-compose.yml up

.PHONY: mypy
mypy: build_docker$(PYTHON_VERSION)
	docker run --rm $(DOCKER_BASE):latest mypy --ignore-missing-imports --strict-optional --disallow-untyped-defs /opt/c2cwsgiutils/c2cwsgiutils

.PHONY: mypy_local
mypy_local: .venv/timestamp
	.venv/bin/mypy --ignore-missing-imports --strict-optional --disallow-untyped-defs c2cwsgiutils

build_docker3.5:
	docker build -t $(DOCKER_BASE):latest -f Dockerfile.3.5 .

clean:
	rm -rf dist c2cwsgiutils.egg-info .venv .mypy_cache
