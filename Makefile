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

GIT_TAG := $(shell git describe --tags --first-parent 2>/dev/null || echo "none")
GIT_HASH := $(shell git rev-parse HEAD)
THIS_MAKEFILE_PATH := $(word $(words $(MAKEFILE_LIST)),$(MAKEFILE_LIST))
THIS_DIR := $(shell cd $(dir $(THIS_MAKEFILE_PATH));pwd)

.PHONY: all
all: acceptance

.PHONY: build
build: build_acceptance build_test_app

.PHONY: acceptance
acceptance: build_acceptance build_test_app
	rm -rf reports/coverage/api reports/acceptance.xml
	mkdir -p reports/coverage/api
	#run the tests
	docker run -e DOCKER_TAG=$(DOCKER_TAG) -v /var/run/docker.sock:/var/run/docker.sock --name c2cwsgiutils_acceptance_$(DOCKER_TAG)_$$PPID $(DOCKER_BASE)_acceptance:$(DOCKER_TAG) py.test -vv --color=yes --junitxml /reports/acceptance.xml $(PYTEST_OPTS) tests; \
	status=$$?; \
	#copy the reports locally \
	docker cp c2cwsgiutils_acceptance_$(DOCKER_TAG)_$$PPID:/reports ./; \
	status=$$status$$?; \
	docker rm c2cwsgiutils_acceptance_$(DOCKER_TAG)_$$PPID; \
	status=$$status$$?; \
	#generate the HTML report for code coverage \
	docker run -v $(THIS_DIR)/reports/coverage/api:/reports/coverage/api:ro --name c2cwsgiutils_acceptance_reports_$(DOCKER_TAG)_$$PPID $(DOCKER_BASE)_test_app:$(DOCKER_TAG) ./c2cwsgiutils_coverage_report.py c2cwsgiutils c2cwsgiutils_app; \
	status=$$status$$?; \
	#copy the HTML locally \
	docker cp c2cwsgiutils_acceptance_reports_$(DOCKER_TAG)_$$PPID:/tmp/coverage/api reports/coverage; \
	status=$$status$$?; \
	#fix code path in the cobertura XML file \
	sed -ie 's%>/app/c2cwsgiutils_app<%>$(THIS_DIR)/acceptance_tests/app/c2cwsgiutils_app<%' reports/coverage/api/coverage.xml; \
	sed -ie 's%>/app/c2cwsgiutils<%>$(THIS_DIR)/c2cwsgiutils<%' reports/coverage/api/coverage.xml; \
	docker rm c2cwsgiutils_acceptance_reports_$(DOCKER_TAG)_$$PPID; \
	exit $$status$$?

.PHONY: build_acceptance
build_acceptance:
	rsync -a c2cwsgiutils rel_requirements.txt setup.cfg acceptance_tests/tests/
	docker build --build-arg DOCKER_VERSION="$(DOCKER_VERSION)" --build-arg DOCKER_COMPOSE_VERSION="$(DOCKER_COMPOSE_VERSION)" -t $(DOCKER_BASE)_acceptance:$(DOCKER_TAG) acceptance_tests/tests

.PHONY: build_test_app
build_test_app:
	rsync -a c2cwsgiutils c2cwsgiutils_run c2cwsgiutils_genversion.py c2cwsgiutils_coverage_report.py c2cwsgiutils_stats_db.py rel_requirements.txt setup.cfg acceptance_tests/app/
	docker build -t $(DOCKER_BASE)_test_app:$(DOCKER_TAG) --build-arg "GIT_TAG=$(GIT_TAG)" --build-arg "GIT_HASH=$(GIT_HASH)" acceptance_tests/app

.venv/timestamp: rel_requirements.txt dev_requirements.txt
	/usr/bin/virtualenv --python=/usr/bin/python3.5 .venv
	.venv/bin/pip install -r rel_requirements.txt -r dev_requirements.txt
	touch $@

.PHONY: pull
pull:
	for image in `find -name Dockerfile | xargs grep --no-filename FROM | awk '{print $$2}' | sort -u`; do docker pull $$image; done
	for image in `find -name "docker-compose*.yml" | xargs grep --no-filename "image:" | awk '{print $$2}' | sort -u | grep -v $(DOCKER_BASE) | grep -v rancher`; do docker pull $$image; done

.PHONY: dist
dist: .venv/timestamp
	rm -rf build dist
	.venv/bin/python setup.py bdist_wheel

.PHONY: release
release: dist
	.venv/bin/twine upload dist/*.whl
