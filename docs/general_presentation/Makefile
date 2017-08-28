DOT_FILES += $(shell find -name "*.dot" -print)
GEN_DOT_FILES +=  $(addprefix build/, $(DOT_FILES:.dot=.png))

all: $(GEN_DOT_FILES) build/remark-latest.min.js

build/%.png: %.dot
	@mkdir -p build
	cat $< | docker run --rm -i pvalsecc/graphviz:latest dot -Tpng > $@

build/remark-latest.min.js:
	curl https://remarkjs.com/downloads/remark-latest.min.js > $@

clean:
	rm -rf build
