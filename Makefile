DOCKER_BASE = camptocamp/c2cwsgiutils

# Get the docker version (must use the same version for acceptance tests)
DOCKER_VERSION_ACTUAL := $(shell docker version --format '{{.Server.Version}}')
ifeq ($(DOCKER_VERSION_ACTUAL),)
DOCKER_VERSION := 1.12.0
else
DOCKER_VERSION := $(DOCKER_VERSION_ACTUAL)
endif


GIT_HASH := $(shell git rev-parse HEAD)
THIS_MAKEFILE_PATH := $(word $(words $(MAKEFILE_LIST)),$(MAKEFILE_LIST))
THIS_DIR := $(shell cd $(dir $(THIS_MAKEFILE_PATH));pwd)

DOCKER_TTY := $(shell [ -t 0 ] && echo -ti)

.PHONY: all
all: build acceptance

.PHONY: build
build: build_docker build_acceptance build_test_app

.PHONY: acceptance
acceptance: build_acceptance build_test_app
	docker build --tag=camptocamp/c2cwsgiutils-redis-sentinel:5 acceptance_tests/tests/redis/
	rm -rf reports/coverage/api reports/acceptance.xml
	mkdir -p reports/coverage/api
	# Get the UT reports
	docker run --rm $(DOCKER_BASE):tests cat /opt/c2cwsgiutils/.coverage > reports/coverage/api/coverage.ut.1
	# Run the tests
	docker run $(DOCKER_TTY) --volume=/var/run/docker.sock:/var/run/docker.sock \
		--name=c2cwsgiutils_acceptance_$$PPID $(DOCKER_BASE)_acceptance \
	    py.test -vv --color=yes --junitxml /reports/acceptance.xml --html /reports/acceptance.html \
			--self-contained-html $(PYTEST_OPTS) tests
	# Copy the reports locally
	docker cp c2cwsgiutils_acceptance_$$PPID:/reports ./
	docker rm c2cwsgiutils_acceptance_$$PPID
	# Generate the HTML report for code coverage
	docker run -v $(THIS_DIR)/reports/coverage/api:/reports/coverage/api:ro --name c2cwsgiutils_acceptance_reports_$$PPID $(DOCKER_BASE)_test_app c2cwsgiutils-coverage-report c2cwsgiutils c2cwsgiutils_app
	# Copy the HTML locally
	docker cp c2cwsgiutils_acceptance_reports_$$PPID:/tmp/coverage/api reports/coverage
	# Fix code path in the cobertura XML file
	sed -ie 's%>/app/c2cwsgiutils_app<%>$(THIS_DIR)/acceptance_tests/app/c2cwsgiutils_app<%' reports/coverage/api/coverage.xml
	sed -ie 's%filename="/opt/c2cwsgiutils/c2cwsgiutils/%filename="c2cwsgiutils/%' reports/coverage/api/coverage.xml
	sed -ie 's%</sources>%<source>$(THIS_DIR)</source></sources>%' reports/coverage/api/coverage.xml
	sed -ie 's%file="tests/%file="acceptance_tests/tests/tests/%' reports/acceptance.xml
	docker rm c2cwsgiutils_acceptance_reports_$$PPID

.PHONY: build_docker
build_docker:
	docker build --tag=$(DOCKER_BASE) --target=standard .

.PHONY: build_docker_test
build_docker_test:
	docker build --tag=$(DOCKER_BASE):tests --target=tests .

.PHONY: build_acceptance
build_acceptance: build_docker_test
	docker build --build-arg=DOCKER_VERSION="$(DOCKER_VERSION)" --tag=$(DOCKER_BASE)_acceptance acceptance_tests/tests

.PHONY: build_test_app
build_test_app: build_docker
	docker build --tag=$(DOCKER_BASE)_test_app --build-arg="GIT_HASH=$(GIT_HASH)" acceptance_tests/app

.venv/timestamp: requirements-local.txt publish-requirements.txt
	/usr/bin/virtualenv --python=/usr/bin/python3 .venv
	.venv/bin/pip3 install --upgrade -r requirements-local.txt
	touch $@

.PHONY: pull
pull:
	for image in `find -name "Dockerfile*" | xargs grep --no-filename FROM | awk '{print $$2}' | sort -u | grep -v c2cwsgiutils`; do docker pull $$image; done
	for image in `find -name "docker-compose*.yml" | xargs grep --no-filename "image:" | awk '{print $$2}' | sort -u | grep -v $(DOCKER_BASE) | grep -v rancher`; do docker pull $$image; done

.PHONY: run
run: build_test_app
	TEST_IP=172.17.0.1 docker-compose -f acceptance_tests/tests/docker-compose.yml up

.PHONY: mypy_local
mypy_local: .venv/timestamp
	.venv/bin/mypy --ignore-missing-imports --strict-optional --strict c2cwsgiutils

clean:
	rm -rf dist c2cwsgiutils.egg-info .venv .mypy_cache
